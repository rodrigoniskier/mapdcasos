import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


def normalize_identifier(value: str) -> str:
    """Normalize RGM/login input so formatting differences do not break access."""
    value = (value or '').strip().lower()
    return re.sub(r'[\s.\-_/]+', '', value)


class RGMAuthenticationForm(AuthenticationForm):
    def clean(self):
        username = self.cleaned_data.get('username')
        if username:
            self.cleaned_data['username'] = normalize_identifier(username)
        return super().clean()


class StudentSignUpForm(UserCreationForm):
    rgm = forms.CharField(label='RGM', max_length=30)
    nome = forms.CharField(label='Nome completo', max_length=150)
    turma = forms.CharField(label='Turma', max_length=80)

    class Meta:
        model = User
        fields = ('rgm', 'nome', 'turma', 'password1', 'password2')

    def clean_rgm(self):
        rgm = normalize_identifier(self.cleaned_data['rgm'])
        if not rgm:
            raise forms.ValidationError('Informe um RGM válido.')
        if User.objects.filter(rgm__iexact=rgm).exists() or User.objects.filter(username__iexact=rgm).exists():
            raise forms.ValidationError('Este RGM já está cadastrado. Se o cadastro anterior foi concluído, tente entrar com sua senha.')
        return rgm

    def save(self, commit=True):
        user = super().save(commit=False)
        user.rgm = normalize_identifier(self.cleaned_data['rgm'])
        user.username = user.rgm
        full_name = self.cleaned_data['nome'].strip().split(maxsplit=1)
        user.first_name = full_name[0]
        user.last_name = full_name[1] if len(full_name) > 1 else ''
        user.turma = self.cleaned_data['turma'].strip()
        user.role = User.Role.STUDENT
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
        return user
