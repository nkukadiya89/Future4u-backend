from django.shortcuts import render
from .models import Internship
from .serializers import InternshipSerializer
from common.master_view import BaseModelViewSet
from rest_framework import status
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from rest_framework.decorators import action
from rest_framework import status
from assessment_career.models import CareerRecommendationSuggestion
from.service import match_internships

# Create your views here.

class InternshipViewSet(BaseModelViewSet):
    queryset = Internship.objects.select_related("city","provider")
    serializer_class = InternshipSerializer

    search_fields = BaseModelViewSet.searching_fields +[
        "name",
        "organization_name",
        "description",
        "responsibilities",
        "skills",
        "education_tags",
        "why_this_match",
        "mode",
        "duration",
        "city__name",
        "internship_type",
        "fees_amount",
        "stipend_amount",
    ]
    ordering_fields = BaseModelViewSet.ordering_fields + [
        "name",
        "organization_name",
        "internship_type",
        "mode",
        "provider",
        "city",
        "duration",
        "fees_amount",
        "stipend_amount",
        "certificate_provided"
    ]
    @transaction.atomic()
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                provider=request.user,
                created_by=request.user,
                created_at = timezone.now(),
            )
            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"success": False, "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    @action(detail=False, methods=["get"], url_path="internship-recommended")
    def internship_recommended(self, request):
        mode = request.query_params.get("mode")
        city_id = request.query_params.get("city_id")
        search = request.query_params.get("search")

        internship_qs = self.get_queryset()

        if mode:
            internship_qs = internship_qs.filter(mode=mode)
        if city_id:
            internship_qs = internship_qs.filter(city__id=city_id)
        if search:
            internship_qs = internship_qs.filter(
                title__icontains = search
            )


        career_id = request.query_params.get("career_id")
        if not career_id:
            return Response(
                {
                    "success":False,
                    "message": "Carrer_id is required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            career = (
                CareerRecommendationSuggestion.objects.get(
                    id = career_id,
                    recommendation__user = request.user,
                    deleted=False,
                    recommendation__deleted=False
                )
            )
        except CareerRecommendationSuggestion.DoesNotExist:
            return Response(
                {
                    "success":False,
                    "message": "Career not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        internships = match_internships(
            ai_skills=career.required_skills or [],
            ai_education=career.required_education or {},
            user=request.user,
            internships_qs = internship_qs,
        )
        data = []

        for item in internships:
            serializer_data = self.get_serializer(
                item["internship"]
            ).data

            data.append(
                {
                    "score" : item["score"],
                    "skill_matches":item["skill_matches"],
                    "internship": serializer_data,
                }
            )
        return Response(
            {
                "success":True,
                "count":len(data),
                "message":"Recommended internships",
                "data":data,
            },
            status=status.HTTP_200_OK
        )
            