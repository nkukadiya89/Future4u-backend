from __future__ import annotations

from collections.abc import Iterable

from assessment.models import UserResponse
from assessment.services.domain_config import get_domain_config
from domain.models import Domain


def _to_percent(score_value: float, max_score_per_answer: float) -> float:
    if max_score_per_answer <= 0:
        return 0.0
    return max(0.0, min(100.0, (float(score_value) / max_score_per_answer) * 100.0))


def _compare(operator: str, left_value: float, right_value: float) -> bool:
    op = (operator or "").lower()
    if op == "lt":
        return left_value < right_value
    if op == "lte":
        return left_value <= right_value
    if op == "gt":
        return left_value > right_value
    if op == "gte":
        return left_value >= right_value
    if op == "eq":
        return left_value == right_value
    return False


def _get_domain(domain_code: str) -> Domain | None:
    return Domain.objects.filter(
        domain_code__iexact=domain_code,
        deleted=False,
        is_active=True,
    ).first()


def _configured_dimensions(domain_cfg: dict) -> dict[str, float]:
    return {
        str(dimension_key).strip().lower(): float(weight)
        for dimension_key, weight in (domain_cfg.get("dimensions") or {}).items()
    }


def _collect_dimension_scores(
    *,
    domain_obj: Domain,
    user_id,
    dimension_weights: dict[str, float],
    missing_dimension_score: float,
    max_score_per_answer: float,
) -> tuple[dict[str, float], int]:
    responses = (
        UserResponse.objects.filter(
            user_id=user_id,
            question__mapped_domains=domain_obj,
            question__is_active=True,
        )
        .select_related("question")
        .distinct()
    )
    if not responses.exists():
        return {}, 0

    grouped = {
        dimension_key: {"total": 0.0, "weight": 0.0}
        for dimension_key in dimension_weights
    }
    response_count = 0

    for response in responses:
        dimension = (response.question.dimension or "").strip().lower()
        if dimension not in grouped:
            continue
        signal_strength = max(
            1, int(getattr(response.question, "signal_strength", 1) or 1)
        )
        grouped[dimension]["total"] += (
            _to_percent(response.score_value, max_score_per_answer) * signal_strength
        )
        grouped[dimension]["weight"] += signal_strength
        response_count += 1

    dimension_scores: dict[str, float] = {}
    for dimension_key, payload in grouped.items():
        if payload["weight"] <= 0:
            dimension_scores[dimension_key] = float(missing_dimension_score)
            continue
        dimension_scores[dimension_key] = payload["total"] / payload["weight"]
    return dimension_scores, response_count


def _score_careers(
    *,
    careers_cfg: dict,
    dimension_scores: dict[str, float],
    dimension_weights: dict[str, float],
) -> dict[str, int]:
    career_scores: dict[str, int] = {}
    for career_key, career_cfg in careers_cfg.items():
        factors = {
            str(k).strip().lower(): float(v)
            for k, v in (career_cfg.get("dimension_factors") or {}).items()
        }
        weighted_sum = 0.0
        total_weight = 0.0
        for dimension_key, global_weight in dimension_weights.items():
            factor = factors.get(dimension_key, 1.0)
            weighted_sum += dimension_scores[dimension_key] * global_weight * factor
            total_weight += global_weight * factor
        score = weighted_sum / total_weight if total_weight > 0 else 0.0
        career_scores[str(career_key)] = int(round(max(0.0, min(100.0, score))))
    return career_scores


def _apply_threshold_actions(*, actions: Iterable[dict], career_scores: dict[str, int]):
    for action in actions:
        action_type = (action.get("type") or "").strip().lower()
        if action_type != "multiply":
            continue
        career_key = str(action.get("career") or "").strip()
        if not career_key or career_key not in career_scores:
            continue
        multiplier = float(action.get("value", 1.0))
        career_scores[career_key] = int(
            round(max(0.0, min(100.0, career_scores[career_key] * multiplier)))
        )


def _apply_rules(
    *,
    domain_cfg: dict,
    dimension_scores: dict[str, float],
    career_scores: dict[str, int],
):
    rules_cfg = domain_cfg.get("rules") or {}

    for rule in rules_cfg.get("thresholds", []):
        dimension = str(rule.get("dimension") or "").strip().lower()
        operator = str(rule.get("operator") or "lt").strip().lower()
        threshold_value = float(rule.get("value", 0))
        if dimension not in dimension_scores:
            continue
        if _compare(operator, dimension_scores[dimension], threshold_value):
            _apply_threshold_actions(
                actions=rule.get("actions", []), career_scores=career_scores
            )

    for suppression in rules_cfg.get("suppressions", []):
        dimension = str(suppression.get("dimension") or "").strip().lower()
        operator = str(suppression.get("operator") or "lt").strip().lower()
        threshold_value = float(suppression.get("value", 0))
        if dimension not in dimension_scores:
            continue
        if not _compare(operator, dimension_scores[dimension], threshold_value):
            continue
        careers = suppression.get("careers") or {}
        for career_key, multiplier in careers.items():
            ckey = str(career_key).strip()
            if ckey not in career_scores:
                continue
            career_scores[ckey] = int(
                round(max(0.0, min(100.0, career_scores[ckey] * float(multiplier))))
            )


def _resolve_top_career(*, career_scores: dict[str, int], hybrid_margin: float):
    if not career_scores:
        return None
    ordered = sorted(career_scores.items(), key=lambda item: item[1], reverse=True)
    top_career = ordered[0][0]
    if len(ordered) > 1 and abs(ordered[0][1] - ordered[1][1]) <= hybrid_margin:
        top_career = f"hybrid: {ordered[0][0]} + {ordered[1][0]}"
    return top_career


def _compute_confidence(
    *,
    response_count: int,
    dimension_scores: dict[str, float],
    career_scores: dict[str, int],
    missing_dimension_score: float,
) -> int:
    if not career_scores:
        return 0

    configured_dimension_count = len(dimension_scores)
    answered_dimensions = len(
        [v for v in dimension_scores.values() if v != missing_dimension_score]
    )
    coverage = (
        (answered_dimensions / configured_dimension_count)
        if configured_dimension_count > 0
        else 0.0
    )
    response_signal = min(
        1.0, float(response_count) / max(1.0, configured_dimension_count)
    )

    ordered_scores = sorted(career_scores.values(), reverse=True)
    if len(ordered_scores) > 1:
        separation = min(1.0, max(0.0, (ordered_scores[0] - ordered_scores[1]) / 30.0))
    else:
        separation = 1.0

    confidence = (coverage * 0.5) + (response_signal * 0.2) + (separation * 0.3)
    return int(round(max(0.0, min(100.0, confidence * 100.0))))


def evaluate_domain(domain_code, user_id):
    domain_key = str(domain_code or "").strip().lower()
    domain_cfg = get_domain_config(domain_key)
    if not domain_cfg:
        return None

    domain_obj = _get_domain(domain_key)
    if not domain_obj:
        return None

    dimension_weights = _configured_dimensions(domain_cfg)
    if not dimension_weights:
        return None

    defaults_cfg = domain_cfg.get("defaults") or {}
    missing_dimension_score = float(defaults_cfg.get("missing_dimension_score", 50.0))
    max_score_per_answer = float(defaults_cfg.get("max_score_per_answer", 5.0))
    careers_cfg = domain_cfg.get("careers") or {}
    if not careers_cfg:
        return None

    dimension_scores, response_count = _collect_dimension_scores(
        domain_obj=domain_obj,
        user_id=user_id,
        dimension_weights=dimension_weights,
        missing_dimension_score=missing_dimension_score,
        max_score_per_answer=max_score_per_answer,
    )
    if not dimension_scores or response_count == 0:
        return None

    career_scores = _score_careers(
        careers_cfg=careers_cfg,
        dimension_scores=dimension_scores,
        dimension_weights=dimension_weights,
    )
    _apply_rules(
        domain_cfg=domain_cfg,
        dimension_scores=dimension_scores,
        career_scores=career_scores,
    )

    hybrid_margin = float((domain_cfg.get("rules") or {}).get("hybrid_margin", 5))
    top_career = _resolve_top_career(
        career_scores=career_scores, hybrid_margin=hybrid_margin
    )
    confidence = _compute_confidence(
        response_count=response_count,
        dimension_scores=dimension_scores,
        career_scores=career_scores,
        missing_dimension_score=missing_dimension_score,
    )

    return {
        "domain": domain_key,
        "career_scores": career_scores,
        "top_career": top_career,
        "confidence": confidence,
    }
