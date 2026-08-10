from django.contrib.auth.models import AbstractUser
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

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='encounters')
    case = models.ForeignKey(ClinicalCase, on_delete=models.PROTECT, related_name='encounters')
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    outcome = models.CharField(max_length=16, choices=Outcome.choices, default=Outcome.NOT_ASSESSED)
    score = models.PositiveSmallIntegerField(null=True, blank=True)
    final_feedback = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        constraints = [models.UniqueConstraint(fields=['student', 'case'], name='unique_student_case_encounter')]

    def __str__(self):
        return f'{self.student} / {self.case.code}'


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
