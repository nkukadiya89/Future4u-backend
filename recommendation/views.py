from django.db.models import Prefetch
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from career.models import Career
from domain.models import Domain
from domain_career_mapping.models import DomainCareerMapping
from domain_skill_mapping.models import DomainSkillMapping
from services.recommendation_engine_service import generate_recommendation
from django.core.cache import cache
from utils.cache_keys import recommendation_key
from utils.throttles import RecommendationRateThrottle
from recommendation.tasks import refresh_recommendation_cache_async


class RecommendationListAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [RecommendationRateThrottle]

    def get(self, request, *args, **kwargs):
        key = recommendation_key(request.user.id)
        try:
            cached = cache.get(key)
        except Exception:
            cached = None

        if cached is None:
            try:
                out = generate_recommendation(request.user.id)
            except Exception:
                out = {"message": "Unable to generate recommendations right now.", "tier": "unknown", "suggestion": [], "recommended_streams": [], "top_domains": [], "top_careers": [], "skill_gaps": [], "next_step": None}
            cached = {
                "message": out.get("message") or "ok",
                "tier": out.get("tier") or "unknown",
                "next_step": out.get("next_step"),
                "suggestion": out.get("suggestion") or [],
                "recommended_streams": out.get("recommended_streams") or [],
                "top_domains": out.get("top_domains") or [],
                "top_careers": out.get("top_careers") or [],
                "skill_gaps": out.get("skill_gaps") or [],
            }
            try:
                cache.set(key, cached, 60 * 5)
            except Exception:
                pass
        else:
            # Stale-while-revalidate: refresh in background (best-effort).
            # Does not change response shape or delay the request.
            try:
                refresh_recommendation_cache_async(request.user.id, ttl_seconds=60 * 5)
            except Exception:
                pass

        # Always return a non-empty structured payload for UX safety.
        if not isinstance(cached, dict):
            cached = {"message": "ok", "tier": "unknown", "next_step": None, "suggestion": [],
                      "recommended_streams": [], "top_domains": [], "top_careers": [], "skill_gaps": []}
        cached.setdefault("message", "ok")
        cached.setdefault("tier", "unknown")
        cached.setdefault("next_step", None)
        cached.setdefault("suggestion", [])
        cached.setdefault("recommended_streams", [])
        cached.setdefault("top_domains", [])
        cached.setdefault("top_careers", [])
        cached.setdefault("skill_gaps", [])

        return Response({"success": True, "data": cached}, status=status.HTTP_200_OK)


class RecommendationDomainDetailAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, id, *args, **kwargs):
        domain = (
            Domain.objects.filter(id=id, is_active=True, deleted=False)
            .only("id", "domain_name", "domain_code", "description", "future_relevance_score")
            .first()
        )
        if not domain:
            return Response(
                {"success": False, "message": "Domain not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )

        career_rows = (
            DomainCareerMapping.objects.filter(
                domain_id=domain.id,
                is_active=True,
                deleted=False,
                career__is_active=True,
                career__deleted=False,
            )
            .select_related("career")
            .only("career__id", "career__career_name")
            .order_by("career__career_name")
        )
        careers = [{"id": str(r.career_id), "name": r.career.career_name} for r in career_rows]

        skill_rows = (
            DomainSkillMapping.objects.filter(
                domain_id=domain.id,
                is_active=True,
                deleted=False,
                skill__is_active=True,
                skill__deleted=False,
            )
            .select_related("skill")
            .only("skill__id", "skill__skill_name")
            .order_by("skill__skill_name")
        )
        skills = [{"id": str(r.skill_id), "name": r.skill.skill_name} for r in skill_rows]

        data = {
            "domain": {
                "id": str(domain.id),
                "code": domain.domain_code,
                "name": domain.domain_name,
                "description": domain.description,
                "future_relevance_score": domain.future_relevance_score,
            },
            "related_careers": careers,
            "required_skills": skills,
        }
        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)


class CareerDetailsAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, id, *args, **kwargs):
        career = (
            Career.objects.filter(id=id, is_active=True, deleted=False)
            .select_related("min_education_level", "max_education_level")
            .only(
                "id",
                "career_name",
                "career_code",
                "description",
                "min_education_level__id",
                "min_education_level__display_name",
                "max_education_level__id",
                "max_education_level__display_name",
            )
            .first()
        )
        if not career:
            return Response(
                {"success": False, "message": "Career not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )

        domain_ids = list(
            DomainCareerMapping.objects.filter(
                career_id=career.id,
                is_active=True,
                deleted=False,
                domain__is_active=True,
                domain__deleted=False,
            )
            .values_list("domain_id", flat=True)
            .distinct()
        )

        skill_rows = (
            DomainSkillMapping.objects.filter(
                domain_id__in=domain_ids,
                is_active=True,
                deleted=False,
                skill__is_active=True,
                skill__deleted=False,
            )
            .select_related("skill")
            .only("skill__id", "skill__skill_name")
            .order_by("skill__skill_name")
        )
        # Deduplicate skills across domains
        seen = set()
        skills = []
        for r in skill_rows:
            if r.skill_id in seen:
                continue
            seen.add(r.skill_id)
            skills.append({"id": str(r.skill_id), "name": r.skill.skill_name})

        min_edu = getattr(career, "min_education_level", None)
        max_edu = getattr(career, "max_education_level", None)
        data = {
            "id": str(career.id),
            "code": career.career_code,
            "name": career.career_name,
            "description": career.description,
            "required_skills": skills,
            "eligibility": {
                "min_education_level": {
                    "id": str(min_edu.id) if min_edu else None,
                    "name": getattr(min_edu, "display_name", None) if min_edu else None,
                },
                "max_education_level": {
                    "id": str(max_edu.id) if max_edu else None,
                    "name": getattr(max_edu, "display_name", None) if max_edu else None,
                },
            },
        }
        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)

