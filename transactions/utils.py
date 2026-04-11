import requests
from django.conf import settings

from transactions.models import Transaction


def get_uzs_rate():
    api_key = settings.CURRENCY_API_KEY
    url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/USD"

    try:
        response = requests.get(url)
        data = response.json()
        if data['result'] == 'success':
            # 1 USD necha so'm ekanligini qaytaradi
            return float(data['conversion_rates']['UZS'])
    except Exception as e:
        print(f"Xato yuz berdi: {e}")

    return 12600.0  # Agar internet bo'lmasa, vaqtinchalik kurs


from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta


def get_financial_forecast(user):
    today = timezone.now()
    month_start = today.replace(day=1)
    days_passed = today.day

    # 1. Shu oydagi jami xarajat
    current_expense = Transaction.objects.filter(
        user=user,
        type='expense',
        date__month=today.month,
        date__year=today.year
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    # 2. Kunlik o'rtacha xarajat
    daily_average = current_expense / days_passed if days_passed > 0 else 0

    # 3. Oy oxirigacha necha kun qoldi?
    import calendar
    last_day = calendar.monthrange(today.year, today.month)[1]
    days_left = last_day - days_passed

    # 4. Bashorat: Oy oxirigacha yana qancha pul ketadi?
    estimated_future_expense = daily_average * days_left
    total_forecast = current_expense + estimated_future_expense

    # 5. Balans holati
    current_balance = Transaction.objects.filter(user=user).aggregate(
        total=Sum('amount', weight='type')  # Bu mantiqiy misol
    )  # O'zingizning balans hisoblash kodingizdan foydalaning

    return {
        'daily_average': daily_average,
        'forecast_total': total_forecast,
        'days_left': days_left,
        'warning': total_forecast > (current_expense + 1000000)  # Misol: limitdan oshsa
    }