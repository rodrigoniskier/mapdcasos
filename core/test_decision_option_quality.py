import re

from django.test import TestCase

from .decision_option_texts import OPTION_TEXTS
from .decision_trees import get_tree
from .models import ClinicalCase


WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+(?:[-–][A-Za-zÀ-ÖØ-öø-ÿ0-9]+)?")
OBVIOUS_CUES = (
    " sempre ",
    " nunca ",
    " obrigatoriamente ",
    " exclusivamente ",
    " por ser mais forte ",
    " porque toda ",
    " porque todo ",
)


class DecisionOptionQualityTests(TestCase):
    def _case(self, order):
        return ClinicalCase.objects.create(
            code=f"B{order:02d}",
            category=ClinicalCase.Category.BACTERIA,
            order=order,
            public_title="Caso de teste",
            patient_name="Paciente Teste",
            age=30,
            sex="Feminino",
            difficulty=ClinicalCase.Difficulty.BASIC,
            complaint="Queixa de teste.",
            pathogen="Agente de teste",
            diagnosis="Diagnóstico de teste",
            master_context={},
            expected_management="Conduta de teste.",
            active=True,
        )

    def test_override_bank_is_complete(self):
        self.assertEqual(set(OPTION_TEXTS), set(range(1, 11)))
        total_nodes = 0
        total_options = 0
        for nodes in OPTION_TEXTS.values():
            self.assertEqual(len(nodes), 6)
            total_nodes += len(nodes)
            for qualities in nodes.values():
                self.assertEqual(
                    set(qualities),
                    {"BEST", "SUBOPTIMAL", "PLAUSIBLE", "WRONG"},
                )
                total_options += len(qualities)
        self.assertEqual(total_nodes, 60)
        self.assertEqual(total_options, 240)

    def test_rendered_options_have_similar_length_and_no_obvious_cues(self):
        checked_nodes = 0
        for order in range(1, 21):
            case = self._case(order)
            tree = get_tree(case)
            for node in tree["nodes"]:
                counts = [len(WORD_RE.findall(option["text"])) for option in node["options"]]
                self.assertGreaterEqual(
                    min(counts),
                    11,
                    f"{case.code}/{node['id']} tem alternativa curta demais: {counts}",
                )
                self.assertLessEqual(
                    max(counts),
                    24,
                    f"{case.code}/{node['id']} tem alternativa longa demais: {counts}",
                )
                self.assertLessEqual(
                    max(counts) - min(counts),
                    7,
                    f"{case.code}/{node['id']} denuncia resposta pelo comprimento: {counts}",
                )
                for option in node["options"]:
                    normalized = f" {option['text'].lower()} "
                    for cue in OBVIOUS_CUES:
                        self.assertNotIn(
                            cue,
                            normalized,
                            f"{case.code}/{node['id']} contém pista óbvia: {option['text']}",
                        )
                checked_nodes += 1
        self.assertEqual(checked_nodes, 120)

    def test_balancing_does_not_change_quality_or_score_model(self):
        case = self._case(1)
        tree = get_tree(case)
        self.assertEqual(tree["max_points"], 24)
        for node in tree["nodes"]:
            self.assertEqual(
                {option["quality"] for option in node["options"]},
                {"BEST", "SUBOPTIMAL", "PLAUSIBLE", "WRONG"},
            )
            self.assertEqual(
                {option["points"] for option in node["options"]},
                {4, 3, 1, 0},
            )
