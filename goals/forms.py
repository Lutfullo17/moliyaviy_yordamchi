from django import forms

from .models import Goal


class GoalForm(forms.ModelForm):
    deadline = forms.DateField(
        label="Muddat",
        input_formats=[
            "%d/%m/%Y",
            "%d.%m.%Y",
            "%Y-%m-%d",
        ],
        widget=forms.TextInput(
            attrs={
                "id": "date_picker",
                "class": "w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-4 "
                "focus:ring-emerald-100 focus:border-emerald-500 outline-none transition-all pr-10",
                "placeholder": "Sana tanlang...",
                "required": True,
            },
        ),
    )

    class Meta:
        model = Goal
        fields = ["title", "target_amount", "current_amount", "deadline"]
