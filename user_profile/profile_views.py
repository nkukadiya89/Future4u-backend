from django.db import DatabaseError, IntegrityError
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views.decorators.cache import cache_page
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.filters import SearchFilter
from rest_framework.response import Response

from user_profile.filters import ProfileFilter
from user_profile.models import Profile
from user_profile.serializers import ProfileSerializer


@method_decorator(cache_page(60 * 2), name="list")
class ProfileViewSet(viewsets.ModelViewSet):
    serializer_class = ProfileSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = ProfileFilter
    search_fields = ["title", "city", "country"]
    ordering_fields = ["created_at", "title"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Profile.objects.filter(deleted=False)

    def list(self, request, *args, **kwargs):
        """
        List all profiles with pagination and filtering
        """
        try:
            queryset = self.filter_queryset(self.get_queryset())

            if not queryset.exists():
                return Response(
                    {"success": True, "message": "No profiles found", "data": []},
                    status=status.HTTP_200_OK,
                )

            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                paginated_response = self.get_paginated_response(serializer.data)
                return Response(
                    {
                        "success": True,
                        "message": "Profiles retrieved successfully",
                        "data": paginated_response.data,
                    },
                    status=status.HTTP_200_OK,
                )

            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {
                    "success": True,
                    "message": "Profiles retrieved successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except DatabaseError:
            return Response(
                {"success": False, "message": "Database error occurred", "data": {}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"An unexpected error occurred: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def create(self, request, *args, **kwargs):
        """
        Create a new profile
        """
        try:
            # Check if user is authenticated
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
            if not serializer.is_valid():
                return Response(
                    {
                        "success": False,
                        "message": "Validation failed",
                        "data": serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            self.perform_create(serializer)
            return Response(
                {
                    "success": True,
                    "message": "Profile created successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        except IntegrityError:
            return Response(
                {
                    "success": False,
                    "message": "Profile with this data already exists",
                    "data": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except DatabaseError:
            return Response(
                {"success": False, "message": "Database error occurred", "data": {}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"An unexpected error occurred: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a single profile by ID
        """
        try:
            instance = self.get_object()
            if instance.deleted:
                return Response(
                    {"success": False, "message": "Profile not found", "data": {}},
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = self.get_serializer(instance)
            return Response(
                {
                    "success": True,
                    "message": "Profile retrieved successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except Profile.DoesNotExist:
            return Response(
                {"success": False, "message": "Profile not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"An unexpected error occurred: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def update(self, request, *args, **kwargs):
        """
        Update a profile completely
        """
        try:
            # Check if user is authenticated
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
            if instance.deleted:
                return Response(
                    {"success": False, "message": "Profile not found", "data": {}},
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = self.get_serializer(instance, data=request.data)
            if not serializer.is_valid():
                return Response(
                    {
                        "success": False,
                        "message": "Validation failed",
                        "data": serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            self.perform_update(serializer)
            return Response(
                {
                    "success": True,
                    "message": "Profile updated successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except Profile.DoesNotExist:
            return Response(
                {"success": False, "message": "Profile not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except IntegrityError:
            return Response(
                {
                    "success": False,
                    "message": "Profile with this data already exists",
                    "data": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except DatabaseError:
            return Response(
                {"success": False, "message": "Database error occurred", "data": {}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"An unexpected error occurred: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def partial_update(self, request, *args, **kwargs):
        """
        Partially update a profile
        """
        try:
            # Check if user is authenticated
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
            if instance.deleted:
                return Response(
                    {"success": False, "message": "Profile not found", "data": {}},
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = self.get_serializer(instance, data=request.data, partial=True)
            if not serializer.is_valid():
                return Response(
                    {
                        "success": False,
                        "message": "Validation failed",
                        "data": serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            self.perform_update(serializer)
            return Response(
                {
                    "success": True,
                    "message": "Profile updated successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except Profile.DoesNotExist:
            return Response(
                {"success": False, "message": "Profile not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except IntegrityError:
            return Response(
                {
                    "success": False,
                    "message": "Profile with this data already exists",
                    "data": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except DatabaseError:
            return Response(
                {"success": False, "message": "Database error occurred", "data": {}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"An unexpected error occurred: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """
        Soft delete instead of hard delete
        """
        try:
            # Check if user is authenticated
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
            if instance.deleted:
                return Response(
                    {"success": False, "message": "Profile not found", "data": {}},
                    status=status.HTTP_404_NOT_FOUND,
                )

            instance.deleted = True
            instance.deleted_by = request.user
            instance.deleted_at = now()
            instance.save()

            return Response(
                {
                    "success": True,
                    "message": "Profile deleted successfully",
                    "data": {},
                },
                status=status.HTTP_200_OK,
            )

        except Profile.DoesNotExist:
            return Response(
                {"success": False, "message": "Profile not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except DatabaseError:
            return Response(
                {"success": False, "message": "Database error occurred", "data": {}},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"An unexpected error occurred: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
