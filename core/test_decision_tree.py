from django.test import TestCase
from django.urls import reverse

from .decision_trees import QUALITY, find_option, get_tree
from .models import ClinicalCase, DecisionAnswer, Encounter, User


def make_case(order=1, category=ClinicalCase.Category.BACTERIA):
    return ClinicalCase.objects.create(
        code=f"{'B' if category == ClinicalCase.Category.BACTERIA else 'F'}{order:02d}",
        category=category,
        order=order,
        public_title="Caso de teste",
        patient_name="Paciente Teste",
        age=30,
        sex="Feminino",
        difficulty=ClinicalCase.Difficulty.BASIC,
        complaint="Queixa de teste.",
        pathogen="Agente de teste",
        diagnosis="Diagnóstico de teste",
        master_context={"variant_note": "Variação de teste."},
        expected_management="Conduta de teste.",
        active=True,
    )


class DecisionTreeContentTests(TestCase):
    def test_all_bacterial_cases_map_to_six_decision_points(self):
        for order in range(1, 21):
            case = make_case(order=order)
            tree = get_tree(case)
            self.assertEqual(len(tree["nodes"]), 6)
            self.assertEqual(tree["max_points"], 24)

    def test_each_node_has_exactly_one_option_of_each_quality(self):
        case = make_case(order=1)
        tree = get_tree(case)
        expected = set(QUALITY)
        for node in tree["nodes"]:
            self.assertEqual(len(node["options"]), 4)
            self.assertEqual({option["quality"] for option in node["options"]}, expected)
            self.assertTrue(node["prompt"].endswith("?"))

    def test_best_answer_position_varies_but_is_deterministic(self):
        positions = set()
        for order in range(1, 21):
            case = make_case(order=order)
            first = get_tree(case)
            second = get_tree(case)
            self.assertEqual(first, second)
            for node in first["nodes"]:
                positions.add(next(i for i, option in enumerate(node["options"]) if option["quality"] == "BEST"))
        self.assertGreaterEqual(len(positions), 3)

    def test_non_bacterial_case_has_no_tree(self):
        case = make_case(order=1, category=ClinicalCase.Category.FUNGI)
        with self.assertRaises(ValueError):
            get_tree(case)


class DecisionTreeFlowTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="12345",
            password="senha-forte",
            rgm="12345",
            first_name="Aluno",
        )
        self.case = make_case(order=1)
        self.client.force_login(self.student)

    def test_same_student_case_can_exist_in_ai_and_tree_modes(self):
        Encounter.objects.create(student=self.student, case=self.case, mode=Encounter.Mode.AI)
        Encounter.objects.create(student=self.student, case=self.case, mode=Encounter.Mode.TREE)
        self.assertEqual(Encounter.objects.filter(student=self.student, case=self.case).count(), 2)

    def test_mode_choice_is_saved_in_session(self):
        response = self.client.post(
            reverse("study_mode"),
            {"mode": Encounter.Mode.TREE},
            secure=True,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard"))
        self.assertEqual(self.client.session["study_mode"], Encounter.Mode.TREE)

    def _select_tree_mode(self):
        response = self.client.post(
            reverse("study_mode"),
            {"mode": Encounter.Mode.TREE},
            secure=True,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard"))

    def test_best_path_completes_with_100(self):
        self._select_tree_mode()

        tree = get_tree(self.case)
        for node in tree["nodes"]:
            best = next(option for option in node["options"] if option["quality"] == "BEST")
            response = self.client.post(
                reverse("decision_tree_case", args=[self.case.id]),
                {"node_id": node["id"], "option_id": best["id"]},
                secure=True,
            )
            self.assertEqual(response.status_code, 302)

        encounter = Encounter.objects.get(
            student=self.student,
            case=self.case,
            mode=Encounter.Mode.TREE,
        )
        self.assertEqual(encounter.status, Encounter.Status.COMPLETED)
        self.assertEqual(encounter.score, 100)
        self.assertEqual(encounter.decision_answers.count(), 6)
        self.assertEqual(
            encounter.decision_answers.filter(quality=DecisionAnswer.Quality.BEST).count(),
            6,
        )

    def test_tree_route_blocks_non_bacterial_case(self):
        fungi = make_case(order=2, category=ClinicalCase.Category.FUNGI)
        self._select_tree_mode()
        response = self.client.get(
            reverse("decision_tree_case", args=[fungi.id]),
            secure=True,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard"))
        self.assertFalse(
            Encounter.objects.filter(
                student=self.student,
                case=fungi,
                mode=Encounter.Mode.TREE,
            ).exists()
        )
