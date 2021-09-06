from django import forms
from .models import Cookie


class PostForm(forms.ModelForm):
    class Meta:
        model = Cookie
        fields = (
        'title', 'link', 'user_login', 'user_password')
