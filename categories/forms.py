from django import forms
from .models import Category


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']

    def clean_name(self):
        name = self.cleaned_data.get('name')

        if not name or not name.strip():
            raise forms.ValidationError("Name cannot be empty")

        return name.strip().lower()