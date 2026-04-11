import os
import django
import sys
import telebot
from django.utils import timezone

# 1. Loyiha papkasini Python yo'liga qo'shish (Xatolik bermasligi uchun)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# 2. Django sozlamalarini ulaymiz
# Siz aytdingizki settings.py 'config' papkasida. Shuning uchun 'config.settings' yozamiz
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from transactions.models import Transaction
from django.contrib.auth import get_user_model

User = get_user_model()

TOKEN = '8743342641:AAEQaqxqGyBxU-4jvfyVwks0XjiL2JALmhQ'
bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=['start'])
def start(message):
    text = message.text.split()
    if len(text) > 1:
        code = text[1]
        # User modelidan kod bo'yicha qidiramiz
        user_obj = User.objects.filter(telegram_code=code).first()
        if user_obj:
            user_obj.telegram_id = message.from_user.id
            user_obj.save()
            bot.send_message(message.chat.id, f"✅ Bog'landi! Xush kelibsiz, {user_obj.username}")
        else:
            bot.send_message(message.chat.id, "❌ Kod noto'g'ri yoki eskirgan.")
    else:
        bot.send_message(message.chat.id, "Salom! Botni ishlatish uchun saytdagi 'Botni ulash' tugmasini bosing.")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    # Telegram ID orqali foydalanuvchini topamiz
    user_obj = User.objects.filter(telegram_id=message.from_user.id).first()

    if not user_obj:
        bot.send_message(message.chat.id, "⚠️ Avval botni profilingizga bog'lang!")
        return

    try:
        parts = message.text.split(' ', 2)
        if len(parts) < 2:
            raise ValueError

        sign = parts[0]  # + yoki -
        amount = float(parts[1])
        note = parts[2] if len(parts) > 2 else "Bot orqali kiritildi"

        if sign == '+':
            t_type = 'income'
        elif sign == '-':
            t_type = 'expense'
        else:
            raise ValueError

        # Tranzaksiyani yaratish
        Transaction.objects.create(
            user=user_obj,
            amount=amount,
            type=t_type,
            note=note,
            date=timezone.now()
        )
        bot.send_message(message.chat.id, f"✅ Saqlandi!\nTur: {t_type}\nSumma: {amount} UZS\nIzoh: {note}")

    except Exception as e:
        bot.send_message(message.chat.id, "❌ Xato! Formatni tekshiring.\nMisol:\n- 20000 tushlik\n+ 500000 oylik")


print("Bot ishga tushdi...")
bot.polling()