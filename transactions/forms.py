from django import forms
from .models import Transaction
import decimal


class TransactionForm(forms.ModelForm):
    # CharField sifatida qabul qilamiz - 1,000,000 formatini qo'llab-quvvatlash uchun
    amount = forms.CharField(
        max_length=25,
        widget=forms.TextInput(attrs={
            'inputmode': 'numeric',
            'class': 'money-input w-full px-4 py-3 rounded-xl border border-slate-200 '
                     'focus:ring-4 focus:ring-blue-50 focus:border-blue-500 outline-none '
                     'transition-all font-bold text-lg',
            'placeholder': 'Masalan: 1,000,000',
        })
    )

    class Meta:
        model = Transaction
        fields = ['amount', 'type', 'category', 'note', 'date']

    def clean_amount(self):
        raw = self.cleaned_data.get('amount', '')
        # Vergul va bo'sh joylarni olib tashlash
        cleaned = str(raw).replace(',', '').replace(' ', '').strip()
        try:
            amount = decimal.Decimal(cleaned)
        except (decimal.InvalidOperation, ValueError):
            raise forms.ValidationError("To'g'ri summa kiriting (masalan: 1,000,000)")

        if amount <= 0:
            raise forms.ValidationError("Summa 0 dan katta bo'lishi kerak")

        return amount