# Create your views here.
from django.utils.timezone import now
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from .filters import CourseFilter
from .models import Course
from .serializers import CourseSerializer


class CourseViewSet(viewsets.ModelViewSet):
    serializer_class = CourseSerializer

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CourseFilter
    search_fields = ["title", "provider_name"]
    ordering_fields = ["price", "created_at"]

    def get_queryset(self):
        return (
            Course.objects.filter(deleted=False)
            .prefetch_related("domains", "skills")
            .select_related("updated_by")
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
                        "message": "Courses retrieved successfully",
                        "data": serializer.data,
                    }
                )

            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {
                    "success": True,
                    "message": "Courses retrieved successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error retrieving courses: {str(e)}",
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
                    "message": "Course retrieved successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Course.DoesNotExist:
            return Response(
                {"success": False, "message": "Course not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error retrieving course: {str(e)}",
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
                        "message": "Course created successfully",
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
                    "message": f"Error creating course: {str(e)}",
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
                        "message": "Course updated successfully",
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
        except Course.DoesNotExist:
            return Response(
                {"success": False, "message": "Course not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error updating course: {str(e)}",
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
                {"success": True, "message": "Course deleted successfully", "data": {}},
                status=status.HTTP_200_OK,
            )
        except Course.DoesNotExist:
            return Response(
                {"success": False, "message": "Course not found", "data": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error deleting course: {str(e)}",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
