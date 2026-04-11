import os
import django
import sys
import telebot
from telebot import types
from django.utils import timezone

# 1. Django muhitini sozlash
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from transactions.models import Transaction
from categories.models import Category
from django.contrib.auth import get_user_model

User = get_user_model()
TOKEN = '8743342641:AAEQaqxqGyBxU-4jvfyVwks0XjiL2JALmhQ'
bot = telebot.TeleBot(TOKEN)

# Vaqtinchalik ma'lumotlarni saqlash
user_data = {}


# Pastdagi doimiy tugmalar
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    item1 = types.KeyboardButton('➕ Daromad qo\'shish')
    item2 = types.KeyboardButton('➖ Xarajat qo\'shish')
    markup.add(item1, item2)
    return markup


# 1. Start komandasi (Foydalanuvchini bog'lash uchun SHART)
@bot.message_handler(commands=['start'])
def start(message):
    text = message.text.split()
    if len(text) > 1:
        code = text[1]
        user_obj = User.objects.filter(telegram_code=code).first()
        if user_obj:
            user_obj.telegram_id = message.from_user.id
            user_obj.save()
            bot.send_message(
                message.chat.id,
                f"✅ Bog'landi! Xush kelibsiz, {user_obj.username}",
                reply_markup=main_keyboard()
            )
        else:
            bot.send_message(message.chat.id, "❌ Kod xato yoki eskirgan.")
    else:
        # Agar foydalanuvchi allaqachon bog'langan bo'lsa
        user_exists = User.objects.filter(telegram_id=message.from_user.id).first()
        if user_exists:
            bot.send_message(message.chat.id, "Siz allaqachon bog'langansiz!", reply_markup=main_keyboard())
        else:
            bot.send_message(message.chat.id, "Botni ishlatish uchun saytdagi 'Botni ulash' tugmasini bosing.")


# 2. Tugmalar bosilganda ko'rsatma berish
@bot.message_handler(func=lambda message: message.text in ['➕ Daromad qo\'shish', '➖ Xarajat qo\'shish'])
def ask_format(message):
    if 'Daromad' in message.text:
        bot.send_message(message.chat.id, "💰 Daromadni quyidagi formatda yozing:\n`+ 500000 oylik`",
                         parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "💸 Xarajatni quyidagi formatda yozing:\n`- 25000 tushlik`",
                         parse_mode="Markdown")


# 3. Summani qabul qilish va kategoriyalarni chiqarish
@bot.message_handler(func=lambda message: message.text.startswith(('+', '-')))
def process_finance(message):
    user_obj = User.objects.filter(telegram_id=message.from_user.id).first()
    if not user_obj:
        bot.send_message(message.chat.id, "⚠️ Avval botni bog'lang!")
        return

    try:
        parts = message.text.split(' ', 2)
        sign = parts[0]
        amount = float(parts[1])
        note = parts[2] if len(parts) > 2 else "Bot orqali"
        t_type = 'income' if sign == '+' else 'expense'

        user_data[message.from_user.id] = {
            'amount': amount,
            'type': t_type,
            'note': note
        }

        # Faqat foydalanuvchining o'ziga tegishli yoki umumiy kategoriyalarni olish
        categories = Category.objects.filter(user=user_obj) | Category.objects.filter(is_default=True)

        if not categories.exists():
            bot.send_message(message.chat.id, "Sizda hali kategoriyalar yo'q. Saytda kategoriya yarating.")
            return

        markup = types.InlineKeyboardMarkup(row_width=2)
        buttons = [types.InlineKeyboardButton(cat.name, callback_data=f"cat_{cat.id}") for cat in categories]
        markup.add(*buttons)

        bot.send_message(message.chat.id, f"💵 Summa: {amount:,} UZS\n📂 Kategoriyani tanlang:", reply_markup=markup)

    except (IndexError, ValueError):
        bot.send_message(message.chat.id, "❌ Xato! Misol: `- 15000 tushlik` (Summa va izoh orasida bo'shliq bo'lsin)")


# 4. Kategoriyani tanlaganda saqlash
@bot.callback_query_handler(func=lambda call: call.data.startswith('cat_'))
def save_transaction(call):
    user_id = call.from_user.id
    if user_id not in user_data:
        bot.answer_callback_query(call.id, "Ma'lumotlar eskirgan.")
        return

    category_id = call.data.split('_')[1]
    data = user_data[user_id]
    user_obj = User.objects.filter(telegram_id=user_id).first()
    cat_obj = Category.objects.filter(id=category_id).first()

    # Bazaga saqlash
    Transaction.objects.create(
        user=user_obj,
        amount=data['amount'],
        type=data['type'],
        note=data['note'],
        category=cat_obj,
        date=timezone.now()
    )

    del user_data[user_id]

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"✅ Saqlandi!\n\n💰 Summa: {data['amount']:,} UZS\n📂 Kategoriya: {cat_obj.name}\n📝 Izoh: {data['note']}"
    )


print("Bot ishga tushdi...")
bot.polling()