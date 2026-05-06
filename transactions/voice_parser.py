"""Parse free-form Uzbek voice/text into structured transaction data.

Supports:
  - Regex / keyword parsing (offline, fast)
  - Synonym buckets -> default category names in DB
  - Optional Gemini for hard cases when API key is set
  - Multiple phrases in one utterance (`... va ...`; `;` bo'yicha)
"""
from __future__ import annotations

import json
import re
from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.db.models import Q

from categories.models import Category


_INCOME_KEYWORDS = frozenset(
    {
        "daromad",
        "kirim",
        "tushdi",
        "olindi",
        "keldi",
        "kelib qoldi",
        "tushumar",
        "maosh",
        "oylik",
        "bonus",
        "stipendiya",
        "dividend",
        "qaytdi",
        "qaytardi",
        "sotdim",
        "sotildi",
        "pul tushdi",
        "pul keldi",
    }
)

_EXPENSE_KEYWORDS = frozenset(
    {
        "xarajat",
        "chiqim",
        "sarfl",
        "sarfladim",
        "sarflangan",
        "to'ladim",
        "to'lash",
        "to'lov",
        "harid",
        "sotib",
        "oldsam",
        "berdim",
        "ketdi",  # "pul ketdi"
        "olib keldim",
        "sotvol",
    }
)

# Muayyan iboralar tartib bilan (expense uchun "olib keldim" da "keldi" bo'lmasligi uchun)
_EXPENSE_HINTS_PRIORITY = (
    r"olib\s+keld",
    r"sarflad",
    r"harid\s+qild",
    r"to'?lad",
    r"sotib\s+old",
    r"xarajat",
    r"tushlikka\b",  # "tushlikka N ming"
    r"\bunga\b.*sarfl",
)

_INCOME_HINTS_PRIORITY = (
    r"maosh.*kel",
    r"pul.*(tushdi|keldi)",
    r"(tushdi|keldi).*maosh",
    r"tushumar",
)


_NUMBER_WORDS = {
    "bir": 1,
    "ikki": 2,
    "uch": 3,
    "to'rt": 4,
    "tort": 4,
    "besh": 5,
    "olti": 6,
    "yetti": 7,
    "sakkiz": 8,
    "to'qqiz": 9,
    "toqqiz": 9,
    "o'n": 10,
    "on": 10,
    "yigirma": 20,
    "o'ttiz": 30,
    "ottiz": 30,
    "qirq": 40,
    "ellik": 50,
    "oltmish": 60,
    "yetmish": 70,
    "sakson": 80,
    "to'qson": 90,
    "toqson": 90,
    "yuz": 100,
}
_MULTIPLIER_WORDS = {
    "ming": 1_000,
    "million": 1_000_000,
    "mln": 1_000_000,
    "milliard": 1_000_000_000,
}


# Har bir qator: (Kalit tokenlar/kichik fraze lar, canonical_category_name)
_INCOME_BUCKET_CATS: tuple[tuple[frozenset[str], str], ...] = (
    (frozenset({"maosh", "maoshi", "ish haqi", "oylik"}), "maosh"),
    (frozenset({"bonus"}), "bonus"),
    (frozenset({"stipendiya", "stipend"}), "stipendiya"),
    (frozenset({"sotdim", "sotildi", "mahsulot"}), "sotish-daromad"),
    (
        frozenset({"pul qayt", "qarz qayt", "qaytarildi", "qaytardi"}),
        "qarz-qaytarildi",
    ),
)


_EXPENSE_BUCKET_CATS: tuple[tuple[frozenset[str], str], ...] = (
    (
        frozenset({"olib keldim", "olib oldim"}),
        "ovqat-ichimlik",
    ),
    (frozenset({"tushlik", "kahvalt", "nonushta"}), "tushlik"),
    (frozenset({"café", "cafe", "restoran"}), "kafe-restoran"),
    (frozenset({"supermarket", "oziq"}), "ovqat-ichimlik"),
    (frozenset({"taksi", "taxi"}), "taksi"),
    (frozenset({"avtobus", "metro", "marshrut"}), "transport"),
    (frozenset({"kvartira", "ijara", "turar joy"}), "uy-ijara"),
    (frozenset({"kommunal", "elektr", "gaz", "suv"}), "kommunal"),
    (frozenset({"internet", "telegram", "aloqa"}), "internet-aloqa"),
    (frozenset({"dori", "shifokor", "klinika", "bemor"}), "tibbiyot"),
    (frozenset({"bollar uchun", "bollar", "maktab uchun", "forma"}), "bolalar-chiqimlari"),
    (frozenset({"universitet", "kurslari", "kitobxonlik", "oqish"}), "ta'lim"),
    (frozenset({"kiyim", "paypoq", "poyafzal"}), "kiyim-kechak"),
    (frozenset({"salon", "sartarosh", "gozallik", "kosmet"}), "gozallik"),
    (frozenset({"sport", "zali", "gimnast"}), "sport"),
    (frozenset({"safar", "sayohat", "bilet", "hotel"}), "sayohat"),
    (frozenset({"gilam", "sovun"}), "uy-rozg'or"),
    (frozenset({"mashina", "avto remont", "benzin"}), "avto"),
    (frozenset({"sugirta", "insurance"}), "sugirta"),
    (frozenset({"kredit", "ipoteka"}), "kredit-to'lovi"),
    (frozenset({"onlayn", "amazon", "olx", "zakaz"}), "onlayn-harid"),
    (frozenset({"xayriya", "ehson"}), "xayriya"),
)


def _text_has_hint(lowered_text: str, hint: str) -> bool:
    h = hint.lower().strip()
    if len(h) < 5 and " " not in h:
        return bool(re.search(rf"(?<![a-z'ʻ’`]){re.escape(h)}(?![a-z'ʻ’`])", lowered_text))
    return h in lowered_text


def _norm_tokens(text: str) -> str:
    return (
        text.lower()
        .replace("`", "'")
        .replace("’", "'")
        .replace("ʻ", "'")
    )


def _words_to_number(text: str) -> Optional[Decimal]:
    tokens = re.findall(r"[a-zA-Zoʻ'`’oʻ]+|\d+", _norm_tokens(text))

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
    text_norm = text
    lc = text_norm.lower().replace(",", "")

    m = re.search(r"(\d+(?:[\.,]\d+)?)\s*k\b", lc)
    if m:
        return Decimal(m.group(1).replace(",", ".")) * 1000

    digit_match = re.search(
        r"\d+(?:[\s']\d{3})*(?:[.,]\d+)?|\d+[.,]\d+",
        text_norm.replace(",", ""),
    )
    if digit_match:
        raw = digit_match.group(0).replace(" ", "").replace("'", "").replace(",", ".")
        if raw.count(".") > 1:
            raw = raw.replace(".", "", raw.count(".") - 1)
        try:
            value = Decimal(raw)
        except Exception:
            value = None
        if value and value > 0:
            tail = lc[digit_match.end() :] if lc else ""
            tail = tail.lstrip(" .:-")
            for word, mult in _MULTIPLIER_WORDS.items():
                if tail.startswith(word):
                    value = value * mult
                    break
            return value

    return _words_to_number(text_norm)


def _detect_type(text: str) -> str:
    t = _norm_tokens(text)
    if text.strip().startswith("+"):
        return "income"
    if text.strip().startswith("-"):
        return "expense"

    if any(re.search(pat, t) for pat in _EXPENSE_HINTS_PRIORITY):
        for pat in _INCOME_HINTS_PRIORITY:
            if re.search(pat, t):
                return "expense"
        return "expense"

    for pat in _INCOME_HINTS_PRIORITY:
        if re.search(pat, t):
            return "income"

    if any(kw in t for kw in _INCOME_KEYWORDS):
        hits_income = True
        for bad in ("olib kel", "olib keld"):
            if bad in t:
                hits_income = False
                break
        if hits_income:
            return "income"

    if any(kw in t for kw in _EXPENSE_KEYWORDS):
        return "expense"
    return "expense"


def _category_queryset(user):
    return Category.objects.filter(Q(user=user) | Q(is_default=True))


def _match_category(text: str, user, t_type: str) -> Optional[Category]:
    lowered = _norm_tokens(text)
    qs = _category_queryset(user).filter(type=t_type)
    buckets = _INCOME_BUCKET_CATS if t_type == "income" else _EXPENSE_BUCKET_CATS

    for tokens, canon_name in buckets:
        if any(_text_has_hint(lowered, tok) for tok in tokens):
            c = qs.filter(name=canon_name).first()
            if c:
                return c

    for cat in qs:
        nm = (cat.name or "").lower()
        if nm and nm in lowered:
            return cat
    return None


def _parse_one_fragment(text: str, user, try_ai_fallback: bool) -> Optional[dict]:
    fragment = text.strip()
    if not fragment:
        return None

    amount = _extract_amount(fragment)
    if not amount or amount <= 0:
        if try_ai_fallback:
            return _ai_parse(fragment, user)
        return None

    t_type = _detect_type(fragment)
    category = _match_category(fragment, user, t_type)

    note = fragment
    if len(note) > 200:
        note = note[:200]

    out = {
        "amount": amount,
        "type": t_type,
        "category_id": category.id if category else None,
        "category_name": category.name if category else None,
        "note": note,
    }
    return out


def _split_transaction_fragments(text: str) -> list[str]:
    raw = text.strip()
    if not raw:
        return []

    normalized = re.sub(r"[\r\n|]+", ";", raw)
    blocks = [p.strip() for p in re.split(r"[;\u2022•]+", normalized) if p.strip()]

    fragments: list[str] = []
    for block in blocks:
        va_rx = r"\s+va\s+"
        if not re.search(va_rx, block, flags=re.I):
            fragments.append(block)
            continue

        va_parts = [p.strip() for p in re.split(va_rx, block, flags=re.I) if p.strip()]
        amt_parts = []
        for p in va_parts:
            a = _extract_amount(p)
            if a is not None and a > 0:
                amt_parts.append(p)
        if len(amt_parts) >= 2:
            fragments.extend(amt_parts)
        else:
            fragments.append(block)

    if not fragments:
        return [raw]
    if len(fragments) > 1:
        with_amt = []
        for f in fragments:
            a = _extract_amount(f)
            if a is not None and a > 0:
                with_amt.append(f)
        return with_amt or fragments
    return fragments


def parse_all_transactions_text(text: str, user, try_ai_fallback: bool = False) -> list[dict]:
    """Bir ovoz/sessionda bir nechta qator: `...; ...` yoki `... va ...`."""
    if not text or not text.strip():
        return []
    results: list[dict] = []
    for frag in _split_transaction_fragments(text):
        parsed = _parse_one_fragment(frag, user=user, try_ai_fallback=try_ai_fallback)
        if parsed:
            results.append(parsed)
    if results:
        return results
    if try_ai_fallback:
        parsed = _ai_parse(text.strip(), user)
        return [parsed] if parsed else []
    parsed = _parse_one_fragment(text.strip(), user=user, try_ai_fallback=True)
    return [parsed] if parsed else []


def parse_transaction_text(text: str, user) -> Optional[dict]:
    """Bitta tranzaksiya (eski API bilan moslik). AI fallback yoqilgan."""
    items = parse_all_transactions_text(text, user=user, try_ai_fallback=True)
    return items[0] if items else None


def _ai_parse(text: str, user) -> Optional[dict]:
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        return None
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        cats = list(_category_queryset(user))
        cat_lines = "\n".join(f"- {c.id}: {c.name} ({c.type})" for c in cats) or "(yo'q)"

        prompt = (
            "Sen moliya botsan. Tranzaksiyani O'zbekcha matndan ajrat.\n"
            "Faqat JSON qaytarsan.\nKalitlar: amount (UZS son), type ('income'|'expense'), "
            "category_id (ro'yhatdan, yoki null), note.\n\n"
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
                "Quyidagi ovozni O'zbek tilida matnga aylantirish. Faqat matn.",
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
            ],
        )
        text = (resp.text or "").strip()
        return text or None
    except Exception as e:
        print("Transcribe error:", e)
        return None
