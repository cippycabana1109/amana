import json
from typing import Any


PLAYBOOK_DEFAULT = {"rules": {}, "insights": []}


def load_playbook(path: str = "playbook.json") -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return PLAYBOOK_DEFAULT.copy()
        data.setdefault("rules", {})
        data.setdefault("insights", [])
        return data
    except FileNotFoundError:
        return PLAYBOOK_DEFAULT.copy()
    except Exception as e:
        print(f"[ACE] Failed to load playbook from {path}: {e}")
        return PLAYBOOK_DEFAULT.copy()


def save_playbook(playbook: dict, path: str = "playbook.json") -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(playbook, f, indent=2, sort_keys=True)
    except Exception as e:
        print(f"[ACE] Failed to save playbook to {path}: {e}")


class Generator:
    def generate(self, query: str, playbook: dict) -> str:
        rules = playbook.get("rules", {}) if isinstance(playbook, dict) else {}
        known_rules = ", ".join(sorted(rules.keys())) if rules else "none"
        return f"Detected fraud: {query}. Applied playbook rules: {known_rules}."


class Reflector:
    def reflect(self, response: str, ground_truth: dict[str, Any]) -> list[str]:
        insights: list[str] = []
        expected = ground_truth.get("expected")
        if expected and expected not in response:
            insights.append("Response mismatch: expected marker not present")

        label = ground_truth.get("label")
        if label == "false_positive":
            insights.append("Potential false positive: consider reducing risk on low-value deposits")
        elif label == "true_positive":
            insights.append("Confirmed fraud pattern: strengthen detection rule")
        else:
            insights.append("No ground truth available: record for review")

        return insights


class Curator:
    def curate(self, playbook: dict, insights: list[str]) -> dict:
        if not isinstance(playbook, dict):
            playbook = PLAYBOOK_DEFAULT.copy()

        playbook.setdefault("rules", {})
        playbook.setdefault("insights", [])

        for insight in insights:
            playbook["insights"].append(insight)

            if "false positive" in insight.lower():
                playbook["rules"].setdefault("fraud-001", "Ignore small deposits")
            if "confirmed fraud" in insight.lower():
                playbook["rules"].setdefault("fraud-002", "Escalate large late-night withdrawals")

        return playbook
