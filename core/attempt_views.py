from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import OperationalError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .decision_trees import get_tree
from .models import AIJob, ClinicalCase, DecisionAnswer, Encounter, Message


def _db_is_busy(exc: Exception) -> bool:
    text = str(exc).lower()
    return 'database is locked' in text or 'database is busy' in text


def _student_encounter(request, case_id, mode):
    case = get_object_or_404(ClinicalCase, id=case_id, active=True)
    encounter = get_object_or_404(
        Encounter,
        student=request.user,
        case=case,
        mode=mode,
    )
    return case, encounter


def _reset_encounter(encounter, *, mode):
    """Reset one student's current attempt without creating a second encounter.

    Encounter is unique per student/case/mode. Clearing dependent rows keeps the
    schema compact for SQLite and avoids accumulating classroom attempts while
    still giving the student a genuinely fresh start.
    """
    # Delete jobs before messages because AIJob.source_message uses SET_NULL.
    encounter.ai_jobs.all().delete()
    encounter.messages.all().delete()
    encounter.decision_answers.all().delete()

    encounter.status = Encounter.Status.OPEN
    encounter.outcome = Encounter.Outcome.NOT_ASSESSED
    encounter.score = None
    encounter.final_feedback = {}
    encounter.completed_at = None
    encounter.patient_interaction_id = ''
    encounter.patient_interaction_model = ''
    encounter.save(
        update_fields=[
            'status',
            'outcome',
            'score',
            'final_feedback',
            'completed_at',
            'patient_interaction_id',
            'patient_interaction_model',
            'updated_at',
        ]
    )

    if mode == Encounter.Mode.AI:
        Message.objects.create(
            encounter=encounter,
            role=Message.Role.PATIENT,
            content=encounter.case.complaint,
        )


@login_required
@require_POST
def restart_ai_case(request, case_id):
    if request.user.is_superuser:
        return redirect('professor_dashboard')
    case, encounter = _student_encounter(request, case_id, Encounter.Mode.AI)
    try:
        with transaction.atomic():
            _reset_encounter(encounter, mode=Encounter.Mode.AI)
    except OperationalError as exc:
        if not _db_is_busy(exc):
            raise
        messages.error(request, 'O banco está ocupado neste momento. Tente reiniciar o caso novamente em alguns segundos.')
        return redirect('case_summary', case_id=case.id)

    request.session['study_mode'] = Encounter.Mode.AI
    messages.success(request, 'Caso reiniciado. A conversa anterior foi apagada e uma nova tentativa foi aberta.')
    return redirect('case_chat', case_id=case.id)


@login_required
@require_POST
def restart_tree_case(request, case_id):
    if request.user.is_superuser:
        return redirect('professor_dashboard')
    case, encounter = _student_encounter(request, case_id, Encounter.Mode.TREE)
    try:
        with transaction.atomic():
            _reset_encounter(encounter, mode=Encounter.Mode.TREE)
    except OperationalError as exc:
        if not _db_is_busy(exc):
            raise
        messages.error(request, 'O banco está ocupado neste momento. Tente reiniciar o caso novamente em alguns segundos.')
        return redirect('tree_summary', case_id=case.id)

    request.session['study_mode'] = Encounter.Mode.TREE
    messages.success(request, 'Caso reiniciado. As decisões anteriores foram apagadas e uma nova tentativa foi aberta.')
    return redirect('decision_tree_case', case_id=case.id)


@login_required
def ai_transcript(request, case_id):
    if request.user.is_superuser:
        return redirect('professor_dashboard')
    case, encounter = _student_encounter(request, case_id, Encounter.Mode.AI)
    if encounter.status != Encounter.Status.COMPLETED:
        return redirect('case_chat', case_id=case.id)

    conversation = encounter.messages.exclude(role=Message.Role.SYSTEM)
    return render(
        request,
        'case_transcript.html',
        {
            'case': case,
            'encounter': encounter,
            'conversation': conversation,
        },
    )


@login_required
def tree_transcript(request, case_id):
    if request.user.is_superuser:
        return redirect('professor_dashboard')
    case, encounter = _student_encounter(request, case_id, Encounter.Mode.TREE)
    if encounter.status != Encounter.Status.COMPLETED:
        return redirect('decision_tree_case', case_id=case.id)

    tree = get_tree(case)
    answers = list(encounter.decision_answers.all())
    return render(
        request,
        'tree_transcript.html',
        {
            'case': case,
            'encounter': encounter,
            'tree': tree,
            'answers': answers,
        },
    )
