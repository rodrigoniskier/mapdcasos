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
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .decision_trees import find_option, get_tree
from .forms import StudentSignUpForm
from .models import AIJob, ClinicalCase, DecisionAnswer, Encounter, Message, User
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
    return redirect('study_mode')


@login_required
def study_mode(request):
    if request.user.is_superuser:
        return redirect('professor_dashboard')
    if request.method == 'POST':
        mode = request.POST.get('mode')
        if mode not in {Encounter.Mode.AI, Encounter.Mode.TREE}:
            messages.error(request, 'Escolha uma modalidade válida.')
        else:
            request.session['study_mode'] = mode
            return redirect('dashboard')
    return render(request, 'study_mode.html', {'current_mode': request.session.get('study_mode')})


def _study_mode(request):
    mode = request.session.get('study_mode')
    if mode in {Encounter.Mode.AI, Encounter.Mode.TREE}:
        return mode
    return None


@login_required
def dashboard(request):
    if request.user.is_superuser:
        return redirect('professor_dashboard')
    mode = _study_mode(request)
    if not mode:
        return redirect('study_mode')

    totals = {
        row['category']: row['total']
        for row in ClinicalCase.objects.filter(active=True)
        .values('category')
        .annotate(total=Count('id'))
    }
    completed = {
        row['case__category']: row['total']
        for row in Encounter.objects.filter(
            student=request.user,
            mode=mode,
            status=Encounter.Status.COMPLETED,
        )
        .values('case__category')
        .annotate(total=Count('id'))
    }
    cards = []
    for value, label in ClinicalCase.Category.choices:
        available = mode == Encounter.Mode.AI or value == ClinicalCase.Category.BACTERIA
        cards.append(
            {
                'value': value,
                'label': label,
                'total': totals.get(value, 0),
                'completed': completed.get(value, 0),
                'available': available,
            }
        )
    return render(
        request,
        'dashboard.html',
        {
            'cards': cards,
            'mode': mode,
            'mode_label': dict(Encounter.Mode.choices)[mode],
        },
    )


@login_required
def category_cases(request, category):
    if request.user.is_superuser:
        return redirect('professor_dashboard')
    mode = _study_mode(request)
    if not mode:
        return redirect('study_mode')

    valid = dict(ClinicalCase.Category.choices)
    if category not in valid:
        return redirect('dashboard')
    if mode == Encounter.Mode.TREE and category != ClinicalCase.Category.BACTERIA:
        messages.info(request, 'Hoje a árvore decisória está disponível apenas para os casos de bactérias.')
        return redirect('dashboard')

    cases = list(ClinicalCase.objects.filter(category=category, active=True))
    encounters = {
        e.case_id: e
        for e in Encounter.objects.filter(student=request.user, case__category=category, mode=mode)
    }
    rows = [{'case': case, 'encounter': encounters.get(case.id)} for case in cases]
    return render(
        request,
        'category_cases.html',
        {
            'rows': rows,
            'category_label': valid[category],
            'mode': mode,
            'mode_label': dict(Encounter.Mode.choices)[mode],
        },
    )


def _student_case(request, case_id, mode=Encounter.Mode.AI):
    case = get_object_or_404(ClinicalCase, id=case_id, active=True)
    try:
        with transaction.atomic():
            encounter, created = Encounter.objects.get_or_create(
                student=request.user,
                case=case,
                mode=mode,
            )
            if created and mode == Encounter.Mode.AI:
                Message.objects.create(
                    encounter=encounter,
                    role=Message.Role.PATIENT,
                    content=case.complaint,
                )
    except IntegrityError:
        encounter = Encounter.objects.get(student=request.user, case=case, mode=mode)
    return case, encounter


@login_required
def case_chat(request, case_id):
    if request.user.is_superuser:
        return redirect('professor_dashboard')
    case, encounter = _student_case(request, case_id, Encounter.Mode.AI)
    if encounter.status == Encounter.Status.COMPLETED:
        return redirect('case_summary', case_id=case.id)
    pending_job = encounter.ai_jobs.filter(
        status__in=[AIJob.Status.PENDING, AIJob.Status.RUNNING]
    ).order_by('-created_at').first()
    return render(
        request,
        'case_chat.html',
        {'case': case, 'encounter': encounter, 'pending_job': pending_job},
    )


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
        _, encounter = _student_case(request, case_id, Encounter.Mode.AI)
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
            {
                'error': 'A plataforma está processando muitos atendimentos simultâneos. Tente novamente em alguns segundos.',
                'retryable': True,
                'retry_after': 3,
            },
            status=503,
        )


@login_required
@require_POST
def ask_preceptor(request, case_id):
    if request.user.is_superuser:
        return JsonResponse({'error': 'Ação indisponível.'}, status=403)
    try:
        _, encounter = _student_case(request, case_id, Encounter.Mode.AI)
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
        _, encounter = _student_case(request, case_id, Encounter.Mode.AI)
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
        _, encounter = _student_case(request, case_id, Encounter.Mode.AI)
        if encounter.status == Encounter.Status.COMPLETED:
            return JsonResponse(
                {'status': 'completed', 'redirect_url': reverse('case_summary', args=[case_id])}
            )
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


def _complete_tree_encounter(encounter, tree):
    answers = list(encounter.decision_answers.all())
    points = sum(answer.points for answer in answers)
    max_points = tree['max_points']
    score = round((points / max_points) * 100) if max_points else 0
    if score >= 80:
        outcome = Encounter.Outcome.ADEQUATE
    elif score >= 60:
        outcome = Encounter.Outcome.PARTIAL
    else:
        outcome = Encounter.Outcome.INADEQUATE
    quality_counts = {
        value: sum(1 for answer in answers if answer.quality == value)
        for value, _ in DecisionAnswer.Quality.choices
    }
    encounter.status = Encounter.Status.COMPLETED
    encounter.outcome = outcome
    encounter.score = score
    encounter.completed_at = timezone.now()
    encounter.final_feedback = {
        'mode': Encounter.Mode.TREE,
        'points': points,
        'max_points': max_points,
        'quality_counts': quality_counts,
        'focus': tree['focus'],
        'summary': (
            'Excelente consistência nas decisões clínicas.'
            if score >= 80
            else 'Bom caminho, mas há decisões que merecem revisão.'
            if score >= 60
            else 'Revise os pontos de decisão e os comentários antes de repetir o caso.'
        ),
    }
    encounter.save(
        update_fields=['status', 'outcome', 'score', 'completed_at', 'final_feedback', 'updated_at']
    )


@login_required
def decision_tree_case(request, case_id):
    if request.user.is_superuser:
        return redirect('professor_dashboard')
    if _study_mode(request) != Encounter.Mode.TREE:
        messages.info(request, 'Selecione primeiro a modalidade Árvore decisória.')
        return redirect('study_mode')

    case = get_object_or_404(ClinicalCase, id=case_id, active=True)
    if case.category != ClinicalCase.Category.BACTERIA:
        messages.info(request, 'A árvore decisória está disponível apenas para bactérias nesta etapa.')
        return redirect('dashboard')
    _, encounter = _student_case(request, case_id, Encounter.Mode.TREE)

    tree = get_tree(case)
    if encounter.status == Encounter.Status.COMPLETED:
        return redirect('tree_summary', case_id=case.id)

    existing = {answer.node_id: answer for answer in encounter.decision_answers.all()}
    current_node = next((node for node in tree['nodes'] if node['id'] not in existing), None)

    if request.method == 'POST':
        node_id = request.POST.get('node_id') or ''
        option_id = request.POST.get('option_id') or ''
        if not current_node or node_id != current_node['id']:
            messages.error(request, 'Esse ponto de decisão já foi respondido ou está fora de sequência.')
            return redirect('decision_tree_case', case_id=case.id)
        node, option = find_option(tree, node_id, option_id)
        if not node or not option:
            messages.error(request, 'Escolha uma alternativa válida.')
            return redirect('decision_tree_case', case_id=case.id)
        try:
            with transaction.atomic():
                DecisionAnswer.objects.create(
                    encounter=encounter,
                    node_id=node['id'],
                    prompt=node['prompt'],
                    selected_option_id=option['id'],
                    selected_text=option['text'],
                    quality=option['quality'],
                    points=option['points'],
                    feedback=option['feedback'],
                )
                answered_count = encounter.decision_answers.count()
                if answered_count == len(tree['nodes']):
                    _complete_tree_encounter(encounter, tree)
        except IntegrityError:
            messages.info(request, 'Essa decisão já foi registrada.')
        if encounter.status == Encounter.Status.COMPLETED:
            return redirect('tree_summary', case_id=case.id)
        return redirect('decision_tree_case', case_id=case.id)

    answered_rows = []
    for node in tree['nodes']:
        answer = existing.get(node['id'])
        if not answer:
            continue
        answered_rows.append(
            {
                'node': node,
                'answer': answer,
                'quality_label': dict(DecisionAnswer.Quality.choices).get(answer.quality, answer.quality),
            }
        )
    progress = len(existing)
    return render(
        request,
        'decision_tree.html',
        {
            'case': case,
            'encounter': encounter,
            'tree': tree,
            'current_node': current_node,
            'answered_rows': answered_rows,
            'progress': progress,
            'total_nodes': len(tree['nodes']),
            'progress_pct': round((progress / len(tree['nodes'])) * 100) if tree['nodes'] else 0,
        },
    )


@login_required
def case_summary(request, case_id):
    case = get_object_or_404(ClinicalCase, id=case_id)
    encounter = get_object_or_404(
        Encounter,
        student=request.user,
        case=case,
        mode=Encounter.Mode.AI,
    )
    if encounter.status != Encounter.Status.COMPLETED:
        return redirect('case_chat', case_id=case_id)
    return render(
        request,
        'case_summary.html',
        {'case': case, 'encounter': encounter, 'feedback': encounter.final_feedback},
    )


@login_required
def tree_summary(request, case_id):
    case = get_object_or_404(ClinicalCase, id=case_id, category=ClinicalCase.Category.BACTERIA)
    encounter = get_object_or_404(
        Encounter,
        student=request.user,
        case=case,
        mode=Encounter.Mode.TREE,
    )
    if encounter.status != Encounter.Status.COMPLETED:
        return redirect('decision_tree_case', case_id=case_id)
    tree = get_tree(case)
    answers = list(encounter.decision_answers.all())
    return render(
        request,
        'tree_summary.html',
        {
            'case': case,
            'encounter': encounter,
            'tree': tree,
            'answers': answers,
            'feedback': encounter.final_feedback,
        },
    )


def _is_professor(user):
    return user.is_authenticated and user.is_superuser


@login_required
@user_passes_test(_is_professor)
def professor_dashboard(request):
    students = User.objects.filter(
        is_superuser=False,
        role=User.Role.STUDENT,
    ).order_by('turma', 'first_name', 'last_name')
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

    category_stats = list(
        completed.values('case__category')
        .annotate(total=Count('id'), average=Avg('score'))
        .order_by('case__category')
    )
    category_labels = dict(ClinicalCase.Category.choices)
    for row in category_stats:
        row['label'] = category_labels.get(row['case__category'], row['case__category'])
        row['average'] = round(row['average'], 1) if row['average'] is not None else None

    mode_stats = list(
        completed.values('mode').annotate(total=Count('id'), average=Avg('score')).order_by('mode')
    )
    mode_labels = dict(Encounter.Mode.choices)
    for row in mode_stats:
        row['label'] = mode_labels.get(row['mode'], row['mode'])
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
            'mode_stats': mode_stats,
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
