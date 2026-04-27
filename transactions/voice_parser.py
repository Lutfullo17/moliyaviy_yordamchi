"""Parse free-form Uzbek voice/text into structured transaction data.

Supports both:
  - Simple regex-based parsing as a fast offline fallback (handles plus/minus,
    digits-and-words like "besh ming", common keywords).
  - Optional Gemini-powered parsing for complex sentences when the API key
    is configured.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.db.models import Q

from categories.models import Category


_INCOME_KEYWORDS = {
    "daromad", "kirim", "tushdi", "oldim", "olindi", "maosh", "oylik",
    "bonus", "stipendiya", "sovg'a", "sotdim",
}
_EXPENSE_KEYWORDS = {
    "xarajat", "chiqim", "sarf", "to'ladim", "to'lov", "sotib", "harid",
    "harid qildim", "berdim", "ketdi", "olib keldim",
}

_NUMBER_WORDS = {
    "bir": 1, "ikki": 2, "uch": 3, "to'rt": 4, "tort": 4, "besh": 5,
    "olti": 6, "yetti": 7, "sakkiz": 8, "to'qqiz": 9, "toqqiz": 9,
    "o'n": 10, "on": 10, "yigirma": 20, "o'ttiz": 30, "ottiz": 30,
    "qirq": 40, "ellik": 50, "oltmish": 60, "yetmish": 70,
    "sakson": 80, "to'qson": 90, "toqson": 90, "yuz": 100,
}
_MULTIPLIER_WORDS = {
    "ming": 1_000,
    "million": 1_000_000,
    "mln": 1_000_000,
    "milliard": 1_000_000_000,
}


def _words_to_number(text: str) -> Optional[Decimal]:
    """Convert "besh ming" / "ikki yuz ming" style phrases to a Decimal."""
    tokens = re.findall(r"[a-zA-Zo'`’ʻ]+", text.lower())
    tokens = [t.replace("`", "'").replace("’", "'").replace("ʻ", "'") for t in tokens]

    if not tokens:
        return None

    total = 0
    current = 0
    matched_any = False
    for tok in tokens:
        if tok in _NUMBER_WORDS:
            current += _NUMBER_WORDS[tok]
            matched_any = True
        elif tok in _MULTIPLIER_WORDS:
            mult = _MULTIPLIER_WORDS[tok]
            current = (current or 1) * mult
            total += current
            current = 0
            matched_any = True
    total += current
    return Decimal(total) if matched_any and total > 0 else None


def _extract_amount(text: str) -> Optional[Decimal]:
    """Extract numeric amount from text. Tries digits first, then words."""
    cleaned = text.lower().replace(",", "").replace(" ", "")

    # 500k / 500 ming style abbreviations
    m = re.search(r"(\d+(?:\.\d+)?)\s*k\b", text.lower())
    if m:
        return Decimal(m.group(1)) * 1000

    digit_match = re.search(r"\d+(?:[\.\s]\d{3})*(?:\.\d+)?", text.replace(",", ""))
    if digit_match:
        raw = digit_match.group(0).replace(" ", "")
        try:
            value = Decimal(raw)
        except Exception:
            value = None
        if value:
            # Heuristic: "5 ming", "5 mln" — multiply
            tail = text.lower().split(digit_match.group(0), 1)[-1].strip()
            for word, mult in _MULTIPLIER_WORDS.items():
                if tail.startswith(word):
                    value = value * mult
                    break
            return value

    return _words_to_number(cleaned)


def _detect_type(text: str) -> str:
    lowered = text.lower()
    if lowered.strip().startswith("+"):
        return "income"
    if lowered.strip().startswith("-"):
        return "expense"
    for kw in _INCOME_KEYWORDS:
        if kw in lowered:
            return "income"
    for kw in _EXPENSE_KEYWORDS:
        if kw in lowered:
            return "expense"
    return "expense"  # default


def _match_category(text: str, user, t_type: str):
    qs = Category.objects.filter(Q(user=user) | Q(is_default=True), type=t_type)
    lowered = text.lower()
    best = None
    for cat in qs:
        if cat.name and cat.name.lower() in lowered:
            best = cat
            break
    return best


def parse_transaction_text(text: str, user) -> Optional[dict]:
    """Parse text into transaction fields. Returns None if amount can't be found."""
    if not text:
        return None

    amount = _extract_amount(text)
    if not amount or amount <= 0:
        # Try AI fallback
        ai = _ai_parse(text, user)
        if ai:
            return ai
        return None

    t_type = _detect_type(text)
    category = _match_category(text, user, t_type)

    note = text.strip()
    if len(note) > 200:
        note = note[:200]

    return {
        "amount": amount,
        "type": t_type,
        "category_id": category.id if category else None,
        "category_name": category.name if category else None,
        "note": note,
    }


def _ai_parse(text: str, user) -> Optional[dict]:
    """Use Gemini to parse — only used if local parsing fails."""
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        return None
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        cats = list(Category.objects.filter(Q(user=user) | Q(is_default=True)))
        cat_lines = "\n".join(f"- {c.id}: {c.name} ({c.type})" for c in cats) or "(yo'q)"

        prompt = (
            "Sen moliya botisan. Foydalanuvchi tranzaksiyani o'zbek tilida aytadi. "
            "Faqat JSON qaytar — boshqa hech narsa. Kalitlar: amount (son, UZS), "
            "type ('income' yoki 'expense'), category_id (ro'yxatdan, yoki null), note (qisqa matn). "
            f"Kategoriyalar:\n{cat_lines}\n\nMatn: {text}"
        )
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        data = json.loads(resp.text)
        amount = Decimal(str(data.get("amount", 0)))
        if amount <= 0:
            return None
        t_type = data.get("type", "expense")
        if t_type not in ("income", "expense"):
            t_type = "expense"
        cat_id = data.get("category_id")
        cat_name = None
        if cat_id:
            c = next((c for c in cats if c.id == cat_id), None)
            if c:
                cat_name = c.name
            else:
                cat_id = None
        return {
            "amount": amount,
            "type": t_type,
            "category_id": cat_id,
            "category_name": cat_name,
            "note": (data.get("note") or text)[:200],
        }
    except Exception as e:
        print("AI parse error:", e)
        return None


def transcribe_audio_bytes(audio_bytes: bytes, mime_type: str = "audio/ogg") -> Optional[str]:
    """Transcribe an audio blob (e.g. Telegram OGG) to text via Gemini."""
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        return None
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                "Quyidagi ovozni o'zbek tilida matnga aylantir. Faqat matnni qaytar.",
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
            ],
        )
        text = (resp.text or "").strip()
        return text or None
    except Exception as e:
        print("Transcribe error:", e)
        return None
