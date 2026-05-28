from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from career.models import Career
from domain.models import Domain
from domain_career_mapping.models import DomainCareerMapping
from domain_skill_mapping.models import DomainSkillMapping


class RecommendationDomainDetailAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, id, *args, **kwargs):
        domain = (
            Domain.objects.filter(id=id, is_active=True, deleted=False)
            .only(
                "id",
                "domain_name",
                "domain_code",
                "description",
                "future_relevance_score",
            )
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
            .order_by("career__career_name")
        )
        careers = [
            {"id": str(r.career_id), "name": r.career.career_name} for r in career_rows
        ]

        skill_rows = (
            DomainSkillMapping.objects.filter(
                domain_id=domain.id,
                is_active=True,
                deleted=False,
                skill__is_active=True,
                skill__deleted=False,
            )
            .select_related("skill")
            .order_by("skill__skill_name")
        )
        skills = [
            {"id": str(r.skill_id), "name": r.skill.skill_name} for r in skill_rows
        ]

        return Response(
            {
                "success": True,
                "data": {
                    "domain": {
                        "id": str(domain.id),
                        "code": domain.domain_code,
                        "name": domain.domain_name,
                        "description": domain.description,
                        "future_relevance_score": domain.future_relevance_score,
                    },
                    "related_careers": careers,
                    "required_skills": skills,
                },
            },
            status=status.HTTP_200_OK,
        )


class CareerDetailsAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, id, *args, **kwargs):
        career = (
            Career.objects.filter(id=id, is_active=True, deleted=False)
            .select_related("min_education_level", "max_education_level")
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
            .order_by("skill__skill_name")
        )
        seen = set()
        skills = []
        for r in skill_rows:
            if r.skill_id not in seen:
                seen.add(r.skill_id)
                skills.append({"id": str(r.skill_id), "name": r.skill.skill_name})

        min_edu = career.min_education_level
        max_edu = career.max_education_level
        return Response(
            {
                "success": True,
                "data": {
                    "id": str(career.id),
                    "code": career.career_code,
                    "name": career.career_name,
                    "description": career.description,
                    "required_skills": skills,
                    "eligibility": {
                        "min_education_level": {
                            "id": str(min_edu.id) if min_edu else None,
                            "name": (
                                getattr(min_edu, "display_name", None)
                                if min_edu
                                else None
                            ),
                        },
                        "max_education_level": {
                            "id": str(max_edu.id) if max_edu else None,
                            "name": (
                                getattr(max_edu, "display_name", None)
                                if max_edu
                                else None
                            ),
                        },
                    },
                },
            },
            status=status.HTTP_200_OK,
        )
