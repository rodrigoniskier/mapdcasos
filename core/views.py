import logging
from collections import defaultdict

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import IntegrityError, OperationalError, connection
from django.db.models import Avg, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import StudentSignUpForm
from .models import ClinicalCase, Encounter, Message, User
from .services.gemini import concept_hint, evaluate_encounter, patient_reply, preceptor_hint

logger = logging.getLogger(__name__)


def _db_is_busy(exc: Exception) -> bool:
    text = str(exc).lower()
    return 'database is locked' in text or 'database is busy' in text


def signup(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = StudentSignUpForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            form.save()
        except IntegrityError:
            form.add_error('rgm', 'Este RGM já foi cadastrado. Tente entrar com a senha criada anteriormente.')
        except OperationalError as exc:
            if not _db_is_busy(exc):
                raise
            logger.warning('SQLite ocupado durante cadastro.', exc_info=True)
            form.add_error(None, 'Muitos alunos estão acessando ao mesmo tempo. Tente concluir o cadastro novamente em alguns segundos.')
        else:
            # Do not auto-login here. Keeping registration and authentication as
            # separate requests avoids a partially-successful first access under load.
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
        encounter, created = Encounter.objects.get_or_create(student=request.user, case=case)
    except IntegrityError:
        # A second near-simultaneous request may lose the get_or_create race.
        encounter = Encounter.objects.get(student=request.user, case=case)
        created = False
    if created:
        Message.objects.create(encounter=encounter, role=Message.Role.PATIENT, content=case.complaint)
    return case, encounter


@login_required
def case_chat(request, case_id):
    if request.user.is_superuser:
        return redirect('professor_dashboard')
    case, encounter = _student_case(request, case_id)
    if encounter.status == Encounter.Status.COMPLETED:
        return redirect('case_summary', case_id=case.id)
    return render(request, 'case_chat.html', {'case': case, 'encounter': encounter})


@login_required
@require_POST
def send_message(request, case_id):
    if request.user.is_superuser:
        return JsonResponse({'error': 'Ação indisponível.'}, status=403)

    try:
        case, encounter = _student_case(request, case_id)
        if encounter.status == Encounter.Status.COMPLETED:
            return JsonResponse({'error': 'Este atendimento já foi concluído.'}, status=400)
        content = (request.POST.get('message') or '').strip()
        if not content:
            return JsonResponse({'error': 'Digite uma mensagem.'}, status=400)
        student_entry = Message.objects.create(encounter=encounter, role=Message.Role.STUDENT, content=content)
    except OperationalError as exc:
        if not _db_is_busy(exc):
            raise
        logger.warning('SQLite ocupado antes da chamada Gemini.', exc_info=True)
        return JsonResponse(
            {'error': 'A plataforma está processando muitos atendimentos simultâneos. Tente enviar novamente em alguns segundos.', 'retryable': True},
            status=503,
        )

    result = patient_reply(encounter, content)
    if result.get('_service_unavailable'):
        # Do not poison the transcript with an API-error message. The front-end
        # restores the student's text so it can be sent again.
        try:
            student_entry.delete()
        except OperationalError:
            logger.warning('Não foi possível remover mensagem pendente após falha Gemini.', exc_info=True)
        return JsonResponse(
            {'error': 'O paciente virtual está atendendo muitos alunos neste momento. Tente enviar novamente em alguns segundos.', 'retryable': True},
            status=503,
        )

    reply = (result.get('reply') or '').strip()
    assessment = result.get('treatment_assessment')
    try:
        Message.objects.create(encounter=encounter, role=Message.Role.PATIENT, content=reply)
        if result.get('is_treatment') and assessment in {'ADEQUATE', 'PARTIAL', 'INADEQUATE'}:
            encounter.outcome = assessment
            encounter.save(update_fields=['outcome', 'updated_at'])
    except OperationalError as exc:
        if not _db_is_busy(exc):
            raise
        logger.warning('SQLite ocupado ao persistir resposta Gemini.', exc_info=True)
        return JsonResponse(
            {'error': 'A resposta foi gerada, mas o servidor está muito ocupado para registrá-la. Tente novamente em alguns segundos.', 'retryable': True},
            status=503,
        )

    return JsonResponse({'reply': reply, 'assessment': assessment})


@login_required
@require_POST
def ask_preceptor(request, case_id):
    if request.user.is_superuser:
        return JsonResponse({'error': 'Ação indisponível.'}, status=403)
    _, encounter = _student_case(request, case_id)
    if encounter.status == Encounter.Status.COMPLETED:
        return JsonResponse({'error': 'Este atendimento já foi concluído.'}, status=400)
    hint = preceptor_hint(encounter)
    Message.objects.create(encounter=encounter, role=Message.Role.PRECEPTOR, content=hint)
    return JsonResponse({'reply': hint})


@login_required
@require_POST
def remember_concept(request, case_id):
    if request.user.is_superuser:
        return JsonResponse({'error': 'Ação indisponível.'}, status=403)
    _, encounter = _student_case(request, case_id)
    if encounter.status == Encounter.Status.COMPLETED:
        return JsonResponse({'error': 'Este atendimento já foi concluído.'}, status=400)
    hint = concept_hint(encounter)
    Message.objects.create(encounter=encounter, role=Message.Role.TUTOR, content=hint)
    return JsonResponse({'reply': hint})


@login_required
@require_POST
def conclude_case(request, case_id):
    if request.user.is_superuser:
        return redirect('professor_dashboard')
    _, encounter = _student_case(request, case_id)
    if encounter.status != Encounter.Status.COMPLETED:
        feedback = evaluate_encounter(encounter)
        if feedback.pop('_service_unavailable', False):
            messages.error(request, 'A avaliação está temporariamente congestionada. Seu atendimento foi preservado; tente concluir novamente em alguns segundos.')
            return redirect('case_chat', case_id=case_id)
        feedback.pop('_model_used', None)
        encounter.final_feedback = feedback
        encounter.score = max(0, min(100, int(feedback.get('score', 0))))
        encounter.status = Encounter.Status.COMPLETED
        encounter.completed_at = timezone.now()
        encounter.save()
        Message.objects.create(encounter=encounter, role=Message.Role.SYSTEM, content='Atendimento encerrado e avaliado pelo preceptor.')
    return redirect('case_summary', case_id=case_id)


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
    return render(request, 'professor_dashboard.html', {'students': students, 'student_count': students.count(), 'completed_count': completed.count(), 'overall_average': completed.aggregate(v=Avg('score'))['v'], 'turma_rows': turma_rows, 'category_stats': category_stats, 'latest': latest})


@login_required
@user_passes_test(_is_professor)
def professor_student(request, user_id):
    student = get_object_or_404(User, id=user_id, is_superuser=False)
    encounters = Encounter.objects.filter(student=student).select_related('case').order_by('-updated_at')
    return render(request, 'professor_student.html', {'student': student, 'encounters': encounters})


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
        },
        status=status,
    )
