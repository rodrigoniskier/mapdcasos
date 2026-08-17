import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, OperationalError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .decision_trees import find_option, get_tree
from .models import ClinicalCase, DecisionAnswer, Encounter

logger = logging.getLogger(__name__)
QUALITY_LABELS = dict(DecisionAnswer.Quality.choices)


def _db_is_busy(exc: Exception) -> bool:
    text = str(exc).lower()
    return 'database is locked' in text or 'database is busy' in text


def _study_mode(request):
    mode = request.session.get('study_mode')
    if mode in {Encounter.Mode.AI, Encounter.Mode.TREE}:
        return mode
    return None


def _tree_encounter(request, case):
    """Get/create only the tree encounter without re-reading ClinicalCase.

    The previous flow looked up the case once in decision_tree_case() and then
    looked it up a second time inside the generic _student_case() helper.  The
    tree is a hot classroom path, so keep the case object already in memory and
    let get_or_create perform the minimum encounter work.
    """
    try:
        encounter, _ = Encounter.objects.get_or_create(
            student=request.user,
            case=case,
            mode=Encounter.Mode.TREE,
        )
    except IntegrityError:
        # Protect against two near-simultaneous first opens for the same student.
        encounter = Encounter.objects.get(
            student=request.user,
            case=case,
            mode=Encounter.Mode.TREE,
        )
    return encounter


def _complete_tree_encounter(encounter, tree, answers):
    """Finish from the answers already loaded in memory.

    Avoids an extra SELECT of all answers at the sixth decision.
    """
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


def _render_tree_case(request, case, encounter, tree, existing, *, status=200):
    current_node = next((node for node in tree['nodes'] if node['id'] not in existing), None)
    answered_rows = []
    for node in tree['nodes']:
        answer = existing.get(node['id'])
        if not answer:
            continue
        answered_rows.append(
            {
                'node': node,
                'answer': answer,
                'quality_label': QUALITY_LABELS.get(answer.quality, answer.quality),
            }
        )

    progress = len(existing)
    response = render(
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
        status=status,
    )
    if status == 503:
        response['Retry-After'] = '2'
    return response


def _render_tree_summary(request, case, encounter, tree, answers):
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


@login_required
def decision_tree_case(request, case_id):
    """Low-overhead decision-tree flow for the one-worker classroom profile.

    Important performance property: a valid answer is persisted and the next
    decision is rendered in the *same* HTTP response.  The old POST -> redirect
    -> GET pattern consumed two queued requests per click on PythonAnywhere.
    """
    if request.user.is_superuser:
        return redirect('professor_dashboard')
    if _study_mode(request) != Encounter.Mode.TREE:
        messages.info(request, 'Selecione primeiro a modalidade Árvore decisória.')
        return redirect('study_mode')

    case = get_object_or_404(ClinicalCase, id=case_id, active=True)
    if case.category != ClinicalCase.Category.BACTERIA:
        messages.info(request, 'A árvore decisória está disponível apenas para bactérias nesta etapa.')
        return redirect('dashboard')

    encounter = _tree_encounter(request, case)
    tree = get_tree(case)
    if encounter.status == Encounter.Status.COMPLETED:
        return redirect('tree_summary', case_id=case.id)

    # One ordered read per request; reuse these objects for progress, feedback
    # and final scoring instead of issuing COUNT() and a second answer SELECT.
    existing = {answer.node_id: answer for answer in encounter.decision_answers.all()}

    if request.method != 'POST':
        return _render_tree_case(request, case, encounter, tree, existing)

    current_node = next((node for node in tree['nodes'] if node['id'] not in existing), None)
    node_id = request.POST.get('node_id') or ''
    option_id = request.POST.get('option_id') or ''

    if not current_node or node_id != current_node['id']:
        messages.error(request, 'Esse ponto de decisão já foi respondido ou está fora de sequência.')
        return _render_tree_case(request, case, encounter, tree, existing)

    node, option = find_option(tree, node_id, option_id)
    if not node or not option:
        messages.error(request, 'Escolha uma alternativa válida.')
        return _render_tree_case(request, case, encounter, tree, existing)

    try:
        with transaction.atomic():
            answer = DecisionAnswer.objects.create(
                encounter=encounter,
                node_id=node['id'],
                prompt=node['prompt'],
                selected_option_id=option['id'],
                selected_text=option['text'],
                quality=option['quality'],
                points=option['points'],
                feedback=option['feedback'],
            )
            existing[answer.node_id] = answer
            if len(existing) == len(tree['nodes']):
                _complete_tree_encounter(encounter, tree, list(existing.values()))
    except IntegrityError:
        # Rare double click / retry: reload once and show the canonical state.
        encounter.refresh_from_db()
        existing = {answer.node_id: answer for answer in encounter.decision_answers.all()}
        messages.info(request, 'Essa decisão já foi registrada.')
    except OperationalError as exc:
        if not _db_is_busy(exc):
            raise
        logger.warning('Banco ocupado ao registrar decisão da árvore.', exc_info=True)
        messages.warning(
            request,
            'Muitos acessos neste momento. Sua resposta não foi perdida; tente enviar novamente em alguns segundos.',
        )
        return _render_tree_case(request, case, encounter, tree, existing, status=503)

    if encounter.status == Encounter.Status.COMPLETED:
        # Render the final summary directly; no final redirect + GET either.
        return _render_tree_summary(request, case, encounter, tree, list(existing.values()))

    # Critical optimization: return the next decision directly in this POST.
    return _render_tree_case(request, case, encounter, tree, existing)


@login_required
def tree_summary(request, case_id):
    case = get_object_or_404(
        ClinicalCase,
        id=case_id,
        category=ClinicalCase.Category.BACTERIA,
    )
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
    return _render_tree_summary(request, case, encounter, tree, answers)
