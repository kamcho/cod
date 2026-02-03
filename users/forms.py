from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User

from django.core.exceptions import ValidationError
import re

class RegistrationStep1Form(forms.ModelForm):
    password1 = forms.CharField(label="4-Digit PIN", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('email', 'phone_number')

    def clean_password1(self):
        pin = self.cleaned_data.get('password1')
        if not re.fullmatch(r'\d{4}', pin):
            raise ValidationError("PIN must be exactly 4 digits.")
        return pin

class RegistrationStep2Form(forms.ModelForm):
    class Meta:
        model = User
        fields = ('gamer_tag', 'full_name', 'county')

    def clean_gamer_tag(self):
        gamer_tag = self.cleaned_data.get('gamer_tag')
        if not gamer_tag:
            raise ValidationError("Gamer Tag is required.")
        if User.objects.filter(gamer_tag=gamer_tag).exists():
            raise ValidationError("This Gamer Tag is already taken.")
        return gamer_tag

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('gamer_tag', 'email', 'phone_number', 'full_name', 'county')
