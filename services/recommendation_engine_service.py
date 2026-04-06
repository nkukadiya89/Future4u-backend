from __future__ import annotations

from django.db import models
from django.db.models import Count, F, FloatField, Sum
from django.db.models.expressions import ExpressionWrapper

from assessment.models import UserResponse
from assessment.services.counsellor_message_service import build_counsellor_message
from assessment.services.domain_config import DOMAIN_CONFIG
from assessment.services.universal_scoring_service import evaluate_domain
from domain.models import Domain
from domain_career_mapping.models import DomainCareerMapping


LEVEL_10TH = "secondary"
LEVEL_12TH = "higher_secondary"
LEVEL_ITI = "iti"
LEVEL_DIPLOMA = "diploma"
LEVEL_GRAD = "graduation"
LEVEL_PG = "post_graduation"
LEVEL_PHD = "doctorate"
LEVEL_PROFESSIONAL = "professional"

STREAM_RECOMMENDATION_LEVELS = {LEVEL_10TH}
DOMAIN_RECOMMENDATION_LEVELS = {LEVEL_12TH}
ENTRY_CAREER_LEVELS = {LEVEL_ITI, LEVEL_DIPLOMA}
FULL_CAREER_LEVELS = {LEVEL_GRAD, LEVEL_PG, LEVEL_PHD, LEVEL_PROFESSIONAL}

TENTH_GRADE_STREAM_CODES = {
    "science", "commerce", "arts", "vocational",
    "sports", "fine_arts", "agriculture",
}


class RecommendationEngineService:
    """
    Education-level aware recommendation engine.
    - 10th  -> stream recommendations
    - 12th  -> domain/field recommendations
    - ITI/Diploma -> entry-level career + domain
    - Grad/PG/PhD/Professional -> full career + domain
    """

    DOMAIN_DECISION_TOP_N = 3

    def recommend(self, *, user_id):
        level_code = self._get_education_level_code(user_id)

        if level_code in STREAM_RECOMMENDATION_LEVELS:
            result = self._recommend_streams(user_id=user_id)
        elif level_code in DOMAIN_RECOMMENDATION_LEVELS:
            result = self._recommend_domains_for_college(user_id=user_id)
        else:
            result = self._recommend_careers(user_id=user_id, level_code=level_code)
            result["education_level"] = level_code
            result["is_entry_level"] = level_code in ENTRY_CAREER_LEVELS

        top_domain = result.get("top_domain") or result.get("domain")
        result["counsellor"] = build_counsellor_message(
            level_code=result.get("education_level") or level_code,
            recommendation_type=result.get("recommendation_type"),
            top_stream=result.get("top_stream"),
            stream_ranking=result.get("stream_ranking", []),
            top_domain=top_domain,
            domain_ranking=result.get("domain_ranking", []),
            top_career=result.get("top_career"),
            career_scores=result.get("career_scores", {}),
            confidence=result.get("confidence", 0),
            is_entry_level=result.get("is_entry_level", False),
            override_reason=result.get("override_reason"),
        )
        return result

    def _recommend_streams(self, *, user_id):
        weighted_expr = ExpressionWrapper(
            (6.0 - F("score_value")) * F("question__signal_strength"), output_field=FloatField()
        )
        max_expr = ExpressionWrapper(
            F("question__signal_strength") * 5.0, output_field=FloatField()
        )
        rows = (
            UserResponse.objects.filter(
                user_id=user_id,
                question__mapped_streams__stream_code__in=TENTH_GRADE_STREAM_CODES,
                question__mapped_streams__is_active=True,
                question__mapped_streams__deleted=False,
            )
            .values(
                "question__mapped_streams__id",
                "question__mapped_streams__stream_code",
                "question__mapped_streams__stream_name",
            )
            .annotate(
                weighted_sum=Sum(weighted_expr, output_field=FloatField()),
                max_possible=Sum(max_expr, output_field=FloatField()),
            )
            .order_by("-weighted_sum")
        )

        stream_ranking = []
        for row in rows:
            max_possible = float(row.get("max_possible") or 0.0)
            weighted_sum = float(row.get("weighted_sum") or 0.0)
            normalized = (weighted_sum / max_possible * 100.0) if max_possible > 0 else 0.0
            stream_ranking.append({
                "stream_id": str(row["question__mapped_streams__id"]),
                "stream_code": row["question__mapped_streams__stream_code"],
                "stream_name": row["question__mapped_streams__stream_name"],
                "score": int(round(max(0.0, min(100.0, normalized)))),
            })

        if not stream_ranking:
            return self._fallback_result(education_level=LEVEL_10TH)

        stream_ranking.sort(key=lambda s: -s["score"])
        confidence = self._calc_confidence(stream_ranking, score_key="score")

        return {
            "education_level": LEVEL_10TH,
            "recommendation_type": "stream",
            "top_stream": stream_ranking[0]["stream_code"] if stream_ranking else None,
            "stream_ranking": stream_ranking,
            "domain_ranking": [],
            "career_scores": {},
            "top_career": None,
            "confidence": confidence,
        }

    def _recommend_domains_for_college(self, *, user_id):
        domain_ranking = self._rank_domains(user_id=user_id)
        if not domain_ranking:
            return self._fallback_result(education_level=LEVEL_12TH)

        confidence = self._calc_confidence(domain_ranking)
        return {
            "education_level": LEVEL_12TH,
            "recommendation_type": "college_domain",
            "top_domain": domain_ranking[0]["domain_code"] if domain_ranking else None,
            "domain_ranking": domain_ranking,
            "career_scores": {},
            "top_career": None,
            "confidence": confidence,
        }

    def _recommend_careers(self, *, user_id, level_code: str | None = None):
        domain_ranking = self._rank_domains(user_id=user_id)
        if not domain_ranking:
            return self._fallback_result()

        LEVEL_ORDER = {
            "secondary": 2, "higher_secondary": 3, "iti": 4, "diploma": 5,
            "graduation": 6, "post_graduation": 7, "doctorate": 8, "professional": 9,
        }
        user_level_seq = LEVEL_ORDER.get(level_code or "", 0)

        top_domain = None
        top_domain_override_reason = None
        for i, ranked in enumerate(domain_ranking[:5]):
            candidate = Domain.objects.filter(
                id=ranked["domain_id"], deleted=False, is_active=True
            ).first()
            if candidate is None:
                continue
            career_qs = DomainCareerMapping.objects.filter(
                domain=candidate, deleted=False, is_active=True,
                career__deleted=False, career__is_active=True,
            ).select_related("career__min_education_level")
            eligible = [
                m for m in career_qs
                if not m.career.min_education_level or user_level_seq == 0
                or LEVEL_ORDER.get((m.career.min_education_level.level_code or "").lower(), 0) <= user_level_seq
            ]
            if eligible:
                if i > 0:
                    top_domain_override_reason = (
                        f"{domain_ranking[0]['domain_name']} scored highest but has no careers "
                        f"mapped at your level — showing {ranked['domain_name']} instead."
                    )
                top_domain = candidate
                break

        if top_domain is None:
            return self._fallback_result()

        generic_result = self._build_generic_result(
            top_domain=top_domain,
            domain_ranking=domain_ranking,
            level_code=level_code,
        )
        if top_domain_override_reason:
            generic_result["override_reason"] = top_domain_override_reason

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
            merged["override_reason"] = generic_result.get("override_reason")
            return merged

        if decision_results:
            first_decision = next(iter(decision_results.values()))
            merged = dict(generic_result)
            merged.update(first_decision)
            merged["domain_ranking"] = domain_ranking
            merged["domain_decisions"] = decision_results
            merged["override_reason"] = generic_result.get("override_reason")
            return merged

        return generic_result

    def _get_education_level_code(self, user_id) -> str | None:
        from user_profile.models import UserProfile
        try:
            profile = UserProfile.objects.select_related("education_level").get(user_id=user_id)
            edu = profile.education_level
            return (edu.level_code or "").lower() if edu else None
        except UserProfile.DoesNotExist:
            return None

    def _evaluate_top_domain_decisions(self, *, user_id, domain_ranking: list[dict]) -> dict[str, dict]:
        decisions: dict[str, dict] = {}
        for ranked_domain in domain_ranking[:self.DOMAIN_DECISION_TOP_N]:
            domain_code = (ranked_domain.get("domain_code") or "").strip().lower()
            if not domain_code or domain_code not in DOMAIN_CONFIG:
                continue
            domain_result = evaluate_domain(domain_code=domain_code, user_id=user_id)
            if domain_result:
                decisions[domain_code] = domain_result
        return decisions

    def _rank_domains(self, *, user_id):
        from user_profile.models import UserProfile
        weighted_expr = ExpressionWrapper(
            (6.0 - F("score_value")) * F("question__signal_strength"), output_field=FloatField()
        )
        max_expr = ExpressionWrapper(
            F("question__signal_strength") * 5.0, output_field=FloatField()
        )

        level_filter = models.Q(question__education_level__isnull=True)
        try:
            profile = UserProfile.objects.select_related("education_level").get(user_id=user_id)
            if profile.education_level:
                level_filter = (
                    models.Q(question__education_level=profile.education_level)
                    | models.Q(question__education_level__isnull=True)
                )
        except UserProfile.DoesNotExist:
            pass

        rows = (
            UserResponse.objects.filter(
                level_filter,
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
                question_count=Count("id", distinct=True),
            )
            .order_by("-weighted_sum", "-max_possible")
        )

        total_answered = UserResponse.objects.filter(level_filter, user_id=user_id).count()

        domain_ranking = []
        for row in rows:
            max_possible = float(row.get("max_possible") or 0.0)
            weighted_sum = float(row.get("weighted_sum") or 0.0)
            q_count = int(row.get("question_count") or 0)
            if max_possible <= 0:
                continue
            raw_score = (weighted_sum / max_possible) * 100.0
            coverage = min(1.0, q_count / max(1, total_answered * 0.20))
            adjusted = (raw_score * 0.60) + (raw_score * coverage * 0.40)
            domain_ranking.append({
                "domain_id": row["question__mapped_domains__id"],
                "domain_code": row["question__mapped_domains__domain_code"],
                "domain_name": row["question__mapped_domains__domain_name"],
                "score": int(round(max(0.0, min(100.0, adjusted)))),
                "question_count": q_count,
                "_raw": raw_score,
                "_weighted_sum": weighted_sum,
            })

        domain_ranking.sort(
            key=lambda d: (-d["score"], -d["question_count"], -d["_raw"], d["domain_code"])
        )
        for d in domain_ranking:
            d.pop("_raw", None)
            d.pop("_weighted_sum", None)

        return domain_ranking

    def _build_generic_result(self, *, top_domain: Domain, domain_ranking: list[dict], level_code: str | None = None):
        top_domain_score = domain_ranking[0]["score"] if domain_ranking else 0
        mappings_qs = DomainCareerMapping.objects.filter(
            domain=top_domain, deleted=False, is_active=True,
            career__deleted=False, career__is_active=True,
        ).select_related("career", "career__min_education_level")

        LEVEL_ORDER = {
            "secondary": 2, "higher_secondary": 3, "iti": 4, "diploma": 5,
            "graduation": 6, "post_graduation": 7, "doctorate": 8, "professional": 9,
        }
        user_level_seq = LEVEL_ORDER.get(level_code or "", 0)

        career_scores: dict[str, int] = {}
        for mapping in mappings_qs.order_by("-weight_score", "career__career_name"):
            career = mapping.career
            if career.min_education_level:
                min_seq = LEVEL_ORDER.get((career.min_education_level.level_code or "").lower(), 0)
                if user_level_seq > 0 and min_seq > user_level_seq:
                    continue
            key = career.career_code or str(career.id)
            score = int(round((mapping.weight_score * top_domain_score) / 100.0))
            career_scores[key] = max(0, min(100, score))

        top_career = None
        if career_scores:
            top_career = max(career_scores.items(), key=lambda item: item[1])[0]

        confidence = self._calc_confidence(domain_ranking)
        return {
            "recommendation_type": "career",
            "domain": (top_domain.domain_code or "").lower(),
            "career_scores": career_scores,
            "top_career": top_career,
            "domain_ranking": domain_ranking,
            "confidence": confidence,
        }

    @staticmethod
    def _calc_confidence(ranking: list[dict], score_key: str = "score") -> int:
        if not ranking:
            return 0
        top_score = ranking[0].get(score_key, 0)
        q_count = ranking[0].get("question_count", 1)
        score_component = top_score * 0.70
        if len(ranking) > 1:
            gap = top_score - ranking[1].get(score_key, 0)
            separation = min(20, gap * 0.5)
        else:
            separation = 15
        coverage = min(15, q_count * 2.5)
        raw = score_component + separation + coverage
        return int(round(min(88, max(0, raw))))

    @staticmethod
    def _fallback_result(education_level=None):
        return {
            "education_level": education_level,
            "recommendation_type": None,
            "domain": None,
            "top_stream": None,
            "top_domain": None,
            "career_scores": {},
            "top_career": None,
            "confidence": 0,
            "domain_ranking": [],
            "stream_ranking": [],
        }
