"""Aplica as alternativas calibradas aos cenários da árvore decisória."""

from .decision_option_texts import OPTION_TEXTS


def install_balanced_options():
    # Import tardio evita ciclo durante a inicialização do app Django.
    from . import decision_trees

    for profile, nodes in OPTION_TEXTS.items():
        scenario = decision_trees.SCENARIOS.get(profile)
        if not scenario:
            continue
        by_id = {node["id"]: node for node in scenario["nodes"]}
        for node_id, texts in nodes.items():
            node = by_id.get(node_id)
            if not node:
                continue
            for option in node["options"]:
                replacement = texts.get(option["quality"])
                if replacement:
                    option["text"] = replacement
