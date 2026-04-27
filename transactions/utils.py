import calendar
import requests

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from transactions.models import Transaction


def get_uzs_rate():
    """Return 1 USD in UZS. Falls back to a sane default on error."""
    api_key = getattr(settings, 'CURRENCY_API_KEY', None)
    if not api_key:
        return 12600.0

    url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/USD"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        if data.get('result') == 'success':
            return float(data['conversion_rates']['UZS'])
    except Exception as e:
        print(f"Currency rate fetch error: {e}")

    return 12600.0


def get_financial_forecast(user):
    """Estimate spending by end of month based on current daily average."""
    today = timezone.now()
    days_passed = today.day

    current_expense = Transaction.objects.filter(
        user=user,
        type='expense',
        date__month=today.month,
        date__year=today.year,
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    daily_average = float(current_expense) / days_passed if days_passed > 0 else 0
    last_day = calendar.monthrange(today.year, today.month)[1]
    days_left = last_day - days_passed
    estimated_future_expense = daily_average * days_left
    total_forecast = float(current_expense) + estimated_future_expense

    income = Transaction.objects.filter(
        user=user,
        type='income',
        date__month=today.month,
        date__year=today.year,
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    return {
        'daily_average': daily_average,
        'forecast_total': total_forecast,
        'days_left': days_left,
        'remaining_forecast': estimated_future_expense,
        'monthly_income': float(income),
        'monthly_expense': float(current_expense),
        'will_overspend': total_forecast > float(income) and float(income) > 0,
    }
