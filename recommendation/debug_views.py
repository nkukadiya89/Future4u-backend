from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from services import recommendation_engine_service as engine
from stream_domain_mapping.models import StreamDomainMapping
from utils.throttles import PerUserBurstRateThrottle


class RecommendationDebugAPIView(APIView):
    """
    INTERNAL DEBUG ONLY
    GET /api/system/recommendation-debug/
    - admin/staff only
    - does not alter recommendation engine logic
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminUser]
    throttle_classes = [PerUserBurstRateThrottle]

    def get(self, request, *args, **kwargs):
        user_id = request.user.id

        # Reuse engine internals to avoid duplicating business logic.
        ctx = engine._fetch_user_context(user_id=user_id)  # noqa: SLF001
        dim_scores = engine._assessment_dimension_scores_0_100(user_id=user_id)  # noqa: SLF001
        base = engine._base_domain_score(dim_scores)  # noqa: SLF001
        top_dim, top_dim_score = engine._top_factor(dim_scores)  # noqa: SLF001

        stream_domain = []
        domain_scores = []

        if ctx is not None:
            qs = (
                StreamDomainMapping.objects.filter(
                    stream_id=ctx.stream_id,
                    deleted=False,
                    is_active=True,
                    domain__deleted=False,
                    domain__is_active=True,
                )
                .select_related("domain")
                .only(
                    "id",
                    "weight_score",
                    "is_primary",
                    "domain__id",
                    "domain__domain_code",
                    "domain__domain_name",
                    "domain__future_relevance_score",
                )
            )
            rows = list(qs)
            for m in rows:
                d = m.domain
                mapping_weight = int(getattr(m, "weight_score", 0) or 0)
                final = (float(base) * 0.6) + (mapping_weight * 0.4)
                stream_domain.append(
                    {
                        "mapping_id": str(m.id),
                        "domain_id": str(d.id),
                        "domain_code": d.domain_code,
                        "domain_name": d.domain_name,
                        "mapping_weight": mapping_weight,
                        "is_primary": bool(getattr(m, "is_primary", False)),
                    }
                )
                domain_scores.append(
                    {
                        "domain_id": str(d.id),
                        "domain_name": d.domain_name,
                        "base_score": round(float(base), 2),
                        "mapping_weight": mapping_weight,
                        "final_score": round(float(final), 2),
                        "reason": engine._domain_reason(  # noqa: SLF001
                            top_dim=top_dim,
                            top_dim_score=float(top_dim_score),
                            mapping_weight=mapping_weight,
                            domain_future_relevance=getattr(d, "future_relevance_score", None),
                        ),
                    }
                )

            domain_scores.sort(key=lambda x: (-float(x["final_score"]), x["domain_name"], x["domain_id"]))

        data = {
            "user_id": user_id,
            "has_context": ctx is not None,
            "context": (
                {
                    "stream_id": str(ctx.stream_id),
                    "education_sequence": int(ctx.education_sequence),
                }
                if ctx is not None
                else None
            ),
            "assessment_scores_0_100": dim_scores,
            "top_factor": {"dimension": top_dim, "score": round(float(top_dim_score), 2)},
            "base_domain_score": round(float(base), 2),
            "mapping_weights": stream_domain,
            "raw_domain_scores": domain_scores,
        }
        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)

