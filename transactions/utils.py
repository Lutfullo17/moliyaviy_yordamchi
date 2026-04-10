import requests
from django.conf import settings


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