from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from transactions.models import Transaction
from goals.models import Goal
from planner.models import DayPlan
from django.utils import timezone
from django.db.models import Sum

def root_redirect(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('users:login')

@login_required
def dashboard_view(request):
    # Total balances calculations
    transactions = Transaction.objects.filter(user=request.user)
    total_income = transactions.filter(type='income').aggregate(Sum('amount'))['amount__sum'] or 0
    total_expense = transactions.filter(type='expense').aggregate(Sum('amount'))['amount__sum'] or 0
    balance = total_income - total_expense

    # Goals progress
    goals = Goal.objects.filter(user=request.user, is_completed=False).order_by('deadline')[:3]

    # Today's tasks
    plan = DayPlan.objects.filter(user=request.user, date=timezone.now().date()).first()
    tasks = plan.tasks.all().order_by('start_time')[:5] if plan else []

    # Recent transactions
    recent_transactions = transactions.order_by('-date', '-created_at')[:5]

    context = {
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,
        'goals': goals,
        'tasks': tasks,
        'recent_transactions': recent_transactions,
    }
    return render(request, 'dashboard.html', context)
