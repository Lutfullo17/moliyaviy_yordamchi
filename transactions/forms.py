from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from categories.models import Category

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

    def __init__(self, *args, user=None, **kwargs):
        self._user = user
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["category"].queryset = Category.objects.filter(
                Q(user=user) | Q(is_default=True)
            ).order_by("type", "name")

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get("category")
        t_type = cleaned.get("type")
        if category and t_type and category.type != t_type:
            raise ValidationError({"category": ("Kategoriya turiga mos emas.")})
        if self._user and category and category.user_id and category.user_id != self._user.id:
            raise ValidationError({"category": ("Bu kategoriyaga ruxsat yo'q.")})
        return cleaned

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