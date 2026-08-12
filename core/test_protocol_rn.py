import json
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings

from core.models import AIJob, ClinicalCase, Encounter, Message, User
from core.services.ai_gateway import (
    AIErrorType,
    check_rate_limit,
    classify_exception,
    policy_for,
    start_background_interaction,
    validate_output,
)
from core.services.ai_jobs import queue_patient_job
from core.services.ai_schemas import EvaluationAIResponse, PatientAIResponse
from core.services.prompts import patient_system


class FakeHTTPError(Exception):
    def __init__(self, status_code, message=None):
        self.status_code = status_code
        super().__init__(message or f'HTTP {status_code}')


class AIGatewayProtocolTests(SimpleTestCase):
    def test_error_router_classifies_quota_and_client_errors(self):
        self.assertEqual(classify_exception(FakeHTTPError(429)), AIErrorType.QUOTA)
        self.assertEqual(classify_exception(FakeHTTPError(503)), AIErrorType.TRANSIENT)
        self.assertEqual(classify_exception(FakeHTTPError(400)), AIErrorType.CLIENT)
        self.assertEqual(classify_exception(FakeHTTPError(401)), AIErrorType.AUTH)

    def test_error_router_treats_missing_model_as_routable(self):
        error = FakeHTTPError(404, "Model 'gemini-new-model' not found")
        self.assertEqual(classify_exception(error), AIErrorType.MODEL)

    def test_patient_output_rejects_extra_keys(self):
        payload = json.dumps({
            'reply': 'Estou melhor.',
            'is_treatment': False,
            'treatment_assessment': 'NOT_APPLICABLE',
            'unexpected': 'no',
        })
        parsed, error = validate_output(payload, PatientAIResponse)
        self.assertIsNone(parsed)
        self.assertEqual(error.error_type, AIErrorType.SCHEMA)

    def test_patient_output_enforces_semantic_consistency(self):
        payload = json.dumps({
            'reply': 'Obrigado.',
            'is_treatment': True,
            'treatment_assessment': 'NOT_APPLICABLE',
        })
        parsed, error = validate_output(payload, PatientAIResponse)
        self.assertIsNone(parsed)
        self.assertEqual(error.error_type, AIErrorType.SCHEMA)

    def test_evaluation_score_must_equal_domain_sum(self):
        payload = json.dumps({
            'score': 100,
            'case_summary': 'Caso.',
            'care_summary': 'Atendimento.',
            'strengths': [],
            'reinforcement': [],
            'study_topics': [],
            'domains': {
                'comunicacao': 1,
                'anamnese': 1,
                'sinais_alarme': 1,
                'investigacao': 1,
                'raciocinio': 1,
                'conduta': 1,
                'seguimento': 1,
            },
        })
        parsed, error = validate_output(payload, EvaluationAIResponse)
        self.assertIsNone(parsed)
        self.assertEqual(error.error_type, AIErrorType.SCHEMA)

    @override_settings(
        AI_RATE_LIMIT_GLOBAL_PER_MINUTE=100,
        AI_RATE_LIMIT_USER_PER_MINUTE=2,
        AI_RATE_LIMIT_KIND_PER_MINUTE=100,
    )
    def test_rate_limit_blocks_user_burst(self):
        cache.clear()
        self.assertTrue(check_rate_limit(999, 'PATIENT').allowed)
        self.assertTrue(check_rate_limit(999, 'PATIENT').allowed)
        decision = check_rate_limit(999, 'PATIENT')
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, 'user')


class GeminiModelDefaultsTests(SimpleTestCase):
    """gemini-2.5-* models are valid for generateContent (confirmed via
    client.models.list() against the production key) but returned 404 Not Found
    when creating an interaction against the preview Interactions API. Only 3.x-tier
    models and *-latest aliases were confirmed to work there via direct production
    testing — keep defaults inside that confirmed-working set."""

    BROKEN_ON_INTERACTIONS = {'gemini-2.5-flash-lite', 'gemini-2.5-flash'}

    def test_default_models_avoid_models_broken_on_interactions_api(self):
        for value in (
            settings.GEMINI_CHAT_MODEL,
            settings.GEMINI_CHAT_FALLBACK_MODEL,
            settings.GEMINI_EVALUATION_MODEL,
            settings.GEMINI_EVALUATION_FALLBACK_MODEL,
        ):
            self.assertNotIn(value, self.BROKEN_ON_INTERACTIONS)

    def test_policy_fallback_tiers_are_distinct(self):
        # A compatibility_model identical to fallback_model silently collapses
        # the 3-tier chain to 2 tiers (this exact bug shipped once already).
        for kind in ('PATIENT', 'EVALUATION'):
            policy = policy_for(kind)
            tiers = [policy.primary_model, policy.fallback_model, policy.compatibility_model]
            self.assertEqual(len(tiers), len(set(tiers)), f'{kind}: fallback tiers collapse into duplicates')


class AIGatewayRequestShapeTests(SimpleTestCase):
    """GET /interactions/{id} polling returned 400 invalid_request against the
    production key/project on the preview Interactions API, while synchronous
    create() (background=False) completed normally. Background defaults to off,
    but 'store' must stay independent of it so previous_interaction_id chaining
    (patient conversation continuity) keeps working either way."""

    def _fake_client(self, captured):
        def fake_create(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                id='fake-interaction-id',
                status='completed',
                output_text='{"reply": "ok"}',
                usage=None,
            )

        return SimpleNamespace(interactions=SimpleNamespace(create=fake_create))

    @override_settings(AI_BACKGROUND_ENABLED=False)
    @patch('core.services.ai_gateway._client')
    def test_store_stays_enabled_when_background_is_disabled(self, mocked_client):
        captured = {}
        mocked_client.return_value = self._fake_client(captured)
        result = start_background_interaction(
            kind='PATIENT',
            system_instruction='sistema',
            input_text='entrada',
            schema_model=PatientAIResponse,
        )
        self.assertTrue(result.ok)
        self.assertFalse(captured['background'])
        self.assertTrue(captured['store'])

    @override_settings(AI_BACKGROUND_ENABLED=True)
    @patch('core.services.ai_gateway._client')
    def test_store_stays_enabled_when_background_is_enabled(self, mocked_client):
        captured = {}
        mocked_client.return_value = self._fake_client(captured)
        result = start_background_interaction(
            kind='PATIENT',
            system_instruction='sistema',
            input_text='entrada',
            schema_model=PatientAIResponse,
        )
        self.assertTrue(result.ok)
        self.assertTrue(captured['background'])
        self.assertTrue(captured['store'])

    def test_default_background_mode_is_synchronous(self):
        self.assertFalse(settings.AI_BACKGROUND_ENABLED)


class PatientPromptContractTests(SimpleTestCase):
    def test_requested_exams_must_return_immediate_simulated_results(self):
        case = SimpleNamespace(
            patient_name='Paciente Teste',
            age=40,
            sex='Feminino',
            complaint='Febre e tosse.',
            pathogen='Agente oculto',
            diagnosis='Diagnóstico oculto',
            master_context={
                'physical_exam_if_requested': 'Avaliar sinais vitais e ausculta pulmonar.',
                'tests_if_requested': 'Hemograma e radiografia conforme o quadro.',
            },
            expected_management='Conduta teste.',
            red_flags='Hipoxemia.',
            concept_anchor='Conceito teste.',
        )
        prompt = patient_system(case)
        self.assertIn('considere esse exame COMO JÁ REALIZADO', prompt)
        self.assertIn('informe imediatamente o resultado/achado', prompt)
        self.assertIn('resultado de TODOS eles', prompt)
        self.assertIn('Não interprete o resultado para o aluno', prompt)
        self.assertNotIn('informe de modo natural que ele não está disponível naquele momento', prompt)


class AIJobIdempotencyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='rn999', rgm='rn999', password='SenhaForte!2026', role=User.Role.STUDENT
        )
        cls.case = ClinicalCase.objects.create(
            code='RNT01',
            category=ClinicalCase.Category.BACTERIA,
            order=99,
            public_title='Caso de teste RN',
            patient_name='Paciente Teste',
            age=30,
            sex='Masculino',
            difficulty=ClinicalCase.Difficulty.BASIC,
            complaint='Febre.',
            pathogen='Agente teste',
            diagnosis='Diagnóstico teste',
            master_context={'historia': 'teste'},
            expected_management='Conduta teste',
        )

    @patch('core.services.ai_jobs.start_job')
    def test_same_request_id_is_idempotent(self, mocked_start):
        encounter = Encounter.objects.create(student=self.user, case=self.case)
        request_id = '2f1f4f30-50aa-4f0d-8a45-d38e132f4891'
        job1, created1 = queue_patient_job(
            encounter=encounter,
            student=self.user,
            content='Como começou?',
            request_id=request_id,
        )
        job2, created2 = queue_patient_job(
            encounter=encounter,
            student=self.user,
            content='Como começou?',
            request_id=request_id,
        )
        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(job1.pk, job2.pk)
        self.assertEqual(Message.objects.filter(encounter=encounter, role=Message.Role.STUDENT).count(), 1)
        self.assertEqual(AIJob.objects.filter(encounter=encounter).count(), 1)
        mocked_start.assert_called_once()
