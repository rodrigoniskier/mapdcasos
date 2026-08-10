from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .forms import normalize_identifier
from .models import ClinicalCase, User


class SeedAndSignupTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_cases', verbosity=0)

    def test_seed_has_80_cases(self):
        self.assertEqual(ClinicalCase.objects.count(), 80)
        for category, _ in ClinicalCase.Category.choices:
            self.assertEqual(ClinicalCase.objects.filter(category=category).count(), 20)

    def test_identifier_normalization(self):
        self.assertEqual(normalize_identifier(' 123.456-7 '), '1234567')
        self.assertEqual(normalize_identifier('Rodrigo'), 'rodrigo')

    def test_student_signup_uses_normalized_rgm_as_username(self):
        response = self.client.post(
            reverse('signup'),
            {
                'rgm': '123.456-7',
                'nome': 'Aluno Teste',
                'turma': 'T01',
                'password1': 'SenhaForte!2026',
                'password2': 'SenhaForte!2026',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('login'))
        user = User.objects.get(rgm='1234567')
        self.assertEqual(user.username, '1234567')
        self.assertFalse(user.is_superuser)

    def test_login_accepts_formatted_rgm(self):
        User.objects.create_user(
            username='9876543',
            rgm='9876543',
            password='SenhaForte!2026',
            role=User.Role.STUDENT,
        )
        response = self.client.post(
            reverse('login'),
            {'username': ' 987.654-3 ', 'password': 'SenhaForte!2026'},
        )
        self.assertEqual(response.status_code, 302)

    def test_login_accepts_legacy_formatted_stored_rgm(self):
        User.objects.create_user(
            username='555.444-3',
            rgm='555.444-3',
            password='SenhaForte!2026',
            role=User.Role.STUDENT,
        )
        response = self.client.post(
            reverse('login'),
            {'username': '5554443', 'password': 'SenhaForte!2026'},
        )
        self.assertEqual(response.status_code, 302)

    def test_duplicate_rgm_is_rejected_after_normalization(self):
        User.objects.create_user(
            username='111.222-3',
            rgm='111.222-3',
            password='SenhaForte!2026',
            role=User.Role.STUDENT,
        )
        response = self.client.post(
            reverse('signup'),
            {
                'rgm': '1112223',
                'nome': 'Outro Aluno',
                'turma': 'T02',
                'password1': 'OutraSenha!2026',
                'password2': 'OutraSenha!2026',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Este RGM já está cadastrado')
