from django import forms
from .models import DayPlan  # Modelingiz nomi boshqacha bo'lsa o'zgartiring


class TaskForm(forms.ModelForm):
    class Meta:
        model = DayPlan
        fields = ['title', 'description', 'start_time', 'end_time', 'priority']  # Kerakli fieldlarni yozing

        widgets = {
            'start_time': forms.TimeInput(
                attrs={'type': 'time',
                       'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none'},
                format='%H:%M'
            ),
            'end_time': forms.TimeInput(
                attrs={'type': 'time',
                       'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none'},
                format='%H:%M'
            ),
            # Boshqa fieldlar uchun ham klasslar qo'shishingiz mumkin
            'title': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg'}),
            'description': forms.Textarea(attrs={'class': 'w-full px-4 py-2 border rounded-lg', 'rows': 3}),
        }