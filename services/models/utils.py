from __future__ import annotations


def risk_label_from_score(score: float) -> str:
    if score < 0.33:
        return "LOW"
    if score < 0.66:
        return "MEDIUM"
    return "HIGH"


def severity_label_from_idx(idx: int) -> str:
    mapping = {
        0: "no_injury",
        1: "minor",
        2: "serious",
        3: "fatal",
    }
    return mapping.get(idx, "minor")
