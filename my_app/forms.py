from django import forms
from .models import Squad


class SquadForm(forms.ModelForm):
    class Meta:
        model = Squad
        fields = ['squad_name', 'coach']
        widgets = {
            'squad_name': forms.TextInput(attrs={'class': 'auth-input', 'placeholder': 'e.g. Sunday League XI'}),
            'coach': forms.Select(attrs={'class': 'auth-input'}),
        }
