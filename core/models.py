import uuid

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'STUDENT', 'Aluno'
        PROFESSOR = 'PROFESSOR', 'Professor'

    rgm = models.CharField('RGM', max_length=30, unique=True, null=True, blank=True)
    turma = models.CharField(max_length=80, blank=True)
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.STUDENT)

    def save(self, *args, **kwargs):
        if self.is_superuser:
            other_superusers = type(self).objects.filter(is_superuser=True)
            if self.pk:
                other_superusers = other_superusers.exclude(pk=self.pk)
            if other_superusers.exists():
                raise ValidationError('O MAPD Casos permite apenas um superusuário.')
            self.role = self.Role.PROFESSOR
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        return self.get_full_name() or self.username


class ClinicalCase(models.Model):
    class Category(models.TextChoices):
        BACTERIA = 'BACTERIA', 'Bactérias'
        FUNGI = 'FUNGI', 'Fungos'
        VIRUS = 'VIRUS', 'Vírus'
        PARASITE = 'PARASITE', 'Parasitas'

    class Difficulty(models.TextChoices):
        BASIC = 'BASIC', 'Básico'
        INTERMEDIATE = 'INTERMEDIATE', 'Intermediário'
        ADVANCED = 'ADVANCED', 'Avançado'

    code = models.CharField(max_length=12, unique=True)
    category = models.CharField(max_length=12, choices=Category.choices, db_index=True)
    order = models.PositiveSmallIntegerField(default=1)
    public_title = models.CharField(max_length=160)
    patient_name = models.CharField(max_length=100)
    age = models.PositiveSmallIntegerField()
    sex = models.CharField(max_length=30)
    difficulty = models.CharField(max_length=16, choices=Difficulty.choices, default=Difficulty.BASIC)
    complaint = models.TextField()
    pathogen = models.CharField(max_length=160)
    diagnosis = models.CharField(max_length=220)
    master_context = models.JSONField(default=dict)
    expected_management = models.TextField()
    red_flags = models.TextField(blank=True)
    concept_anchor = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['category', 'order', 'code']
        constraints = [models.UniqueConstraint(fields=['category', 'order'], name='unique_case_order_per_category')]

    def __str__(self):
        return f'{self.code} — {self.public_title}'


class Encounter(models.Model):
    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Em andamento'
        COMPLETED = 'COMPLETED', 'Concluído'

    class Outcome(models.TextChoices):
        NOT_ASSESSED = 'NOT_ASSESSED', 'Não avaliado'
        ADEQUATE = 'ADEQUATE', 'Conduta adequada'
        PARTIAL = 'PARTIAL', 'Conduta parcialmente adequada'
        INADEQUATE = 'INADEQUATE', 'Conduta inadequada'

    class Mode(models.TextChoices):
        AI = 'AI', 'Com auxílio de IA'
        TREE = 'TREE', 'Árvore decisória'

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='encounters')
    case = models.ForeignKey(ClinicalCase, on_delete=models.PROTECT, related_name='encounters')
    mode = models.CharField(max_length=8, choices=Mode.choices, default=Mode.AI, db_index=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    outcome = models.CharField(max_length=16, choices=Outcome.choices, default=Outcome.NOT_ASSESSED)
    score = models.PositiveSmallIntegerField(null=True, blank=True)
    final_feedback = models.JSONField(default=dict, blank=True)
    patient_interaction_id = models.CharField(max_length=512, blank=True)
    patient_interaction_model = models.CharField(max_length=80, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'case', 'mode'],
                name='unique_student_case_mode_encounter',
            )
        ]

    def __str__(self):
        return f'{self.student} / {self.case.code} / {self.mode}'


class DecisionAnswer(models.Model):
    class Quality(models.TextChoices):
        BEST = 'BEST', 'Melhor resposta'
        SUBOPTIMAL = 'SUBOPTIMAL', 'Correta, mas subótima'
        PLAUSIBLE = 'PLAUSIBLE', 'Plausível, mas incorreta'
        WRONG = 'WRONG', 'Totalmente incorreta'

    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name='decision_answers')
    node_id = models.CharField(max_length=64)
    prompt = models.TextField()
    selected_option_id = models.CharField(max_length=24)
    selected_text = models.TextField()
    quality = models.CharField(max_length=16, choices=Quality.choices)
    points = models.PositiveSmallIntegerField(default=0)
    feedback = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['encounter', 'node_id'],
                name='unique_decision_answer_per_node',
            )
        ]

    def __str__(self):
        return f'{self.encounter} / {self.node_id} / {self.quality}'


class Message(models.Model):
    class Role(models.TextChoices):
        STUDENT = 'STUDENT', 'Aluno'
        PATIENT = 'PATIENT', 'Paciente'
        PRECEPTOR = 'PRECEPTOR', 'Preceptor'
        TUTOR = 'TUTOR', 'Lembre o conceito'
        SYSTEM = 'SYSTEM', 'Sistema'

    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=12, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']

    def __str__(self):
        return f'{self.get_role_display()}: {self.content[:50]}'


class AIJob(models.Model):
    class Kind(models.TextChoices):
        PATIENT = 'PATIENT', 'Paciente virtual'
        PRECEPTOR = 'PRECEPTOR', 'Preceptor'
        CONCEPT = 'CONCEPT', 'Lembre o conceito'
        EVALUATION = 'EVALUATION', 'Avaliação final'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pendente'
        RUNNING = 'RUNNING', 'Processando'
        COMPLETED = 'COMPLETED', 'Concluído'
        FAILED = 'FAILED', 'Falhou'
        CANCELLED = 'CANCELLED', 'Cancelado'

    request_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name='ai_jobs')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_jobs')
    source_message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_jobs',
    )
    kind = models.CharField(max_length=16, choices=Kind.choices, db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    input_hash = models.CharField(max_length=64, db_index=True)
    prompt_version = models.CharField(max_length=64, blank=True)
    provider_interaction_id = models.CharField(max_length=512, blank=True, db_index=True)
    model_used = models.CharField(max_length=80, blank=True)
    fallback_used = models.BooleanField(default=False)
    repair_attempts = models.PositiveSmallIntegerField(default=0)
    result = models.JSONField(default=dict, blank=True)
    error_type = models.CharField(max_length=64, blank=True)
    error_code = models.CharField(max_length=32, blank=True)
    error_message = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'status', 'created_at'], name='aijob_user_status_idx'),
            models.Index(fields=['encounter', 'kind', 'status'], name='aijob_enc_kind_idx'),
        ]

    def __str__(self):
        return f'{self.kind} / {self.status} / {self.request_id}'
