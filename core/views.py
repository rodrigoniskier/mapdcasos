import logging
from collections import defaultdict

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import IntegrityError, OperationalError, connection, transaction
from django.db.models import Avg, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from .forms import StudentSignUpForm
from .models import AIJob, ClinicalCase, Encounter, Message, User
from .services.ai_gateway import circuit_state
from .services.ai_jobs import (
    QueueError,
    job_public_payload,
    queue_patient_job,
    queue_snapshot,
    queue_tool_job,
    refresh_job,
)

logger = logging.getLogger(__name__)


def _db_is_busy(exc: Exception) -> bool:
    text = str(exc).lower()
    return 'database is locked' in text or 'database is busy' in text


def _json_queue_error(exc: QueueError):
    response = JsonResponse(
        {
            'error': exc.message,
            'retryable': exc.retryable,
            'retry_after': exc.retry_after,
        },
        status=exc.status_code,
    )
    if exc.retry_after:
        response['Retry-After'] = str(exc.retry_after)
    return response


def signup(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = StudentSignUpForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                form.save()
        except IntegrityError:
            form.add_error('rgm', 'Este RGM já foi cadastrado. Tente entrar com a senha criada anteriormente.')
        except OperationalError as exc:
            if not _db_is_busy(exc):
                raise
            logger.warning('Banco ocupado durante cadastro.', exc_info=True)
            form.add_error(None, 'Muitos alunos estão acessando ao mesmo tempo. Tente concluir o cadastro novamente em alguns segundos.')
        else:
            messages.success(request, 'Cadastro concluído. Agora entre com seu RGM e a senha que você criou.')
            return redirect('login')
    return render(request, 'registration/signup.html', {'form': form})


@login_required
def home(request):
    if request.user.is_superuser:
        return redirect('professor_dashboard')
    return redirect('dashboard')


@login_required
def dashboard(request):
    if request.user.is_superuser:
        return redirect('professor_dashboard')

    totals = {
        row['category']: row['total']
        for row in ClinicalCase.objects.filter(active=True)
        .values('category')
        .annotate(total=Count('id'))
    }
    completed = {
        row['case__category']: row['total']
        for row in Encounter.objects.filter(student=request.user, status=Encounter.Status.COMPLETED)
        .values('case__category')
        .annotate(total=Count('id'))
    }
    cards = [
        {
            'value': value,
            'label': label,
            'total': totals.get(value, 0),
            'completed': completed.get(value, 0),
        }
        for value, label in ClinicalCase.Category.choices
    ]
    return render(request, 'dashboard.html', {'cards': cards})


@login_required
def category_cases(request, category):
    if request.user.is_superuser:
        return redirect('professor_dashboard')
    valid = dict(ClinicalCase.Category.choices)
    if category not in valid:
        return redirect('dashboard')
    cases = list(ClinicalCase.objects.filter(category=category, active=True))
    encounters = {e.case_id: e for e in Encounter.objects.filter(student=request.user, case__category=category)}
    rows = [{'case': case, 'encounter': encounters.get(case.id)} for case in cases]
    return render(request, 'category_cases.html', {'rows': rows, 'category_label': valid[category]})


def _student_case(request, case_id):
    case = get_object_or_404(ClinicalCase, id=case_id, active=True)
    try:
        with transaction.atomic():
            encounter, created = Encounter.objects.get_or_create(student=request.user, case=case)
            if created:
                Message.objects.create(encounter=encounter, role=Message.Role.PATIENT, content=case.complaint)
    except IntegrityError:
        encounter = Encounter.objects.get(student=request.user, case=case)
    return case, encounter


@login_required
def case_chat(request, case_id):
    if request.user.is_superuser:
        return redirect('professor_dashboard')
    case, encounter = _student_case(request, case_id)
    if encounter.status == Encounter.Status.COMPLETED:
        return redirect('case_summary', case_id=case.id)
    pending_job = encounter.ai_jobs.filter(status__in=[AIJob.Status.PENDING, AIJob.Status.RUNNING]).order_by('-created_at').first()
    return render(request, 'case_chat.html', {'case': case, 'encounter': encounter, 'pending_job': pending_job})


def _queued_response(job: AIJob):
    payload = job_public_payload(job)
    payload['status_url'] = reverse('ai_job_status', args=[job.request_id])
    status = 200 if payload['status'] in {'completed', 'failed'} else 202
    return JsonResponse(payload, status=status)


@login_required
@require_POST
def send_message(request, case_id):
    if request.user.is_superuser:
        return JsonResponse({'error': 'Ação indisponível.'}, status=403)
    try:
        _, encounter = _student_case(request, case_id)
        if encounter.status == Encounter.Status.COMPLETED:
            return JsonResponse({'error': 'Este atendimento já foi concluído.'}, status=400)
        job, _ = queue_patient_job(
            encounter=encounter,
            student=request.user,
            content=request.POST.get('message') or '',
            request_id=request.POST.get('request_id'),
        )
        return _queued_response(job)
    except QueueError as exc:
        return _json_queue_error(exc)
    except OperationalError as exc:
        if not _db_is_busy(exc):
            raise
        logger.warning('Banco ocupado ao enfileirar paciente virtual.', exc_info=True)
        return JsonResponse(
            {'error': 'A plataforma está processando muitos atendimentos simultâneos. Tente novamente em alguns segundos.', 'retryable': True, 'retry_after': 3},
            status=503,
        )


@login_required
@require_POST
def ask_preceptor(request, case_id):
    if request.user.is_superuser:
        return JsonResponse({'error': 'Ação indisponível.'}, status=403)
    try:
        _, encounter = _student_case(request, case_id)
        if encounter.status == Encounter.Status.COMPLETED:
            return JsonResponse({'error': 'Este atendimento já foi concluído.'}, status=400)
        job, _ = queue_tool_job(
            encounter=encounter,
            student=request.user,
            kind=AIJob.Kind.PRECEPTOR,
            request_id=request.POST.get('request_id'),
        )
        return _queued_response(job)
    except QueueError as exc:
        return _json_queue_error(exc)


@login_required
@require_POST
def remember_concept(request, case_id):
    if request.user.is_superuser:
        return JsonResponse({'error': 'Ação indisponível.'}, status=403)
    try:
        _, encounter = _student_case(request, case_id)
        if encounter.status == Encounter.Status.COMPLETED:
            return JsonResponse({'error': 'Este atendimento já foi concluído.'}, status=400)
        job, _ = queue_tool_job(
            encounter=encounter,
            student=request.user,
            kind=AIJob.Kind.CONCEPT,
            request_id=request.POST.get('request_id'),
        )
        return _queued_response(job)
    except QueueError as exc:
        return _json_queue_error(exc)


@login_required
@require_POST
def conclude_case(request, case_id):
    if request.user.is_superuser:
        return JsonResponse({'error': 'Ação indisponível.'}, status=403)
    try:
        _, encounter = _student_case(request, case_id)
        if encounter.status == Encounter.Status.COMPLETED:
            return JsonResponse({'status': 'completed', 'redirect_url': reverse('case_summary', args=[case_id])})
        job, _ = queue_tool_job(
            encounter=encounter,
            student=request.user,
            kind=AIJob.Kind.EVALUATION,
            request_id=request.POST.get('request_id'),
        )
        return _queued_response(job)
    except QueueError as exc:
        return _json_queue_error(exc)


@login_required
@require_GET
def ai_job_status(request, request_id):
    if request.user.is_superuser:
        return JsonResponse({'error': 'Ação indisponível.'}, status=403)
    job = get_object_or_404(
        AIJob.objects.select_related('encounter__case'),
        request_id=request_id,
        student=request.user,
    )
    try:
        job = refresh_job(job)
    except OperationalError as exc:
        if not _db_is_busy(exc):
            raise
        logger.warning('Banco ocupado ao consultar job de IA.', exc_info=True)
        return JsonResponse(
            {'status': 'processing', 'job_id': str(job.request_id), 'retry_after': 2},
            status=202,
        )
    payload = job_public_payload(job)
    payload['status_url'] = reverse('ai_job_status', args=[job.request_id])
    return JsonResponse(payload, status=202 if payload['status'] == 'processing' else 200)


@login_required
def case_summary(request, case_id):
    case = get_object_or_404(ClinicalCase, id=case_id)
    encounter = get_object_or_404(Encounter, student=request.user, case=case)
    if encounter.status != Encounter.Status.COMPLETED:
        return redirect('case_chat', case_id=case_id)
    return render(request, 'case_summary.html', {'case': case, 'encounter': encounter, 'feedback': encounter.final_feedback})


def _is_professor(user):
    return user.is_authenticated and user.is_superuser


@login_required
@user_passes_test(_is_professor)
def professor_dashboard(request):
    students = User.objects.filter(is_superuser=False, role=User.Role.STUDENT).order_by('turma', 'first_name', 'last_name')
    completed = Encounter.objects.filter(status=Encounter.Status.COMPLETED)
    turma_stats = defaultdict(lambda: {'students': 0, 'completed': 0, 'scores': []})
    for student in students:
        turma_stats[student.turma or 'Sem turma']['students'] += 1
    for encounter in completed.select_related('student'):
        key = encounter.student.turma or 'Sem turma'
        turma_stats[key]['completed'] += 1
        if encounter.score is not None:
            turma_stats[key]['scores'].append(encounter.score)
    turma_rows = []
    for turma, data in sorted(turma_stats.items()):
        scores = data.pop('scores')
        data['turma'] = turma
        data['average'] = round(sum(scores) / len(scores), 1) if scores else None
        turma_rows.append(data)
    category_stats = list(completed.values('case__category').annotate(total=Count('id'), average=Avg('score')).order_by('case__category'))
    category_labels = dict(ClinicalCase.Category.choices)
    for row in category_stats:
        row['label'] = category_labels.get(row['case__category'], row['case__category'])
        row['average'] = round(row['average'], 1) if row['average'] is not None else None
    latest = Encounter.objects.select_related('student', 'case').order_by('-updated_at')[:20]
    return render(
        request,
        'professor_dashboard.html',
        {
            'students': students,
            'student_count': students.count(),
            'completed_count': completed.count(),
            'overall_average': completed.aggregate(v=Avg('score'))['v'],
            'turma_rows': turma_rows,
            'category_stats': category_stats,
            'latest': latest,
            'ai_queue': queue_snapshot(),
        },
    )


@login_required
@user_passes_test(_is_professor)
def professor_student(request, user_id):
    student = get_object_or_404(User, id=user_id, is_superuser=False)
    encounters = Encounter.objects.filter(student=student).select_related('case').order_by('-updated_at')
    return render(request, 'professor_student.html', {'student': student, 'encounters': encounters})


@require_GET
def app_health(request):
    return JsonResponse({'status': 'ok', 'environment': settings.APP_ENV})


@require_GET
def database_health(request):
    try:
        User.objects.only('pk').first()
        return JsonResponse({'status': 'ok', 'backend': connection.vendor})
    except Exception:
        logger.exception('Health check: banco indisponível.')
        return JsonResponse({'status': 'error', 'backend': connection.vendor}, status=503)


@login_required
@user_passes_test(_is_professor)
@require_GET
def ai_health(request):
    return JsonResponse(
        {
            'status': 'ok' if settings.AI_ENABLED and bool(settings.GEMINI_API_KEY) else 'degraded',
            'enabled': settings.AI_ENABLED,
            'patient_enabled': settings.PATIENT_AI_ENABLED,
            'evaluation_enabled': settings.EVALUATION_AI_ENABLED,
            'background_enabled': settings.AI_BACKGROUND_ENABLED,
            'chat': circuit_state(settings.GEMINI_CHAT_MODEL),
            'chat_fallback': circuit_state(settings.GEMINI_CHAT_FALLBACK_MODEL),
            'evaluation': circuit_state(settings.GEMINI_EVALUATION_MODEL),
            'evaluation_fallback': circuit_state(settings.GEMINI_EVALUATION_FALLBACK_MODEL),
        }
    )


@login_required
@user_passes_test(_is_professor)
@require_GET
def queue_health(request):
    snapshot = queue_snapshot()
    status = 200 if snapshot['active'] < snapshot['max_active'] else 503
    return JsonResponse({'status': 'ok' if status == 200 else 'saturated', **snapshot}, status=status)


@require_GET
def healthz(request):
    try:
        User.objects.only('pk').first()
        database_status = 'ok'
        status = 200
    except Exception:
        logger.exception('Health check: banco indisponível.')
        database_status = 'error'
        status = 503
    return JsonResponse(
        {
            'status': 'ok' if status == 200 else 'degraded',
            'database': database_status,
            'database_backend': connection.vendor,
            'ai_configured': bool(settings.GEMINI_API_KEY),
            'ai_enabled': settings.AI_ENABLED,
        },
        status=status,
    )
