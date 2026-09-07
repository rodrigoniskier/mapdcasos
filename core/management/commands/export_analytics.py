import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Avg, Count, Max, Min, Q
from django.utils import timezone

from core.models import ClinicalCase, DecisionAnswer, Encounter, Message, User


class Command(BaseCommand):
    help = "Exporta métricas acadêmicas agregadas e anonimizadas do MAPD Casos."

    def handle(self, *args, **options):
        students = User.objects.filter(role=User.Role.STUDENT)

        total_enc = Encounter.objects.count()
        completed_enc = Encounter.objects.filter(
            status=Encounter.Status.COMPLETED
        ).count()

        active_students = students.filter(
            encounters__isnull=False
        ).distinct().count()

        completed_students = students.filter(
            encounters__status=Encounter.Status.COMPLETED
        ).distinct().count()

        period = Encounter.objects.aggregate(
            first=Min("started_at"),
            last=Max("updated_at"),
        )

        def local_iso(value):
            if not value:
                return None
            return timezone.localtime(value).isoformat()

        overall_score = Encounter.objects.filter(
            status=Encounter.Status.COMPLETED,
            score__isnull=False,
        ).aggregate(avg=Avg("score"))["avg"]

        modes = []
        for x in (
            Encounter.objects
            .values("mode")
            .annotate(
                students=Count("student", distinct=True),
                encounters=Count("id"),
                completed=Count(
                    "id",
                    filter=Q(status=Encounter.Status.COMPLETED),
                ),
                average_score=Avg(
                    "score",
                    filter=Q(
                        status=Encounter.Status.COMPLETED,
                        score__isnull=False,
                    ),
                ),
            )
            .order_by("mode")
        ):
            x["average_score"] = (
                round(x["average_score"], 2)
                if x["average_score"] is not None
                else None
            )
            x["completion_rate_pct"] = (
                round(x["completed"] * 100 / x["encounters"], 1)
                if x["encounters"]
                else 0
            )
            modes.append(x)

        categories = []
        for x in (
            Encounter.objects
            .values("case__category")
            .annotate(
                students=Count("student", distinct=True),
                encounters=Count("id"),
                completed=Count(
                    "id",
                    filter=Q(status=Encounter.Status.COMPLETED),
                ),
                average_score=Avg(
                    "score",
                    filter=Q(
                        status=Encounter.Status.COMPLETED,
                        score__isnull=False,
                    ),
                ),
            )
            .order_by("case__category")
        ):
            x["average_score"] = (
                round(x["average_score"], 2)
                if x["average_score"] is not None
                else None
            )
            x["completion_rate_pct"] = (
                round(x["completed"] * 100 / x["encounters"], 1)
                if x["encounters"]
                else 0
            )
            categories.append(x)

        qualities_qs = (
            DecisionAnswer.objects
            .values("quality")
            .annotate(n=Count("id"))
            .order_by("quality")
        )

        quality_counts = {
            x["quality"]: x["n"]
            for x in qualities_qs
        }

        total_decisions = sum(quality_counts.values())

        quality_percentages = {
            key: round(value * 100 / total_decisions, 1)
            if total_decisions else 0
            for key, value in quality_counts.items()
        }

        favorable = (
            quality_counts.get("BEST", 0)
            + quality_counts.get("SUBOPTIMAL", 0)
        )

        activity = (
            students
            .annotate(
                encounters_n=Count("encounters", distinct=True),
                completed_n=Count(
                    "encounters",
                    filter=Q(
                        encounters__status=Encounter.Status.COMPLETED
                    ),
                    distinct=True,
                ),
            )
            .filter(encounters_n__gt=0)
            .aggregate(
                average_encounters=Avg("encounters_n"),
                minimum_encounters=Min("encounters_n"),
                maximum_encounters=Max("encounters_n"),
                average_completed=Avg("completed_n"),
                maximum_completed=Max("completed_n"),
            )
        )

        turmas = list(
            students.exclude(turma="")
            .values("turma")
            .annotate(students=Count("id"))
            .order_by("turma")
        )

        usage = (
            students
            .annotate(
                encounters_n=Count("encounters", distinct=True),
                completed_n=Count(
                    "encounters",
                    filter=Q(
                        encounters__status=Encounter.Status.COMPLETED
                    ),
                    distinct=True,
                ),
                ai_n=Count(
                    "encounters",
                    filter=Q(encounters__mode=Encounter.Mode.AI),
                    distinct=True,
                ),
                tree_n=Count(
                    "encounters",
                    filter=Q(encounters__mode=Encounter.Mode.TREE),
                    distinct=True,
                ),
            )
        )

        active_n = usage.filter(encounters_n__gt=0).count()
        two_plus_encounters = usage.filter(encounters_n__gte=2).count()
        five_plus_encounters = usage.filter(encounters_n__gte=5).count()
        two_plus_completed = usage.filter(completed_n__gte=2).count()
        five_plus_completed = usage.filter(completed_n__gte=5).count()
        both_modes = usage.filter(ai_n__gt=0, tree_n__gt=0).count()

        adequate_completed = Encounter.objects.filter(
            status=Encounter.Status.COMPLETED,
            outcome=Encounter.Outcome.ADEQUATE,
        ).count()

        distinct_cases_used = (
            Encounter.objects
            .values("case_id")
            .distinct()
            .count()
        )

        award_metrics = {
            "engagement": {
                "active_students": active_n,
                "students_with_2plus_encounters": two_plus_encounters,
                "students_with_2plus_encounters_pct": round(
                    two_plus_encounters * 100 / active_n, 1
                ) if active_n else 0,
                "students_with_5plus_encounters": five_plus_encounters,
                "students_with_5plus_encounters_pct": round(
                    five_plus_encounters * 100 / active_n, 1
                ) if active_n else 0,
                "students_with_2plus_completed": two_plus_completed,
                "students_with_2plus_completed_pct": round(
                    two_plus_completed * 100 / active_n, 1
                ) if active_n else 0,
                "students_with_5plus_completed": five_plus_completed,
                "students_with_5plus_completed_pct": round(
                    five_plus_completed * 100 / active_n, 1
                ) if active_n else 0,
                "students_using_both_modes": both_modes,
                "students_using_both_modes_pct": round(
                    both_modes * 100 / active_n, 1
                ) if active_n else 0,
            },
            "measurable_benefits": {
                "completed_encounters": completed_enc,
                "completion_rate_pct": round(
                    completed_enc * 100 / total_enc, 1
                ) if total_enc else 0,
                "average_score": (
                    round(overall_score, 2)
                    if overall_score is not None
                    else None
                ),
                "adequate_completed_encounters": adequate_completed,
                "adequate_completed_encounters_pct": round(
                    adequate_completed * 100 / completed_enc, 1
                ) if completed_enc else 0,
                "structured_decisions": total_decisions,
                "best_or_suboptimal_decisions_pct": round(
                    favorable * 100 / total_decisions, 1
                ) if total_decisions else 0,
            },
            "university_impact": {
                "registered_students": students.count(),
                "active_students": active_n,
                "students_with_completed_case": completed_students,
                "student_messages": Message.objects.filter(
                    role=Message.Role.STUDENT
                ).count(),
                "clinical_decisions": total_decisions,
                "distinct_cases_used": distinct_cases_used,
            },
            "teaching_learning_contribution": {
                "study_modes": 2,
                "active_cases": ClinicalCase.objects.filter(active=True).count(),
                "case_categories": ClinicalCase.objects.filter(
                    active=True
                ).values("category").distinct().count(),
                "distinct_cases_already_used": distinct_cases_used,
                "student_generated_interactions": (
                    Message.objects.filter(
                        role=Message.Role.STUDENT
                    ).count()
                    + total_decisions
                ),
            },
            "originality": {
                "automatically_quantifiable": False,
                "evidence_requires_project_narrative": True,
            },
            "replicability_sustainability": {
                "automatically_quantifiable": False,
                "evidence_requires_architecture_and_implementation_narrative": True,
            },
        }

        case_categories = list(
            ClinicalCase.objects
            .filter(active=True)
            .values("category")
            .annotate(cases=Count("id"))
            .order_by("category")
        )

        messages = {
            "total": Message.objects.count(),
            "student": Message.objects.filter(
                role=Message.Role.STUDENT
            ).count(),
            "patient": Message.objects.filter(
                role=Message.Role.PATIENT
            ).count(),
            "preceptor": Message.objects.filter(
                role=Message.Role.PRECEPTOR
            ).count(),
            "tutor": Message.objects.filter(
                role=Message.Role.TUTOR
            ).count(),
            "system": Message.objects.filter(
                role=Message.Role.SYSTEM
            ).count(),
        }

        data = {
            "project": "MAPD Casos",
            "generated_at": timezone.localtime().isoformat(),
            "privacy": {
                "contains_personal_data": False,
                "contains_names": False,
                "contains_rgm": False,
                "contains_email": False,
                "aggregation_only": True,
            },
            "usage_period": {
                "first_use": local_iso(period["first"]),
                "last_use": local_iso(period["last"]),
            },
            "students": {
                "registered": students.count(),
                "active": active_students,
                "with_completed_case": completed_students,
                "activation_rate_pct": round(
                    active_students * 100 / students.count(), 1
                ) if students.count() else 0,
                "completed_case_rate_pct": round(
                    completed_students * 100 / active_students, 1
                ) if active_students else 0,
            },
            "cases": {
                "active": ClinicalCase.objects.filter(active=True).count(),
                "by_category": case_categories,
            },
            "encounters": {
                "total": total_enc,
                "completed": completed_enc,
                "completion_rate_pct": round(
                    completed_enc * 100 / total_enc, 1
                ) if total_enc else 0,
                "average_score": (
                    round(overall_score, 2)
                    if overall_score is not None
                    else None
                ),
                "by_mode": modes,
                "by_category": categories,
            },
            "decisions": {
                "total": total_decisions,
                "quality_counts": quality_counts,
                "quality_percentages": quality_percentages,
                "best_or_suboptimal_pct": round(
                    favorable * 100 / total_decisions, 1
                ) if total_decisions else 0,
            },
            "award_metrics": award_metrics,
            "messages": messages,
            "student_activity": {
                key: round(value, 2)
                if isinstance(value, float)
                else value
                for key, value in activity.items()
            },
        }

        output_dir = Path(settings.BASE_DIR) / "analytics"
        output_dir.mkdir(exist_ok=True)

        output_file = output_dir / "summary.json"

        with output_file.open("w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Analytics exportado para {output_file}"
            )
        )
