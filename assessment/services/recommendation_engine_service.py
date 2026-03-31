from __future__ import annotations

from django.db.models import F, FloatField, Sum
from django.db.models.expressions import ExpressionWrapper

from assessment.models import UserResponse
from assessment.services.domain_config import DOMAIN_CONFIG
from assessment.services.universal_scoring_service import evaluate_domain
from domain.models import Domain
from domain_career_mapping.models import DomainCareerMapping


class RecommendationEngineService:
    """
    Generic recommendation engine with optional domain-specific decision layers.
    Sports is the first decision layer and can override generic output.
    """

    DOMAIN_DECISION_TOP_N = 3

    def recommend(self, *, user_id):
        domain_ranking = self._rank_domains(user_id=user_id)
        if not domain_ranking:
            return self._fallback_result()

        top_domain_id = domain_ranking[0]["domain_id"]
        top_domain = Domain.objects.filter(id=top_domain_id, deleted=False, is_active=True).first()
        if top_domain is None:
            return self._fallback_result()

        generic_result = self._build_generic_result(top_domain=top_domain, domain_ranking=domain_ranking)

        # Domain decision layer integration:
        # evaluate configured top-ranked domains and override when a domain-specific score exists.
        decision_results = self._evaluate_top_domain_decisions(
            user_id=user_id,
            domain_ranking=domain_ranking,
        )

        top_domain_code = (top_domain.domain_code or "").strip().lower()
        top_decision = decision_results.get(top_domain_code)
        if top_decision:
            merged = dict(generic_result)
            merged.update(top_decision)
            merged["domain_ranking"] = domain_ranking
            merged["domain_decisions"] = decision_results
            return merged

        if decision_results:
            first_decision = next(iter(decision_results.values()))
            merged = dict(generic_result)
            merged.update(first_decision)
            merged["domain_ranking"] = domain_ranking
            merged["domain_decisions"] = decision_results
            return merged

        return generic_result

    def _evaluate_top_domain_decisions(self, *, user_id, domain_ranking: list[dict]) -> dict[str, dict]:
        decisions: dict[str, dict] = {}
        for ranked_domain in domain_ranking[: self.DOMAIN_DECISION_TOP_N]:
            domain_code = (ranked_domain.get("domain_code") or "").strip().lower()
            if not domain_code or domain_code not in DOMAIN_CONFIG:
                continue
            domain_result = evaluate_domain(domain_code=domain_code, user_id=user_id)
            if domain_result:
                decisions[domain_code] = domain_result
        return decisions

    def _rank_domains(self, *, user_id):
        weighted_expr = ExpressionWrapper(F("score_value") * F("question__signal_strength"), output_field=FloatField())
        max_expr = ExpressionWrapper(F("question__signal_strength") * 5.0, output_field=FloatField())
        rows = (
            UserResponse.objects.filter(
                user_id=user_id,
                question__mapped_domains__deleted=False,
                question__mapped_domains__is_active=True,
            )
            .values(
                "question__mapped_domains__id",
                "question__mapped_domains__domain_code",
                "question__mapped_domains__domain_name",
            )
            .annotate(
                weighted_sum=Sum(weighted_expr, output_field=FloatField()),
                max_possible=Sum(max_expr, output_field=FloatField()),
            )
            .order_by("-weighted_sum")
        )

        domain_ranking = []
        for row in rows:
            max_possible = float(row.get("max_possible") or 0.0)
            weighted_sum = float(row.get("weighted_sum") or 0.0)
            normalized = (weighted_sum / max_possible * 100.0) if max_possible > 0 else 0.0
            domain_ranking.append(
                {
                    "domain_id": row["question__mapped_domains__id"],
                    "domain_code": row["question__mapped_domains__domain_code"],
                    "domain_name": row["question__mapped_domains__domain_name"],
                    "score": int(round(max(0.0, min(100.0, normalized)))),
                }
            )
        return domain_ranking

    def _build_generic_result(self, *, top_domain: Domain, domain_ranking: list[dict]):
        top_domain_score = domain_ranking[0]["score"] if domain_ranking else 0
        mappings = (
            DomainCareerMapping.objects.filter(
                domain=top_domain,
                deleted=False,
                is_active=True,
                career__deleted=False,
                career__is_active=True,
            )
            .select_related("career")
            .order_by("-weight_score", "career__career_name")
        )

        career_scores: dict[str, int] = {}
        for mapping in mappings:
            key = mapping.career.career_code or str(mapping.career.id)
            score = int(round((mapping.weight_score * top_domain_score) / 100.0))
            career_scores[key] = max(0, min(100, score))

        top_career = None
        if career_scores:
            top_career = max(career_scores.items(), key=lambda item: item[1])[0]

        return {
            "domain": (top_domain.domain_code or "").lower(),
            "career_scores": career_scores,
            "top_career": top_career,
            "domain_ranking": domain_ranking,
        }

    @staticmethod
    def _fallback_result():
        return {
            "domain": None,
            "career_scores": {},
            "top_career": None,
            "confidence": 0,
            "domain_ranking": [],
        }
