from django.test import TestCase

from .decision_trees import get_tree
from .models import ClinicalCase
from .templatetags.decision_learning import best_option, learning_note


class DecisionLearningCoverageTests(TestCase):
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

    def test_every_bacterial_decision_has_theory_pearl_and_basis(self):
        checked = 0
        for order in range(1, 21):
            case = self._case(order)
            tree = get_tree(case)
            for node in tree["nodes"]:
                note = learning_note(node, case)
                self.assertTrue(note["theory"], f"{case.code}/{node['id']} sem teoria")
                self.assertTrue(note["pearl"], f"{case.code}/{node['id']} sem pérola")
                self.assertTrue(note["pearl_basis"], f"{case.code}/{node['id']} sem justificativa da pérola")
                self.assertTrue(note["base"], f"{case.code}/{node['id']} sem base de revisão")
                best = best_option(node)
                self.assertEqual(best.get("quality"), "BEST")
                checked += 1
        self.assertEqual(checked, 120)

    def test_generated_pearl_does_not_change_answer_order_or_scoring(self):
        case = self._case(1)
        tree_before = get_tree(case)
        positions_before = [option["quality"] for option in tree_before["nodes"][0]["options"]]
        note = learning_note(tree_before["nodes"][0], case)
        self.assertTrue(note["pearl"])
        tree_after = get_tree(case)
        positions_after = [option["quality"] for option in tree_after["nodes"][0]["options"]]
        self.assertEqual(positions_before, positions_after)
        self.assertEqual(tree_after["max_points"], 24)
