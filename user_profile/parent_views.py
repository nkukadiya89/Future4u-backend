from django.db import DatabaseError, IntegrityError
from django.utils.timezone import now
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.filters import SearchFilter
from rest_framework.response import Response

from common.mixins.view_mixins import PartialUpdateFromUpdateMixin, SaveUpdatedByMixin
from user_profile.filters import ProfileFilter
from user_profile.models import ParentProfile
from user_profile.parent_serializers import ParentProfileSerializer


class ParentProfileViewSet(
    PartialUpdateFromUpdateMixin, SaveUpdatedByMixin, viewsets.ModelViewSet
):
    serializer_class = ParentProfileSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = ProfileFilter
    search_fields = ["title", "city", "country"]
    ordering_fields = ["created_at", "title"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            ParentProfile.objects.filter(deleted=False, profile__user=self.request.user)
            .select_related("profile", "updated_by")
            .prefetch_related("child_interests")  # only if you switch to M2M
        )

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                paginated_response = self.get_paginated_response(serializer.data)
                return Response(
                    {
                        "success": True,
                        "message": "Parent profiles retrieved successfully",
                        "data": paginated_response.data,
                    },
                    status=status.HTTP_200_OK,
                )

            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {
                    "success": True,
                    "message": "Parent profiles retrieved successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except DatabaseError:
            return Response(
                {"success": False, "message": "Database error occurred", "data": {}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception:
            return Response(
                {
                    "success": False,
                    "message": "An unexpected error occurred",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                self.perform_create(serializer)
                return Response(
                    {
                        "success": True,
                        "message": "Parent profile created successfully",
                        "data": serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {
                        "success": False,
                        "message": "Validation failed",
                        "data": serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except IntegrityError:
            return Response(
                {"success": False, "message": "Data integrity error", "data": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except DatabaseError:
            return Response(
                {"success": False, "message": "Database error occurred", "data": {}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception:
            return Response(
                {
                    "success": False,
                    "message": "An unexpected error occurred",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except ParentProfile.DoesNotExist:
            return Response(
                {"success": False, "message": "Parent profile not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception:
            return Response(
                {
                    "success": False,
                    "message": "An unexpected error occurred",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            serializer = self.get_serializer(instance)
            return Response(
                {
                    "success": True,
                    "message": "Parent profile retrieved successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception:
            return Response(
                {
                    "success": False,
                    "message": "An unexpected error occurred",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop("partial", False)
            instance = self.get_object()
        except ParentProfile.DoesNotExist:
            return Response(
                {"success": False, "message": "Parent profile not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception:
            return Response(
                {
                    "success": False,
                    "message": "An unexpected error occurred",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            if serializer.is_valid():
                self.perform_update(serializer)
                return Response(
                    {
                        "success": True,
                        "message": "Parent profile updated successfully",
                        "data": serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {
                        "success": False,
                        "message": "Validation failed",
                        "data": serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except IntegrityError:
            return Response(
                {"success": False, "message": "Data integrity error", "data": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except DatabaseError:
            return Response(
                {"success": False, "message": "Database error occurred", "data": {}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception:
            return Response(
                {
                    "success": False,
                    "message": "An unexpected error occurred",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except ParentProfile.DoesNotExist:
            return Response(
                {"success": False, "message": "Parent profile not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception:
            return Response(
                {
                    "success": False,
                    "message": "An unexpected error occurred",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            instance.deleted = True
            instance.deleted_by = request.user
            instance.deleted_at = now()
            instance.save()

            return Response(
                {
                    "success": True,
                    "message": "Parent profile deleted successfully",
                    "data": {},
                },
                status=status.HTTP_200_OK,
            )
        except DatabaseError:
            return Response(
                {"success": False, "message": "Database error occurred", "data": {}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception:
            return Response(
                {
                    "success": False,
                    "message": "An unexpected error occurred",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
