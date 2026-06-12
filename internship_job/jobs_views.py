from .models import Job
from .serializers import JobSerializer
from rest_framework import status
from rest_framework.decorators import action
from django.db import transaction
from rest_framework.response import Response
from common.master_view import BaseModelViewSet
from django.utils import timezone


class JobViewSet(BaseModelViewSet):
    queryset = Job.objects.select_related("city", "provider")
    serializer_class = JobSerializer

    search_fields = BaseModelViewSet.searching_fields + [
        "name",
        "organization_name",
        "description",
        "skills",
        "responsibilities",
        "education_tags__name",
        "experience_level",
        "job_type",
        "mode",
        "city__name",
        "salary_min",
        "salary_max",
        "provider__full_name",
        "why_this_match",
    ]
    ordering_fields = BaseModelViewSet.ordering_fields+[
        "name",
        "organization_name",
        "description",
        "education_tags",
        "experience_level",
        "job_type",
        "mode",
        "city",
        "salary_min",
        "salary_max",
        "provider",
        "why_this_match",
    ]

    @transaction.atomic()
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                provider=request.user,
                created_by=request.user,
                created_at=timezone.now(),
            )
            return Response(
                {
                    "success":True,
                    "data":serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {
                "success": False,
                "message": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    @transaction.atomic()
    def update(self, request, *args, **kwargs):
        job = self.get_object()

        if job.provider != request.user:
            return Response(
                {
                    "success": False,
                    "message": "You can only update jobs created by you."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)
    
    @transaction.atomic()
    def destroy(self, request, *args, **kwargs):
        job = self.get_object()
        
        if job.provider != request.user:
            return Response(
                {
                    "success": False,
                    "message":"You can only delete jobs created by you.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)
    
    