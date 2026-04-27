from django import forms
from .models import Reminder

class ReminderForm(forms.ModelForm):
    class Meta:
        model = Reminder
        fields = ['title', 'description', 'remind_time']
        widgets = {
            'remind_time': forms.TextInput(attrs={
                'id': 'date_picker',
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-4 focus:ring-amber-50 focus:border-amber-400 outline-none transition-all pr-10',
                'placeholder': 'Vaqtni tanlang...',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'rows': '3',
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-4 focus:ring-amber-50 focus:border-amber-400 outline-none transition-all',
                'placeholder': "Qo'shimcha ma'lumotlar..."
            }),
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-4 focus:ring-amber-50 focus:border-amber-400 outline-none transition-all',
                'placeholder': 'Masalan: Kvartira to\'lovi'
            })
        }
