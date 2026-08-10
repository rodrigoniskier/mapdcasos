from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import ClinicalCase, User


class SeedAndSignupTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_cases', verbosity=0)

    def test_seed_has_80_cases(self):
        self.assertEqual(ClinicalCase.objects.count(), 80)
        for category, _ in ClinicalCase.Category.choices:
            self.assertEqual(ClinicalCase.objects.filter(category=category).count(), 20)

    def test_student_signup_uses_rgm_as_username(self):
        response = self.client.post(reverse('signup'), {'rgm': '123456', 'nome': 'Aluno Teste', 'turma': 'T01', 'password1': 'SenhaForte!2026', 'password2': 'SenhaForte!2026'})
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(rgm='123456')
        self.assertEqual(user.username, '123456')
        self.assertFalse(user.is_superuser)
