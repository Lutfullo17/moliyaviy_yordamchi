from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils.dateparse import parse_date

from .models import Transaction
from .forms import TransactionForm
from categories.models import Category

#transactions_list
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


#create_transaction
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


#update_transaction
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


#delete_transaction
@login_required
def transaction_delete(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)

    if request.method == 'POST':
        transaction.delete()
        return redirect('transactions:list')

    return render(request, 'transactions/delete.html', {
        'transaction': transaction
    })



#transaction summary
@login_required
def transaction_summary(request):
    transactions = Transaction.objects.filter(user=request.user)

    total_income = transactions.filter(type='income').aggregate(
        Sum('amount')
    )['amount__sum'] or 0

    total_expense = transactions.filter(type='expense').aggregate(
        Sum('amount')
    )['amount__sum'] or 0

    context = {
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': total_income - total_expense
    }

    return render(request, 'transactions/summary.html', context)
