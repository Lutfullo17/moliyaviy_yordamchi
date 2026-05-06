import csv
import json
from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST

from .forms import TransactionForm
from .models import Transaction
from categories.models import Category


def _user_categories(user):
    return Category.objects.filter(user=user) | Category.objects.filter(is_default=True)


@login_required
def transaction_list(request):
    transactions = Transaction.objects.filter(user=request.user)

    date = request.GET.get('date')
    if date:
        parsed_date = parse_date(date)
        if parsed_date:
            transactions = transactions.filter(date=parsed_date)

    category = request.GET.get('category')
    if category:
        transactions = transactions.filter(category_id=category)

    t_type = request.GET.get('type')
    if t_type in ('income', 'expense'):
        transactions = transactions.filter(type=t_type)

    transactions = transactions.order_by('-date', '-created_at')

    total_income = transactions.filter(type='income').aggregate(Sum('amount'))['amount__sum'] or 0
    total_expense = transactions.filter(type='expense').aggregate(Sum('amount'))['amount__sum'] or 0

    context = {
        'transactions': transactions,
        'categories': _user_categories(request.user),
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': total_income - total_expense,
    }
    return render(request, 'transactions/summary.html', context)


# Backwards-compatible alias
transaction_summary = transaction_list


@login_required
def transaction_create(request):
    """Ovoz/matn parse API orqali qo'shiladi — klassik POST formasi yo'q."""
    return render(request, 'transactions/create.html')


@login_required
def transaction_update(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    categories = _user_categories(request.user)

    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('transactions:list')
    else:
        form = TransactionForm(instance=transaction, user=request.user)

    return render(request, 'transactions/update.html', {
        'form': form,
        'transaction': transaction,
        'categories': categories,
    })


@login_required
def transaction_delete(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == 'POST':
        transaction.delete()
        return redirect('transactions:list')

    return render(request, 'transactions/delete.html', {
        'transaction': transaction
    })


@login_required
def transaction_export_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    today = timezone.now().date().isoformat()
    response['Content-Disposition'] = f'attachment; filename="transactions_{today}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Sana', 'Turi', 'Kategoriya', 'Summa', 'Izoh'])

    qs = Transaction.objects.filter(user=request.user).order_by('-date', '-created_at')
    for t in qs:
        writer.writerow([
            t.date.strftime('%d.%m.%Y'),
            'Daromad' if t.type == 'income' else 'Xarajat',
            t.category.name if t.category else '',
            t.amount,
            t.note or '',
        ])
    return response


@login_required
def category_breakdown_api(request):
    today = timezone.now()
    qs = Transaction.objects.filter(
        user=request.user,
        type='expense',
        date__month=today.month,
        date__year=today.year,
    ).values('category__name').annotate(total=Sum('amount')).order_by('-total')

    data = [
        {
            'category': row['category__name'] or 'Kategoriyasiz',
            'total': float(row['total'] or 0),
        }
        for row in qs
    ]
    return JsonResponse({'items': data})


@login_required
@require_POST
def voice_parse(request):
    """Parse free-text Uzbek transaction description into structured data."""
    try:
        body = json.loads(request.body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'error': 'Noto\'g\'ri so\'rov'}, status=400)

    transcript = (body.get('transcript') or '').strip()
    if not transcript:
        return JsonResponse({'error': 'Bo\'sh matn'}, status=400)

    from .voice_parser import parse_all_transactions_text

    parsed_list = parse_all_transactions_text(transcript, request.user, try_ai_fallback=True)
    if not parsed_list:
        return JsonResponse({'error': 'Tushunilmadi. Iltimos qayta urinib ko\'ring.'}, status=422)

    def serialize(p):
        return {
            'amount': float(p['amount']),
            'type': p['type'],
            'category_id': p.get('category_id'),
            'category_name': p.get('category_name'),
            'note': p.get('note', ''),
        }

    rows = [serialize(p) for p in parsed_list]
    payload = {'transcript': transcript, 'transactions': rows, 'count': len(rows)}
    if len(parsed_list) == 1:
        payload.update(rows[0])
    return JsonResponse(payload)


@login_required
@require_POST
def voice_create(request):
    """Save one or many parsed transactions ({amount, type, category_id?, note})."""
    try:
        body = json.loads(request.body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'error': 'Noto\'g\'ri so\'rov'}, status=400)

    raw_rows = body.get('transactions')
    if isinstance(raw_rows, list):
        rows = raw_rows
    elif raw_rows:
        rows = [raw_rows]
    else:
        rows = [body]

    saved = 0
    errors: list[str] = []

    for item in rows:
        if not isinstance(item, dict):
            errors.append('noto\'g\'ri yozuv')
            continue
        try:
            amount = Decimal(str(item.get('amount', '0')))
        except (InvalidOperation, ValueError):
            errors.append('summa')
            continue
        if amount <= 0:
            errors.append('summa 0')
            continue

        t_type = item.get('type')
        if t_type not in ('income', 'expense'):
            errors.append('tur')
            continue

        note = (item.get('note') or '').strip()[:255]
        category_id = item.get('category_id')
        category = None
        if category_id:
            category = Category.objects.filter(
                id=category_id
            ).filter(
                user=request.user
            ).first() or Category.objects.filter(id=category_id, is_default=True).first()

        Transaction.objects.create(
            user=request.user,
            amount=amount,
            type=t_type,
            category=category,
            note=note,
            date=timezone.now().date(),
        )
        saved += 1

    if not saved:
        return JsonResponse(
            {'ok': False, 'error': 'Hech bir tranzaksiya saqlanmadi', 'details': errors[:5]},
            status=400,
        )
    return JsonResponse({'ok': True, 'saved': saved})
