from rest_framework.viewsets import ModelViewSet
from rest_framework.filters import OrderingFilter
from utils.custom_filters import CustomSearchFilter
from utils.generate_ip_address import get_client_ip
from utils.pagination import Pagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication


class BaseModelViewSet(ModelViewSet):
    filter_backends = [CustomSearchFilter,OrderingFilter]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    list_serializer_class = None

    searching_fields = [
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
        "created_by__full_name",
        "updated_by__full_name",
    ]
    
    ordering_fields = [
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
    ]


    def get_serializer_class(self):
        if self.action == "list" and self.list_serializer_class:
            return self.list_serializer_class
        return super().get_serializer_class()
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.get_serializer(queryset,many=True)
            return Response({"success":True, "data":serializer.data})
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"success":True, "data":serializer.data})
        
        serializer = self.get_serializer(queryset,many=True)
        return self.get_paginated_response({"success":True, "data":serializer.data})
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action not in [
        "archive_list",
        "archive",
        "restore",
        "bulk_archive",
        "bulk_restore", 
        "destroy",                      
        ]:
            queryset = queryset.filter(deleted=False).order_by("-id")
        return queryset
    
    def log_action(self, request, instance, action):
        from activity_log.models import ActivityLog

        ip_address = get_client_ip(request)
        model_name = instance.__class__.__name__.lower()

        method_name = f"{model_name}_{action.lower()}"

        if hasattr(ActivityLog.log, method_name):
            getattr(ActivityLog.log, method_name)(
                instance, ip_address=ip_address, user=request.user
            )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            instance = serializer.save(
                created_by = request.user,
                created_at = timezone.now(),
            )
            self.log_action(request,instance, "CREATE")
            return Response({"success":True, "data":serializer.data},status=status.HTTP_201_CREATED)
        return Response({"success":False,"message":serializer.errors},status=status.HTTP_400_BAD_REQUEST)
    
    def update(self,request,*args,**kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance,data=request.data, partial=True)
        if serializer.is_valid():
            instance = serializer.save(
                updated_by=request.user,
                updated_at = timezone.now(),
            )
            self.log_action(request,instance,"UPDATE")
            return Response({"success":True, "data":serializer.data},status=status.HTTP_200_OK)
        return Response({"success":False,"message":serializer.errors},status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if getattr(instance, "deleted",False):
            return Response({"success":False, "message":"Already Archived"},status=status.HTTP_400_BAD_REQUEST)
        instance.deleted=True
        instance.deleted_at = timezone.now()

        if hasattr(instance, "deleted_by"):
            instance.deleted_by = request.user
        instance.save()

        if hasattr(self, "log_archive_action"):
            self.log_archive_action(request, instance=instance, action="ARCHIVE")
        return Response({"success":True, "message":"Record Archived Successfully"},status=status.HTTP_200_OK)
        
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        if getattr(instance, "deleted", False):
            return Response(
                {"success": False, "message": "Record not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(instance)

        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )