from django.shortcuts import render
from django.utils.timezone import now
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.filters import SearchFilter
from rest_framework.response import Response

from jobs.filters import JobFilters
from jobs.models import Job, JobApplication, JobPreference, JobSkill, SavedJob
from jobs.serializers import (
    JobApplicationSerializer,
    JobPreferenceSerializer,
    JobSerializer,
    JobSkillSerializer,
    SavedJobSerializer,
)


# Create your views here.
class JobViewSet(viewsets.ModelViewSet):
    serializer_class = JobSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = JobFilters
    search_fields = [
        "title",
        "company_name",
        "description",
        "location",
        "employment_type",
        "work_mode",
        "job_type",
        "application_deadline",
        "domain__domain_name",
    ]
    ordering_fields = [
        "created_at",
        "title",
        "company_name",
        "description",
        "location",
        "employment_type",
        "work_mode",
        "job_type",
        "application_deadline",
        "domain__domain_name",
    ]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Job.objects.filter(deleted=False, is_active=True).select_related(
            "domain", "updated_by"
        )

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(
                    {
                        "success": True,
                        "message": "Jobs retrieved successfully",
                        "data": serializer.data,
                    }
                )

            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {
                    "success": True,
                    "message": "Jobs retrieved successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error retrieving jobs: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(
                {
                    "success": True,
                    "message": "Job retrieved successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Job.DoesNotExist:
            return Response(
                {"success": False, "message": "Job not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error retrieving job: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def create(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return Response(
                    {
                        "success": False,
                        "message": "Authentication required",
                        "data": {},
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                serializer.save(updated_by=request.user)
                return Response(
                    {
                        "success": True,
                        "message": "Job created successfully",
                        "data": serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )

            return Response(
                {
                    "success": False,
                    "message": "Validation failed",
                    "data": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error creating job: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def update(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return Response(
                    {
                        "success": False,
                        "message": "Authentication required",
                        "data": {},
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=kwargs.get("partial", False)
            )

            if serializer.is_valid():
                serializer.save(updated_by=request.user)
                return Response(
                    {
                        "success": True,
                        "message": "Job updated successfully",
                        "data": serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )

            return Response(
                {
                    "success": False,
                    "message": "Validation failed",
                    "data": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Job.DoesNotExist:
            return Response(
                {"success": False, "message": "Job not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error updating job: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return Response(
                    {
                        "success": False,
                        "message": "Authentication required",
                        "data": {},
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            obj = self.get_object()
            obj.deleted = True
            obj.deleted_by = request.user
            obj.deleted_at = now()
            obj.save()

            return Response(
                {"success": True, "message": "Job deleted successfully", "data": {}},
                status=status.HTTP_200_OK,
            )
        except Job.DoesNotExist:
            return Response(
                {"success": False, "message": "Job not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error deleting job: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class JobSkillViewSet(viewsets.ModelViewSet):
    serializer_class = JobSkillSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = JobFilters
    search_fields = ["level_choices", "job__title", "skill__name"]
    ordering_fields = ["created_at", "level_choices", "job__title", "skill__name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return JobSkill.objects.filter(deleted=False).select_related("job", "skill")

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(
                    {
                        "success": True,
                        "message": "Job skills retrieved successfully",
                        "data": serializer.data,
                    }
                )

            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {
                    "success": True,
                    "message": "Job skills retrieved successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error retrieving job skills: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(
                {
                    "success": True,
                    "message": "Job skill retrieved successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except JobSkill.DoesNotExist:
            return Response(
                {"success": False, "message": "Job skill not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error retrieving job skill: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def create(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return Response(
                    {
                        "success": False,
                        "message": "Authentication required",
                        "data": {},
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                serializer.save(updated_by=request.user)
                return Response(
                    {
                        "success": True,
                        "message": "Job skill created successfully",
                        "data": serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )

            return Response(
                {
                    "success": False,
                    "message": "Validation failed",
                    "data": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error creating job skill: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def update(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return Response(
                    {
                        "success": False,
                        "message": "Authentication required",
                        "data": {},
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=kwargs.get("partial", False)
            )

            if serializer.is_valid():
                serializer.save(updated_by=request.user)
                return Response(
                    {
                        "success": True,
                        "message": "Job skill updated successfully",
                        "data": serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )

            return Response(
                {
                    "success": False,
                    "message": "Validation failed",
                    "data": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except JobSkill.DoesNotExist:
            return Response(
                {"success": False, "message": "Job skill not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error updating job skill: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return Response(
                    {
                        "success": False,
                        "message": "Authentication required",
                        "data": {},
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            obj = self.get_object()
            obj.deleted = True
            obj.deleted_by = request.user
            obj.deleted_at = now()
            obj.save()

            return Response(
                {
                    "success": True,
                    "message": "Job skill deleted successfully",
                    "data": {},
                },
                status=status.HTTP_200_OK,
            )
        except JobSkill.DoesNotExist:
            return Response(
                {"success": False, "message": "Job skill not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error deleting job skill: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class JobPreferenceViewSet(viewsets.ModelViewSet):
    serializer_class = JobPreferenceSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = JobFilters
    search_fields = [
        "preferred_industries",
        "soft_skills__name",
        "education_requirement",
        "job__title",
    ]
    ordering_fields = [
        "created_at",
        "preferred_industries",
        "soft_skills__name",
        "education_requirement",
        "job__title",
    ]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            JobPreference.objects.filter(deleted=False)
            .select_related("job")
            .prefetch_related("soft_skills")
        )

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(
                    {
                        "success": True,
                        "message": "Job preferences retrieved successfully",
                        "data": serializer.data,
                    }
                )

            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {
                    "success": True,
                    "message": "Job preferences retrieved successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error retrieving job preferences: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(
                {
                    "success": True,
                    "message": "Job preference retrieved successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except JobPreference.DoesNotExist:
            return Response(
                {"success": False, "message": "Job preference not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error retrieving job preference: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def create(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return Response(
                    {
                        "success": False,
                        "message": "Authentication required",
                        "data": {},
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                serializer.save(updated_by=request.user)
                return Response(
                    {
                        "success": True,
                        "message": "Job preference created successfully",
                        "data": serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )

            return Response(
                {
                    "success": False,
                    "message": "Validation failed",
                    "data": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error creating job preference: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def update(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return Response(
                    {
                        "success": False,
                        "message": "Authentication required",
                        "data": {},
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=kwargs.get("partial", False)
            )

            if serializer.is_valid():
                serializer.save(updated_by=request.user)
                return Response(
                    {
                        "success": True,
                        "message": "Job preference updated successfully",
                        "data": serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )

            return Response(
                {
                    "success": False,
                    "message": "Validation failed",
                    "data": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except JobPreference.DoesNotExist:
            return Response(
                {"success": False, "message": "Job preference not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error updating job preference: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return Response(
                    {
                        "success": False,
                        "message": "Authentication required",
                        "data": {},
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            obj = self.get_object()
            obj.deleted = True
            obj.deleted_by = request.user
            obj.deleted_at = now()
            obj.save()

            return Response(
                {
                    "success": True,
                    "message": "Job preference deleted successfully",
                    "data": {},
                },
                status=status.HTTP_200_OK,
            )
        except JobPreference.DoesNotExist:
            return Response(
                {"success": False, "message": "Job preference not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error deleting job preference: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class JobApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = JobApplicationSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = JobFilters
    search_fields = [
        "status",
        "job__title",
        "profile__headline",
        "profile__user__first_name",
        "profile__user__last_name",
    ]
    ordering_fields = [
        "created_at",
        "status",
        "job__title",
        "profile__headline",
        "profile__user__first_name",
        "profile__user__last_name",
    ]
    ordering = ["-created_at"]

    def get_queryset(self):
        return JobApplication.objects.filter(
            deleted=False, user=self.request.user
        ).select_related("job", "profile")

    def list(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return Response(
                    {
                        "success": False,
                        "message": "Authentication required",
                        "data": {},
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(
                    {
                        "success": True,
                        "message": "Job applications retrieved successfully",
                        "data": serializer.data,
                    }
                )

            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {
                    "success": True,
                    "message": "Job applications retrieved successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error retrieving job applications: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def retrieve(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return Response(
                    {
                        "success": False,
                        "message": "Authentication required",
                        "data": {},
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(
                {
                    "success": True,
                    "message": "Job application retrieved successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except JobApplication.DoesNotExist:
            return Response(
                {"success": False, "message": "Job application not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error retrieving job application: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def create(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return Response(
                    {
                        "success": False,
                        "message": "Authentication required",
                        "data": {},
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                serializer.save(user=request.user, updated_by=request.user)
                return Response(
                    {
                        "success": True,
                        "message": "Job application created successfully",
                        "data": serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )

            return Response(
                {
                    "success": False,
                    "message": "Validation failed",
                    "data": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error creating job application: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def update(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return Response(
                    {
                        "success": False,
                        "message": "Authentication required",
                        "data": {},
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=kwargs.get("partial", False)
            )

            if serializer.is_valid():
                serializer.save(updated_by=request.user)
                return Response(
                    {
                        "success": True,
                        "message": "Job application updated successfully",
                        "data": serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )

            return Response(
                {
                    "success": False,
                    "message": "Validation failed",
                    "data": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except JobApplication.DoesNotExist:
            return Response(
                {"success": False, "message": "Job application not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error updating job application: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return Response(
                    {
                        "success": False,
                        "message": "Authentication required",
                        "data": {},
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            obj = self.get_object()
            obj.deleted = True
            obj.deleted_by = request.user
            obj.deleted_at = now()
            obj.save()

            return Response(
                {
                    "success": True,
                    "message": "Job application deleted successfully",
                    "data": {},
                },
                status=status.HTTP_200_OK,
            )
        except JobApplication.DoesNotExist:
            return Response(
                {"success": False, "message": "Job application not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error deleting job application: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SavedJobViewSet(viewsets.ModelViewSet):
    serializer_class = SavedJobSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = JobFilters
    search_fields = [
        "job__title",
        "job__company_name",
        "job__description",
        "job__location",
        "job__employeement_type",
        "job__work_mode",
    ]
    ordering_fields = [
        "created_at",
        "job__title",
        "job__company_name",
        "job__description",
        "job__location",
        "job__employeement_type",
        "job__work_mode",
    ]
    ordering = ["-created_at"]

    def get_queryset(self):
        return SavedJob.objects.filter(
            deleted=False, user=self.request.user
        ).select_related("job")

    def list(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return Response(
                    {
                        "success": False,
                        "message": "Authentication required",
                        "data": {},
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(
                    {
                        "success": True,
                        "message": "Saved jobs retrieved successfully",
                        "data": serializer.data,
                    }
                )

            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {
                    "success": True,
                    "message": "Saved jobs retrieved successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error retrieving saved jobs: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def retrieve(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return Response(
                    {
                        "success": False,
                        "message": "Authentication required",
                        "data": {},
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(
                {
                    "success": True,
                    "message": "Saved job retrieved successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except SavedJob.DoesNotExist:
            return Response(
                {"success": False, "message": "Saved job not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error retrieving saved job: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def create(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return Response(
                    {
                        "success": False,
                        "message": "Authentication required",
                        "data": {},
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                serializer.save(user=request.user, updated_by=request.user)
                return Response(
                    {
                        "success": True,
                        "message": "Job saved successfully",
                        "data": serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )

            return Response(
                {
                    "success": False,
                    "message": "Validation failed",
                    "data": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error saving job: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def update(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return Response(
                    {
                        "success": False,
                        "message": "Authentication required",
                        "data": {},
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=kwargs.get("partial", False)
            )

            if serializer.is_valid():
                serializer.save(updated_by=request.user)
                return Response(
                    {
                        "success": True,
                        "message": "Saved job updated successfully",
                        "data": serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )

            return Response(
                {
                    "success": False,
                    "message": "Validation failed",
                    "data": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except SavedJob.DoesNotExist:
            return Response(
                {"success": False, "message": "Saved job not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error updating saved job: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                return Response(
                    {
                        "success": False,
                        "message": "Authentication required",
                        "data": {},
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            obj = self.get_object()
            obj.deleted = True
            obj.deleted_by = request.user
            obj.deleted_at = now()
            obj.save()

            return Response(
                {
                    "success": True,
                    "message": "Saved job deleted successfully",
                    "data": {},
                },
                status=status.HTTP_200_OK,
            )
        except SavedJob.DoesNotExist:
            return Response(
                {"success": False, "message": "Saved job not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error deleting saved job: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
