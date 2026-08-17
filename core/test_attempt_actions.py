from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .decision_trees import get_tree
from .models import ClinicalCase, DecisionAnswer, Encounter, Message, User


def make_case(order=1):
    return ClinicalCase.objects.create(
        code=f'B{order:02d}',
        category=ClinicalCase.Category.BACTERIA,
        order=order,
        public_title='Caso de teste',
        patient_name='Paciente Teste',
        age=30,
        sex='Feminino',
        difficulty=ClinicalCase.Difficulty.BASIC,
        complaint='Queixa inicial do paciente.',
        pathogen='Agente de teste',
        diagnosis='Diagnóstico de teste',
        master_context={'variant_note': 'Variação de teste.'},
        expected_management='Conduta de teste.',
        active=True,
    )


class CompletedAttemptActionsTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username='90001',
            password='senha-forte',
            rgm='90001',
            first_name='Aluno',
        )
        self.case = make_case()
        self.client.force_login(self.student)

    def _completed_ai_encounter(self):
        encounter = Encounter.objects.create(
            student=self.student,
            case=self.case,
            mode=Encounter.Mode.AI,
            status=Encounter.Status.COMPLETED,
            outcome=Encounter.Outcome.ADEQUATE,
            score=88,
            completed_at=timezone.now(),
            final_feedback={'case_summary': 'Resumo', 'care_summary': 'Atendimento'},
            patient_interaction_id='old-provider-state',
            patient_interaction_model='old-model',
        )
        Message.objects.create(encounter=encounter, role=Message.Role.PATIENT, content='Olá.')
        Message.objects.create(encounter=encounter, role=Message.Role.STUDENT, content='Conte sua queixa.')
        Message.objects.create(encounter=encounter, role=Message.Role.PATIENT, content='Estou com dor.')
        return encounter

    def _completed_tree_encounter(self):
        encounter = Encounter.objects.create(
            student=self.student,
            case=self.case,
            mode=Encounter.Mode.TREE,
            status=Encounter.Status.COMPLETED,
            outcome=Encounter.Outcome.ADEQUATE,
            score=100,
            completed_at=timezone.now(),
            final_feedback={'summary': 'Excelente', 'points': 24, 'max_points': 24},
        )
        tree = get_tree(self.case)
        for node in tree['nodes']:
            best = next(option for option in node['options'] if option['quality'] == DecisionAnswer.Quality.BEST)
            DecisionAnswer.objects.create(
                encounter=encounter,
                node_id=node['id'],
                prompt=node['prompt'],
                selected_option_id=best['id'],
                selected_text=best['text'],
                quality=best['quality'],
                points=best['points'],
                feedback=best['feedback'],
            )
        return encounter

    def test_ai_transcript_is_available_only_after_completion(self):
        encounter = self._completed_ai_encounter()
        response = self.client.get(reverse('ai_transcript', args=[self.case.id]), secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'case_transcript.html')
        self.assertContains(response, 'Conte sua queixa.')
        self.assertContains(response, 'Estou com dor.')

        encounter.status = Encounter.Status.OPEN
        encounter.save(update_fields=['status'])
        response = self.client.get(reverse('ai_transcript', args=[self.case.id]), secure=True)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('case_chat', args=[self.case.id]))

    def test_restart_ai_case_clears_attempt_and_recreates_initial_patient_message(self):
        encounter = self._completed_ai_encounter()
        response = self.client.post(reverse('restart_ai_case', args=[self.case.id]), secure=True)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('case_chat', args=[self.case.id]))

        encounter.refresh_from_db()
        self.assertEqual(encounter.status, Encounter.Status.OPEN)
        self.assertEqual(encounter.outcome, Encounter.Outcome.NOT_ASSESSED)
        self.assertIsNone(encounter.score)
        self.assertEqual(encounter.final_feedback, {})
        self.assertIsNone(encounter.completed_at)
        self.assertEqual(encounter.patient_interaction_id, '')
        self.assertEqual(encounter.patient_interaction_model, '')
        self.assertEqual(encounter.messages.count(), 1)
        first = encounter.messages.get()
        self.assertEqual(first.role, Message.Role.PATIENT)
        self.assertEqual(first.content, self.case.complaint)
        self.assertEqual(self.client.session['study_mode'], Encounter.Mode.AI)

    def test_restart_actions_require_post(self):
        self._completed_ai_encounter()
        response = self.client.get(reverse('restart_ai_case', args=[self.case.id]), secure=True)
        self.assertEqual(response.status_code, 405)

    def test_tree_history_and_restart(self):
        encounter = self._completed_tree_encounter()
        response = self.client.get(reverse('tree_transcript', args=[self.case.id]), secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tree_transcript.html')
        self.assertEqual(len(response.context['answers']), 6)

        response = self.client.post(reverse('restart_tree_case', args=[self.case.id]), secure=True)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('decision_tree_case', args=[self.case.id]))

        encounter.refresh_from_db()
        self.assertEqual(encounter.status, Encounter.Status.OPEN)
        self.assertEqual(encounter.outcome, Encounter.Outcome.NOT_ASSESSED)
        self.assertIsNone(encounter.score)
        self.assertEqual(encounter.decision_answers.count(), 0)
        self.assertEqual(self.client.session['study_mode'], Encounter.Mode.TREE)

    def test_tree_history_redirects_while_case_is_open(self):
        Encounter.objects.create(
            student=self.student,
            case=self.case,
            mode=Encounter.Mode.TREE,
        )
        session = self.client.session
        session['study_mode'] = Encounter.Mode.TREE
        session.save()

        response = self.client.get(reverse('tree_transcript', args=[self.case.id]), secure=True)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('decision_tree_case', args=[self.case.id]))
