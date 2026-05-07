from django.utils.timezone import now
from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import ProfileCoursePreference
from .serializers import ProfileCoursePreferenceSerializer


class ProfileCoursePreferenceViewSet(viewsets.ModelViewSet):
    serializer_class = ProfileCoursePreferenceSerializer

    def get_queryset(self):
        return (
            ProfileCoursePreference.objects.filter(
                deleted=False, profile__user=self.request.user
            )
            .select_related("profile")
            .prefetch_related("preferred_domains", "preferred_skills")
        )

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
                        "message": "Profile course preferences retrieved successfully",
                        "data": serializer.data,
                    }
                )

            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {
                    "success": True,
                    "message": "Profile course preferences retrieved successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error retrieving profile course preferences: {str(e)}",
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
                    "message": "Profile course preference retrieved successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except ProfileCoursePreference.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Profile course preference not found",
                    "data": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error retrieving profile course preference: {str(e)}",
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
                        "message": "Profile course preference created successfully",
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
                    "message": f"Error creating profile course preference: {str(e)}",
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
                        "message": "Profile course preference updated successfully",
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
        except ProfileCoursePreference.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Profile course preference not found",
                    "data": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error updating profile course preference: {str(e)}",
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
                    "message": "Profile course preference deleted successfully",
                    "data": {},
                },
                status=status.HTTP_200_OK,
            )
        except ProfileCoursePreference.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Profile course preference not found",
                    "data": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error deleting profile course preference: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
