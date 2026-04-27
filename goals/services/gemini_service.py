from openai import OpenAI
from django.conf import settings

client = OpenAI(
    api_key=settings.OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)


def get_ai_advice(goal, daily_needed, days_left):
    try:
        prompt = f"""
        Sen professional moliyaviy maslahatchisan.
        Faqat o‘zbek tilida javob ber.

        Maqsad: {goal.title}
        Kerakli summa: {goal.target_amount}
        Hozirgi summa: {goal.current_amount}
        Qolgan kun: {days_left}
        Kunlik yig‘ish kerak: {daily_needed}

        1 ta qisqa tahlil yoz.
        Keyin 3 ta tavsiya yoz (raqam bilan).
        """

        response = client.chat.completions.create(
            model="deepseek/deepseek-chat",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        text = response.choices[0].message.content.strip()

        lines = [l.strip() for l in text.split("\n") if l.strip()]

        return lines[0], lines[1:]

    except Exception as e:
        print("OpenRouter error:", e)
        return (
            "AI ishlamayapti",
            ["Keyinroq urinib ko‘ring"]
        )