from __future__ import annotations

from django.db import models
from django.db.models import Count, F, FloatField, Sum
from django.db.models.expressions import ExpressionWrapper

from assessment.models import AssessmentAttempt, UserResponse
from assessment.services.counsellor_message_service import build_counsellor_message
from assessment.services.domain_config import domain_has_config
from assessment.services.universal_scoring_service import evaluate_domain
from domain.models import Domain
from domain_career_mapping.models import DomainCareerMapping


# ── Education level codes ─────────────────────────────────────────────────────
# These match EducationLevel.level_code values in the DB.
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

# ── Fallback stream codes (used only if DB has no Stream records for that level) ─
_FALLBACK_STREAM_CODES: dict[str, set[str]] = {
    LEVEL_10TH: {
        "science",
        "commerce",
        "arts",
        "vocational",
        "sports",
        "fine_arts",
        "agriculture",
    },
    LEVEL_12TH: {"science", "commerce", "arts", "vocational", "sports", "fine_arts"},
}


def _get_stream_codes_for_level(level_code: str) -> set[str]:
    """Load active stream codes for a given education level from DB. Falls back to _FALLBACK_STREAM_CODES."""
    from stream.models import Stream

    codes = set(
        Stream.objects.filter(
            education_level__level_code=level_code,
            is_active=True,
            deleted=False,
        ).values_list("stream_code", flat=True)
    )
    return codes if codes else _FALLBACK_STREAM_CODES.get(level_code, set())


def _get_education_level_sequence(level_code: str) -> int:
    """
    Return sequence_order for a level_code from the DB.
    Falls back to 0 if not found, which safely skips career-level filtering.
    """
    from education_level.models import EducationLevel

    try:
        obj = (
            EducationLevel.objects.filter(
                level_code__iexact=level_code, is_active=True, deleted=False
            )
            .only("sequence_order")
            .first()
        )
        if obj:
            return int(obj.sequence_order)
    except Exception:
        pass
    return 0


def _latest_user_responses(user_id):
    latest_attempt = (
        AssessmentAttempt.objects.filter(user_id=user_id, completed_at__isnull=False)
        .order_by("-completed_at")
        .first()
    )
    if latest_attempt:
        return UserResponse.objects.filter(attempt=latest_attempt)
    return UserResponse.objects.filter(user_id=user_id)


class RecommendationEngineService:
    """
    Education-level aware recommendation engine.

    - 10th  → stream recommendations (which stream to pick for 11th/12th)
    - 12th  → domain/field recommendations (which college degree path to pursue)
    - ITI/Diploma → entry-level career + domain recommendations
    - Grad/PG/PhD/Professional → full career + domain recommendations
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

        # Attach counsellor message to every result
        result["counsellor"] = build_counsellor_message(
            level_code=result.get("education_level") or level_code,
            recommendation_type=result.get("recommendation_type"),
            top_stream=result.get("top_stream"),
            stream_ranking=result.get("stream_ranking", []),
            top_domain=result.get("top_domain"),
            domain_ranking=result.get("domain_ranking", []),
            top_career=result.get("top_career"),
            career_scores=result.get("career_scores", {}),
            confidence=result.get("confidence", 0),
            is_entry_level=result.get("is_entry_level", False),
        )
        return result

    # ------------------------------------------------------------------
    # 10th grade: recommend streams
    # ------------------------------------------------------------------
    def _recommend_streams(self, *, user_id):
        """
        Score streams based on user responses to questions that have mapped_streams.
        Returns ranked list of streams suitable for 10th-grade users.
        """
        from assessment.models import Question

        weighted_expr = ExpressionWrapper(
            F("score_value") * F("question__signal_strength"), output_field=FloatField()
        )
        max_expr = ExpressionWrapper(
            F("question__signal_strength") * 5.0, output_field=FloatField()
        )

        rows = (
            _latest_user_responses(user_id).filter(
                question__mapped_streams__stream_code__in=_get_stream_codes_for_level(
                    LEVEL_10TH
                ),
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
            normalized = (
                (weighted_sum / max_possible * 100.0) if max_possible > 0 else 0.0
            )
            stream_ranking.append(
                {
                    "stream_id": str(row["question__mapped_streams__id"]),
                    "stream_code": row["question__mapped_streams__stream_code"],
                    "stream_name": row["question__mapped_streams__stream_name"],
                    "score": int(round(max(0.0, min(100.0, normalized)))),
                }
            )

        if not stream_ranking:
            return self._fallback_result(education_level=LEVEL_10TH)

        confidence = self._stream_confidence(stream_ranking)

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

    def _stream_confidence(self, stream_ranking: list[dict]) -> int:
        return self._calc_confidence(stream_ranking, score_key="score")

    @staticmethod
    def _calc_confidence(ranking: list[dict], score_key: str = "score") -> int:
        """
        Realistic confidence based on:
        - Top score (how strong is the signal)
        - Separation from #2 (how clear is the winner)
        - Question coverage (how many questions backed this up)
        Never returns 100 unless there's overwhelming evidence.
        """
        if not ranking:
            return 0

        top_score = ranking[0].get(score_key, 0)
        q_count = ranking[0].get("question_count", 1)

        # Score component: top score scaled down — 80 score → ~56 confidence
        score_component = top_score * 0.70

        # Separation component: gap between #1 and #2
        if len(ranking) > 1:
            gap = top_score - ranking[1].get(score_key, 0)
            separation = min(20, gap * 0.5)
        else:
            separation = 15

        # Coverage component: more questions = more confidence, caps at 15
        coverage = min(15, q_count * 2.5)

        raw = score_component + separation + coverage
        # Cap at 88 — never show 100% confidence from a short assessment
        return int(round(min(88, max(0, raw))))

    # ------------------------------------------------------------------
    # 12th grade: recommend college degree domains
    # ------------------------------------------------------------------
    def _recommend_domains_for_college(self, *, user_id):
        """
        For 12th-grade users: rank domains as college degree path suggestions.
        Output is domain ranking only — no career scores yet (too early).
        """
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

        top_domain_id = domain_ranking[0]["domain_id"]
        top_domain = Domain.objects.filter(
            id=top_domain_id, deleted=False, is_active=True
        ).first()
        if top_domain is None:
            return self._fallback_result()

        generic_result = self._build_generic_result(
            top_domain=top_domain,
            domain_ranking=domain_ranking,
            level_code=level_code,
        )

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

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------
    def _get_education_level_code(self, user_id) -> str | None:
        from user_profile.models import UserProfile

        try:
            profile = UserProfile.objects.select_related("education_level").get(
                user_id=user_id
            )
            edu = profile.education_level
            return (edu.level_code or "").lower() if edu else None
        except UserProfile.DoesNotExist:
            return None

    def _evaluate_top_domain_decisions(
        self, *, user_id, domain_ranking: list[dict]
    ) -> dict[str, dict]:
        decisions: dict[str, dict] = {}
        for ranked_domain in domain_ranking[: self.DOMAIN_DECISION_TOP_N]:
            domain_code = (ranked_domain.get("domain_code") or "").strip().lower()
            if not domain_code or not domain_has_config(domain_code):
                continue
            domain_result = evaluate_domain(domain_code=domain_code, user_id=user_id)
            if domain_result:
                decisions[domain_code] = domain_result
        return decisions

    def _rank_domains(self, *, user_id):
        weighted_expr = ExpressionWrapper(
            F("score_value") * F("question__signal_strength"), output_field=FloatField()
        )
        max_expr = ExpressionWrapper(
            F("question__signal_strength") * 5.0, output_field=FloatField()
        )
        rows = (
            _latest_user_responses(user_id).filter(
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

        # Total questions answered by this user (for coverage penalty)
        total_answered = _latest_user_responses(user_id).count()

        domain_ranking = []
        for row in rows:
            max_possible = float(row.get("max_possible") or 0.0)
            weighted_sum = float(row.get("weighted_sum") or 0.0)
            q_count = int(row.get("question_count") or 0)

            if max_possible <= 0:
                continue

            # Raw score: how well the user answered questions mapped to this domain
            raw_score = (weighted_sum / max_possible) * 100.0

            # Coverage factor: penalise domains seen in very few questions
            # A domain seen in 1 question out of 20 answered should score lower
            # than one seen in 5 questions, even if both got perfect answers.
            # Coverage = min(1.0, q_count / max(1, total_answered * 0.15))
            # This means a domain needs ~15% of total questions to get full credit.
            coverage = min(1.0, q_count / max(1, total_answered * 0.15))

            # Blend: 70% raw score + 30% coverage-adjusted score
            adjusted = (raw_score * 0.70) + (raw_score * coverage * 0.30)

            domain_ranking.append(
                {
                    "domain_id": row["question__mapped_domains__id"],
                    "domain_code": row["question__mapped_domains__domain_code"],
                    "domain_name": row["question__mapped_domains__domain_name"],
                    "score": int(round(max(0.0, min(100.0, adjusted)))),
                    "question_count": q_count,
                    "_raw": raw_score,
                    "_weighted_sum": weighted_sum,
                }
            )

        # Sort: score desc, then question_count desc, then domain_code for determinism
        domain_ranking.sort(
            key=lambda d: (
                -d["score"],
                -d["question_count"],
                -d["_raw"],
                d["domain_code"],
            )
        )

        # Strip internal fields
        for d in domain_ranking:
            d.pop("_raw", None)
            d.pop("_weighted_sum", None)

        return domain_ranking

    def _build_generic_result(
        self,
        *,
        top_domain: Domain,
        domain_ranking: list[dict],
        level_code: str | None = None,
    ):
        top_domain_score = domain_ranking[0]["score"] if domain_ranking else 0

        mappings_qs = DomainCareerMapping.objects.filter(
            domain=top_domain,
            deleted=False,
            is_active=True,
            career__deleted=False,
            career__is_active=True,
        ).select_related("career", "career__min_education_level")

        # Filter careers appropriate for the user's education level using DB sequence_order.
        # e.g. don't show "Investment Banker (requires PG)" to a diploma student
        user_level_seq = _get_education_level_sequence(level_code or "")

        career_scores: dict[str, int] = {}
        for mapping in mappings_qs.order_by("-weight_score", "career__career_name"):
            career = mapping.career
            # Skip careers that require a higher education level than the user has
            if career.min_education_level:
                min_seq = int(
                    getattr(career.min_education_level, "sequence_order", 0) or 0
                )
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
