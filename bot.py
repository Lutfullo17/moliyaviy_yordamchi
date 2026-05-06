"""Telegram bot for the MoliyaviyYordamchi app.

Features:
- Linking telegram account to web user via /start <code>
- Quick income/expense entry via "+ 5000 lunch" or "- 25000 taksi" syntax
- Voice transactions: send a voice message describing the spend/income
- /balance, /summary, /list, /goals, /tip, /help, /menu commands
"""

from __future__ import annotations

import os
import sys
import calendar
import django
from decimal import Decimal

# 1. Django muhitini sozlash
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import telebot
from telebot import types

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Sum, Q
from django.utils import timezone

from transactions.models import Transaction
from transactions.voice_parser import parse_all_transactions_text, transcribe_audio_bytes
from categories.models import Category
from goals.models import Goal


User = get_user_model()
TOKEN = getattr(settings, 'TELEGRAM_BOT_TOKEN', None) or os.environ.get('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    raise RuntimeError('TELEGRAM_BOT_TOKEN sozlanmagan')

bot = telebot.TeleBot(TOKEN)

# Vaqtinchalik foydalanuvchi holati
user_data: dict[int, dict] = {}


def fmt_money(value) -> str:
    try:
        return f"{int(round(float(value))):,}".replace(",", " ")
    except (TypeError, ValueError):
        return str(value)


def main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton('➕ Daromad qo\'shish'),
        types.KeyboardButton('➖ Xarajat qo\'shish'),
    )
    markup.add(
        types.KeyboardButton('💼 Balans'),
        types.KeyboardButton('📊 Hisobot'),
    )
    markup.add(
        types.KeyboardButton('🎯 Maqsadlar'),
        types.KeyboardButton('🤖 AI maslahat'),
    )
    markup.add(types.KeyboardButton('🎤 Ovozli kiritish'))
    return markup


def get_user(message) -> 'User | None':
    return User.objects.filter(telegram_id=message.from_user.id).first()


def require_user(message):
    user = get_user(message)
    if not user:
        bot.send_message(message.chat.id, "⚠️ Avval saytda ro'yxatdan o'ting va 'Botni ulash' tugmasini bosing.")
        return None
    return user


# ==============================
#  /start - hisobni bog'lash
# ==============================
@bot.message_handler(commands=['start'])
def start(message):
    parts = message.text.split()
    if len(parts) > 1:
        code = parts[1]
        user_obj = User.objects.filter(telegram_code=code).first()
        if user_obj:
            user_obj.telegram_id = message.from_user.id
            user_obj.save()
            bot.send_message(
                message.chat.id,
                f"✅ Bog'landi! Xush kelibsiz, {user_obj.username}",
                reply_markup=main_keyboard(),
            )
        else:
            bot.send_message(message.chat.id, "❌ Kod xato yoki eskirgan.")
        return

    user_exists = get_user(message)
    if user_exists:
        bot.send_message(
            message.chat.id,
            f"Salom, {user_exists.username}! Quyidagi tugmalardan foydalaning.",
            reply_markup=main_keyboard(),
        )
    else:
        bot.send_message(
            message.chat.id,
            "Botni ishlatish uchun saytdagi 'Botni ulash' tugmasini bosing.",
        )


@bot.message_handler(commands=['help'])
def help_cmd(message):
    text = (
        "🤖 *MoliyaBot komandalari*\n\n"
        "📌 *Tezkor kiritish:*\n"
        "`+ 5000000 oylik` — daromad qo'shish\n"
        "`- 25000 tushlik` — xarajat qo'shish\n"
        "🎤 Ovozli xabar yuboring — bot avtomatik tushunadi.\n\n"
        "*Komandalar:*\n"
        "/balance — joriy balans\n"
        "/summary — bu oyning hisoboti\n"
        "/list — oxirgi 5 ta tranzaksiya\n"
        "/goals — maqsadlar holati\n"
        "/tip — AI moliyaviy maslahat\n"
        "/menu — asosiy menyu\n"
        "/help — yordam"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=main_keyboard())


@bot.message_handler(commands=['menu'])
def menu_cmd(message):
    bot.send_message(message.chat.id, "Asosiy menyu:", reply_markup=main_keyboard())


# ==============================
#  Balans
# ==============================
def _balance_text(user) -> str:
    qs = Transaction.objects.filter(user=user)
    income = qs.filter(type='income').aggregate(Sum('amount'))['amount__sum'] or 0
    expense = qs.filter(type='expense').aggregate(Sum('amount'))['amount__sum'] or 0
    balance = income - expense
    sign = '🟢' if balance >= 0 else '🔴'
    return (
        f"{sign} *Joriy balans:* `{fmt_money(balance)}` UZS\n"
        f"📈 Daromad: `{fmt_money(income)}` UZS\n"
        f"📉 Xarajat: `{fmt_money(expense)}` UZS"
    )


@bot.message_handler(commands=['balance'])
def balance_cmd(message):
    user = require_user(message)
    if not user:
        return
    bot.send_message(message.chat.id, _balance_text(user), parse_mode="Markdown")


# ==============================
#  Oylik hisobot
# ==============================
def _monthly_summary_text(user) -> str:
    today = timezone.now()
    qs = Transaction.objects.filter(
        user=user, date__month=today.month, date__year=today.year,
    )
    income = qs.filter(type='income').aggregate(Sum('amount'))['amount__sum'] or 0
    expense = qs.filter(type='expense').aggregate(Sum('amount'))['amount__sum'] or 0
    days_passed = today.day or 1
    daily_avg = float(expense) / days_passed
    last_day = calendar.monthrange(today.year, today.month)[1]
    days_left = last_day - days_passed
    forecast = float(expense) + daily_avg * days_left

    by_cat = (
        qs.filter(type='expense')
        .values('category__name')
        .annotate(total=Sum('amount'))
        .order_by('-total')[:5]
    )
    cat_lines = "\n".join(
        f"  • {row['category__name'] or 'Boshqa'}: `{fmt_money(row['total'])}` UZS"
        for row in by_cat
    ) or "  • Hali xarajat yo'q"

    return (
        f"📊 *{today.strftime('%B %Y')} hisoboti*\n\n"
        f"📈 Daromad: `{fmt_money(income)}` UZS\n"
        f"📉 Xarajat: `{fmt_money(expense)}` UZS\n"
        f"💰 Oqim: `{fmt_money(income - expense)}` UZS\n\n"
        f"⏳ Kunlik o'rtacha xarajat: `{fmt_money(daily_avg)}` UZS\n"
        f"🔮 Oy oxiri prognoz: `{fmt_money(forecast)}` UZS\n\n"
        f"*Top 5 kategoriya:*\n{cat_lines}"
    )


@bot.message_handler(commands=['summary'])
def summary_cmd(message):
    user = require_user(message)
    if not user:
        return
    bot.send_message(message.chat.id, _monthly_summary_text(user), parse_mode="Markdown")


# ==============================
#  Oxirgi tranzaksiyalar
# ==============================
def _recent_text(user) -> str:
    qs = Transaction.objects.filter(user=user).order_by('-date', '-created_at')[:5]
    if not qs:
        return "Hali tranzaksiya yo'q."
    lines = []
    for t in qs:
        sign = '➕' if t.type == 'income' else '➖'
        cat = (t.category.name if t.category else 'kategoriyasiz')
        lines.append(
            f"{sign} `{fmt_money(t.amount)}` UZS · {cat}\n"
            f"   📅 {t.date.strftime('%d.%m.%Y')}  📝 _{t.note or '—'}_"
        )
    return "🧾 *Oxirgi 5 ta tranzaksiya*\n\n" + "\n\n".join(lines)


@bot.message_handler(commands=['list'])
def list_cmd(message):
    user = require_user(message)
    if not user:
        return
    bot.send_message(message.chat.id, _recent_text(user), parse_mode="Markdown")


# ==============================
#  Maqsadlar
# ==============================
def _goals_text(user) -> str:
    goals = Goal.objects.filter(user=user, is_completed=False).order_by('deadline')[:5]
    if not goals:
        return "🎯 Hozircha aktiv maqsad yo'q. Saytdan yangi maqsad qo'shing."
    lines = []
    for g in goals:
        pct = g.progress_percentage()
        lines.append(
            f"🎯 *{g.title}*\n"
            f"   {fmt_money(g.current_amount)} / {fmt_money(g.target_amount)} UZS ({pct}%)\n"
            f"   📅 Muddat: {g.deadline.strftime('%d.%m.%Y')}"
        )
    return "*Aktiv maqsadlaringiz:*\n\n" + "\n\n".join(lines)


@bot.message_handler(commands=['goals'])
def goals_cmd(message):
    user = require_user(message)
    if not user:
        return
    bot.send_message(message.chat.id, _goals_text(user), parse_mode="Markdown")


# ==============================
#  AI maslahat
# ==============================
@bot.message_handler(commands=['tip'])
def tip_cmd(message):
    user = require_user(message)
    if not user:
        return
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        from goals.services.gemini_service import client
        today = timezone.now()
        qs = Transaction.objects.filter(
            user=user, date__month=today.month, date__year=today.year, type='expense',
        )
        total = qs.aggregate(Sum('amount'))['amount__sum'] or 0
        top_cats = (
            qs.values('category__name')
            .annotate(total=Sum('amount'))
            .order_by('-total')[:3]
        )
        cats_str = ", ".join(f"{c['category__name'] or 'boshqa'}: {fmt_money(c['total'])}" for c in top_cats)
        prompt = (
            "Sen O'zbekistondagi moliyaviy maslahatchisan. Foydalanuvchining bu oydagi xarajatlari: "
            f"{fmt_money(total)} UZS. Eng katta kategoriyalar: {cats_str}. "
            "2-3 jumlada qisqa, aniq va foydali maslahat ber. Faqat o'zbek tilida."
        )
        resp = client.chat.completions.create(
            model="deepseek/deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
        )
        bot.send_message(message.chat.id, "💡 " + resp.choices[0].message.content.strip())
    except Exception as e:
        bot.send_message(message.chat.id, f"🤖 AI hozir mavjud emas: {e}")


# ==============================
#  Reply tugmalari
# ==============================
@bot.message_handler(func=lambda m: m.text in [
    '➕ Daromad qo\'shish', '➖ Xarajat qo\'shish',
])
def ask_format(message):
    if 'Daromad' in message.text:
        bot.send_message(message.chat.id, "💰 Daromadni quyidagi formatda yozing:\n`+ 500000 oylik`",
                         parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "💸 Xarajatni quyidagi formatda yozing:\n`- 25000 tushlik`",
                         parse_mode="Markdown")


@bot.message_handler(func=lambda m: m.text == '💼 Balans')
def kb_balance(message):
    balance_cmd(message)


@bot.message_handler(func=lambda m: m.text == '📊 Hisobot')
def kb_summary(message):
    summary_cmd(message)


@bot.message_handler(func=lambda m: m.text == '🎯 Maqsadlar')
def kb_goals(message):
    goals_cmd(message)


@bot.message_handler(func=lambda m: m.text == '🤖 AI maslahat')
def kb_tip(message):
    tip_cmd(message)


@bot.message_handler(func=lambda m: m.text == '🎤 Ovozli kiritish')
def kb_voice(message):
    bot.send_message(
        message.chat.id,
        "🎤 Ovozli xabar yuboring. Misol uchun ayting: \n"
        "_\"Tushlikka 25 ming sarfladim\"_ yoki _\"Maoshim 5 million keldi\"_",
        parse_mode="Markdown",
    )


# ==============================
#  + 5000 lunch / - 25000 taksi
# ==============================
def _ask_for_category(chat_id, user, t_type, amount, note):
    categories = Category.objects.filter(
        Q(user=user) | Q(is_default=True), type=t_type,
    )
    if not categories.exists():
        type_uz = "daromad" if t_type == 'income' else "xarajat"
        bot.send_message(chat_id, f"⚠️ Sizda hali {type_uz} uchun kategoriyalar yo'q. Saytdan qo'shing.")
        return False

    user_data[chat_id] = {'amount': amount, 'type': t_type, 'note': note}
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [types.InlineKeyboardButton(cat.name, callback_data=f"cat_{cat.id}") for cat in categories]
    markup.add(*buttons)
    sign = '➕' if t_type == 'income' else '➖'
    bot.send_message(
        chat_id,
        f"{sign} *Summa:* `{fmt_money(amount)}` UZS\n📝 *Izoh:* {note}\n\n📂 Kategoriyani tanlang:",
        parse_mode="Markdown",
        reply_markup=markup,
    )
    return True


@bot.message_handler(func=lambda m: m.text and m.text.startswith(('+', '-')))
def process_finance(message):
    user = require_user(message)
    if not user:
        return
    try:
        parts = message.text.split(' ', 2)
        sign = parts[0]
        amount = Decimal(parts[1].replace(',', '').replace(' ', ''))
        note = parts[2] if len(parts) > 2 else "Bot orqali"
    except (IndexError, ValueError):
        bot.send_message(message.chat.id, "❌ Xato! Misol: `- 15000 tushlik` yoki `+ 500000 oylik`.")
        return

    t_type = 'income' if sign == '+' else 'expense'
    _ask_for_category(message.chat.id, user, t_type, amount, note)


# ==============================
#  Ovozli xabar
# ==============================
@bot.message_handler(content_types=['voice', 'audio'])
def handle_voice(message):
    user = require_user(message)
    if not user:
        return
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        file_id = message.voice.file_id if message.voice else message.audio.file_id
        file_info = bot.get_file(file_id)
        audio_bytes = bot.download_file(file_info.file_path)
        mime = 'audio/ogg' if message.voice else (message.audio.mime_type or 'audio/mpeg')

        text = transcribe_audio_bytes(audio_bytes, mime_type=mime)
        if not text:
            bot.send_message(
                message.chat.id,
                "❌ Ovozni tushuna olmadim. Iltimos, aniqroq gapiring yoki matn yozing.",
            )
            return

        bot.send_message(message.chat.id, f"📝 _Eshitildi:_ \"{text}\"", parse_mode="Markdown")
        parsed_list = parse_all_transactions_text(text, user, try_ai_fallback=True)
        if not parsed_list:
            bot.send_message(
                message.chat.id,
                "❌ Summa topilmadi. Misol uchun: \"Tushlikka 25 ming sarfladim\".",
            )
            return

        saved_lines = []
        for parsed in parsed_list:
            amt = Decimal(str(parsed["amount"]))
            cid = parsed.get("category_id")
            category = (
                Category.objects.filter(id=cid).filter(user=user).first()
                or Category.objects.filter(id=cid, is_default=True).first()
                if cid
                else None
            )
            Transaction.objects.create(
                user=user,
                amount=amt,
                type=parsed["type"],
                category=category,
                note=(parsed.get("note") or text)[:255],
                date=timezone.now().date(),
            )
            sign = "➕" if parsed["type"] == "income" else "➖"
            cat_name = category.name if category else "(kategoriyasiz)"
            saved_lines.append(
                f"{sign} `{fmt_money(amt)}` UZS • {cat_name}"
            )

        bot.send_message(
            message.chat.id,
            "✅ *Saqlandi:*\n" + "\n".join(saved_lines),
            parse_mode="Markdown",
        )
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Xatolik: {e}")


# ==============================
#  Kategoriya tanlash callback
# ==============================
@bot.callback_query_handler(func=lambda call: call.data.startswith('cat_'))
def save_transaction(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data:
        bot.answer_callback_query(call.id, "Ma'lumotlar eskirgan.")
        return

    category_id = int(call.data.split('_')[1])
    data = user_data[chat_id]
    user = User.objects.filter(telegram_id=call.from_user.id).first()
    cat = Category.objects.filter(id=category_id).first()
    if not user or not cat:
        bot.answer_callback_query(call.id, "Xatolik.")
        return

    Transaction.objects.create(
        user=user,
        amount=data['amount'],
        type=data['type'],
        note=data['note'],
        category=cat,
        date=timezone.now().date(),
    )
    del user_data[chat_id]

    sign = '➕' if data['type'] == 'income' else '➖'
    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text=(
            f"✅ *Saqlandi!*\n\n"
            f"{sign} `{fmt_money(data['amount'])}` UZS\n"
            f"📂 {cat.name}\n"
            f"📝 _{data['note']}_"
        ),
        parse_mode="Markdown",
    )


if __name__ == '__main__':
    print("Bot ishga tushdi...")
    bot.infinity_polling(skip_pending=True)
