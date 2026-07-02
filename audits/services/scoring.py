"""Combines all check results into a single 0-100 overall score and a
good/warn/poor band, used to drive the report gauge.
"""
STATUS_POINTS = {"pass": 1.0, "warn": 0.9, "fail": 0.0}


def compute_overall_score(check_dicts: list[dict]) -> int:
    if not check_dicts:
        return 0
    total = sum(STATUS_POINTS.get(c["status"], 0) for c in check_dicts)
    return round((total / len(check_dicts)) * 100)


def score_band(score: int) -> tuple[str, str]:
    """Returns (band, human-readable label) for the given score."""
    if score >= 80:
        return "good", "Good, with minor gaps to close."
    if score >= 50:
        return "warn", "Needs work \u2014 several issues found."
    return "poor", "Poor \u2014 significant issues found."
