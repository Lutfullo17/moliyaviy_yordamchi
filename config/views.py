from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from transactions.models import Transaction
from categories.models import Category
from goals.models import Goal
from planner.models import DayPlan
from django.utils import timezone
from django.db.models import Sum
import uuid
import calendar

def root_redirect(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('users:login')

@login_required
def dashboard_view(request):
    current_month = timezone.now().month
    current_year = timezone.now().year

    # --- TELEGRAM BOT BOG'LASH ---
    user = request.user
    if not user.telegram_code:
        user.telegram_code = str(uuid.uuid4())[:8]
        user.save()

    bot_username = "moliyaYordam_bot"
    bot_url = f"https://t.me/{bot_username}?start={user.telegram_code}"

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

    # Svetofor (budget) data - faqat limit > 0 bo'lgan kategoriyalar
    categories = Category.objects.filter(user=request.user) | Category.objects.filter(is_default=True)
    budget_data = []
    for cat in categories:
        if not (cat.monthly_limit and cat.monthly_limit > 0):
            continue
        
        # Limit muddati tugaganligini tekshirish
        if cat.limit_duration and cat.limit_set_at:
            from datetime import timedelta
            expiry_date = cat.limit_set_at + timedelta(days=cat.limit_duration)
            if timezone.now() > expiry_date:
                continue # Muddat tugagan, svetofordan olib tashlaymiz

        spent = Transaction.objects.filter(
            category=cat,
            type='expense',
            date__month=current_month,
            date__year=current_year,
            user=request.user
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        limit = float(cat.monthly_limit)
        percent = (float(spent) / limit * 100) if limit > 0 else 0

        if percent >= 100:
            color = 'red'
            color_class = 'bg-red-500'
            text_class = 'text-red-600'
            badge = 'Limitdan oshdi!'
        elif percent >= 80:
            color = 'yellow'
            color_class = 'bg-yellow-400'
            text_class = 'text-yellow-600'
            badge = 'Ehtiyot bo\'ling'
        else:
            color = 'green'
            color_class = 'bg-emerald-500'
            text_class = 'text-emerald-600'
            badge = 'Yaxshi'

        budget_data.append({
            'category': cat.name,
            'spent': float(spent),
            'limit': limit,
            'percent': min(percent, 100),
            'real_percent': percent,
            'color': color,
            'color_class': color_class,
            'text_class': text_class,
            'badge': badge,
        })

    # --- AQLLI BASHORAT ---
    total_monthly_expense = Transaction.objects.filter(
        user=request.user, type='expense',
        date__month=current_month, date__year=current_year
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    today = timezone.now()
    days_passed = today.day
    daily_average = float(total_monthly_expense) / days_passed if days_passed > 0 else 0
    last_day = calendar.monthrange(current_year, current_month)[1]
    days_left = last_day - days_passed
    remaining_forecast = daily_average * days_left

    forecast = {
        'daily_average': daily_average,
        'forecast_total': float(total_monthly_expense) + remaining_forecast,
        'days_left': days_left,
        'remaining_forecast': remaining_forecast,
    }

    context = {
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,
        'goals': goals,
        'tasks': tasks,
        'recent_transactions': recent_transactions,
        'budget_data': budget_data,
        'bot_url': bot_url,
        'forecast': forecast,
    }
    return render(request, 'dashboard.html', context)
