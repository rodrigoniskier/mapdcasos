import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


def normalize_identifier(value: str) -> str:
    """Normalize RGM/login input so formatting differences do not break access."""
    value = (value or '').strip().lower()
    return re.sub(r'[\s.\-_/]+', '', value)


def _identifier_already_exists(identifier: str) -> bool:
    # Direct lookups cover all new records efficiently.
    if User.objects.filter(rgm__iexact=identifier).exists() or User.objects.filter(username__iexact=identifier).exists():
        return True
    # Compatibility path for users created before RGM normalization was added.
    for rgm, username in User.objects.filter(is_superuser=False).values_list('rgm', 'username'):
        if normalize_identifier(rgm or '') == identifier or normalize_identifier(username or '') == identifier:
            return True
    return False


class RGMAuthenticationForm(AuthenticationForm):
    def clean(self):
        raw_username = (self.cleaned_data.get('username') or '').strip()
        normalized = normalize_identifier(raw_username)
        if raw_username:
            # New accounts are stored normalized. If this direct lookup misses,
            # preserve compatibility with RGMs saved with punctuation previously.
            candidate = User.objects.filter(username__iexact=normalized).only('username').first()
            if candidate is None:
                candidate = User.objects.filter(username__iexact=raw_username).only('username').first()
            if candidate is None:
                for user in User.objects.filter(is_superuser=False).only('username'):
                    if normalize_identifier(user.username) == normalized:
                        candidate = user
                        break
            self.cleaned_data['username'] = candidate.username if candidate else normalized
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
        if _identifier_already_exists(rgm):
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
