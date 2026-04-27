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
    all_categories = _user_categories(request.user)
    income_categories = all_categories.filter(type='income')
    expense_categories = all_categories.filter(type='expense')

    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.save()
            return redirect('transactions:list')
    else:
        form = TransactionForm()

    return render(request, 'transactions/create.html', {
        'form': form,
        'income_categories': income_categories,
        'expense_categories': expense_categories,
    })


@login_required
def transaction_update(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    categories = _user_categories(request.user)

    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction)
        if form.is_valid():
            form.save()
            return redirect('transactions:list')
    else:
        form = TransactionForm(instance=transaction)

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

    from .voice_parser import parse_transaction_text
    parsed = parse_transaction_text(transcript, request.user)

    if not parsed:
        return JsonResponse({'error': 'Tushunilmadi. Iltimos qayta urinib ko\'ring.'}, status=422)

    return JsonResponse({
        'transcript': transcript,
        'amount': float(parsed['amount']),
        'type': parsed['type'],
        'category_id': parsed.get('category_id'),
        'category_name': parsed.get('category_name'),
        'note': parsed.get('note', ''),
    })


@login_required
@require_POST
def voice_create(request):
    """Save a transaction parsed from voice/text."""
    try:
        body = json.loads(request.body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'error': 'Noto\'g\'ri so\'rov'}, status=400)

    try:
        amount = Decimal(str(body.get('amount', '0')))
    except (InvalidOperation, ValueError):
        return JsonResponse({'error': 'Summa noto\'g\'ri'}, status=400)
    if amount <= 0:
        return JsonResponse({'error': 'Summa 0 dan katta bo\'lishi kerak'}, status=400)

    t_type = body.get('type')
    if t_type not in ('income', 'expense'):
        return JsonResponse({'error': 'Tur noto\'g\'ri'}, status=400)

    note = (body.get('note') or '').strip()[:255]
    category_id = body.get('category_id')
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
    return JsonResponse({'ok': True})
