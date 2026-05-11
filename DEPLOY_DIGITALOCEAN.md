# DigitalOcean Deploy (App Platform)

Ushbu loyiha `Django web + Telegram bot worker` dan iborat.

## 1) GitHub'ga push qiling

Repo `main` branchga push bo'lishi kerak.

## 2) DigitalOcean App yarating

1. `cloud.digitalocean.com` -> **Apps** -> **Create App**
2. GitHub repository'ni ulang
3. Branch: `main`

## 3) Components qo'shing

### A) Web Service
- **Type**: Web Service
- **Source dir**: repo root
- **Build Command**:
  - `pip install -r requirements.txt`
- **Run Command**:
  - `python manage.py migrate && python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
- **HTTP Port**: avtomatik (`$PORT`)

### B) Worker (Telegram bot)
- **Type**: Worker
- **Source dir**: repo root
- **Build Command**:
  - `pip install -r requirements.txt`
- **Run Command**:
  - `python bot.py`

## 4) Database (PostgreSQL) ulash

1. App ichida **Add Resource** -> **Database** -> PostgreSQL
2. Environment variable sifatida `DATABASE_URL` beriladi (yoki o'zingiz qo'shing)

## 5) Environment Variables

Quyidagilarni App darajasida qo'shing:

- `SECRET_KEY` = kuchli secret
- `DEBUG` = `False`
- `ALLOWED_HOSTS` = web domen(lar), vergul bilan  
  Misol: `my-app-xxxx.ondigitalocean.app`
- `DATABASE_URL` = PostgreSQL connection string
- `TELEGRAM_BOT_TOKEN` = bot token
- `TELEGRAM_BOT_USERNAME` = bot username
- `OPENROUTER_API_KEY` (agar ishlatilsa)
- `CURRENCY_API_KEY` (agar ishlatilsa)
- `GEMINI_API_KEY` (agar ishlatilsa)
- `GROQ_API_KEY` (agar ishlatilsa)
- `OPENAI_API_KEY` (agar ishlatilsa)
- `OPENAI_STT_MODEL` = `gpt-4o-transcribe` (ixtiyoriy)





## 6) Deploy va tekshiruv

1. **Create Resources** ni bosing
2. Deploy tugagach web URL oching
3. Admin yaratish (App Console ichida):
   - `python manage.py createsuperuser`
4. Telegram botni tekshirish:
   - `/start`
   - `/balance`

## Eslatma

- `SQLite` production uchun tavsiya etilmaydi; shu sabab `DATABASE_URL` orqali Postgres ishlatish sozlangan.
- Har deployda worker qayta ishga tushadi; bot `infinity_polling` bilan ishlaydi.
