import google.generativeai as genai
from django.conf import settings

genai.configure(api_key=settings.GEMINI_API_KEY)


def get_ai_advice(goal, daily_needed, days_left):
    model = genai.GenerativeModel("gemini-2.0-flash-lite")

    prompt = f"""
Sen professional moliyaviy maslahatchisan.

Maqsad: {goal.title}
Kerakli summa: {goal.target_amount}
Hozirgi summa: {goal.current_amount}
Qolgan kun: {days_left}
Kunlik yig‘ish kerak: {daily_needed}

1 ta qisqa tahlil yoz.
Keyin 3 ta tavsiya yoz (raqam bilan).
"""

    response = model.generate_content(prompt)

    text = response.text.strip()
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    advice = lines[0] if lines else "AI javob yo‘q"
    recommendations = lines[1:]

    return advice, recommendations