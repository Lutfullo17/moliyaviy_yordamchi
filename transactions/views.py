from django.shortcuts import render, redirect, get_object_or_404
from django.utils.dateparse import parse_date
from .forms import TransactionForm
import uuid
import calendar
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from transactions.models import Transaction
from categories.models import Category


@login_required
def dashboard_view(request):
    today = timezone.now()
    current_month = today.month
    current_year = today.year


    user = request.user

    if not user.telegram_code:
        user.telegram_code = str(uuid.uuid4())[:8]
        user.save()

    bot_username = "moliyaYordam_bot"
    bot_url = f"https://t.me/{bot_username}?start={user.telegram_code}"

    # --- Svetofor Tizimi ---
    categories = Category.objects.filter(user=user) | Category.objects.filter(is_default=True)
    budget_data = []
    for cat in categories:
        spent = Transaction.objects.filter(
            category=cat, type='expense',
            date__month=current_month, date__year=current_year, user=user
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        limit = cat.monthly_limit
        percent = (spent / limit * 100) if limit > 0 else 0
        color = "bg-green-500"
        if percent >= 100:
            color = "bg-red-600"
        elif percent >= 80:
            color = "bg-yellow-500"

        budget_data.append({
            'category': cat.name, 'spent': spent, 'limit': limit,
            'percent': min(percent, 100), 'color': color
        })

    # --- AQLLI BASHORAT ---
    total_monthly_expense = Transaction.objects.filter(
        user=user, type='expense',
        date__month=current_month, date__year=current_year
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    days_passed = today.day
    daily_average = total_monthly_expense / days_passed if days_passed > 0 else 0
    last_day = calendar.monthrange(current_year, current_month)[1]
    days_left = last_day - days_passed
    remaining_forecast = daily_average * days_left

    context = {
        'bot_url': bot_url,
        'budget_data': budget_data,
        'forecast': {
            'daily_average': daily_average,
            'forecast_total': total_monthly_expense + remaining_forecast,
            'days_left': days_left,
            'remaining_forecast': remaining_forecast,
        }
    }
    return render(request, 'dashboard.html', context)

# TRANSACTIONS LIST
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

    categories = Category.objects.filter(user=request.user) | Category.objects.filter(is_default=True)

    context = {
        'transactions': transactions.order_by('-date'),
        'categories': categories
    }
    return render(request, 'transactions/list.html', context)


# CREATE TRANSACTION
@login_required
def transaction_create(request):
    categories = Category.objects.filter(user=request.user) | Category.objects.filter(is_default=True)

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
        'categories': categories
    })


# UPDATE TRANSACTION
@login_required
def transaction_update(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    categories = Category.objects.filter(user=request.user) | Category.objects.filter(is_default=True)

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
        'categories': categories
    })


# DELETE TRANSACTION
@login_required
def transaction_delete(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == 'POST':
        transaction.delete()
        return redirect('transactions:list')

    return render(request, 'transactions/delete.html', {
        'transaction': transaction
    })


# TRANSACTION SUMMARY
@login_required
def transaction_summary(request):
    transactions = Transaction.objects.filter(user=request.user)
    total_income = transactions.filter(type='income').aggregate(Sum('amount'))['amount__sum'] or 0
    total_expense = transactions.filter(type='expense').aggregate(Sum('amount'))['amount__sum'] or 0

    context = {
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': total_income - total_expense
    }
    return render(request, 'transactions/summary.html', context)


# VALYUTA BILAN ISHLASH (Agar kerak bo'lsa)
from .utils import get_uzs_rate


def transaction_create1(request):
    if request.method == 'POST':
        amount = float(request.POST.get('amount'))
        currency = request.POST.get('currency')
        final_amount = amount
        if currency == 'USD':
            rate = get_uzs_rate()
            final_amount = amount * rate