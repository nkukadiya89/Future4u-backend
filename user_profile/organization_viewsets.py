import json

from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication

from common.master_view import BaseModelViewSet
from utils.aws_file_upload import delete_uploaded_file


class OrganizationProfileViewSet(BaseModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    http_method_names = ["get", "patch", "head", "options"]

    profile_model = None
    read_serializer_class = None
    update_serializer_class = None

    def get_queryset(self):
        return self.profile_model.objects.filter(
            user=self.request.user,
            deleted=False,
        ).select_related("user", "user__city", "user__states").prefetch_related(
            "gallery_images"
        )

    def list(self, request, *args, **kwargs):
        profile = self.get_queryset().first()
        if not profile:
            return Response(
                {"success": False, "message": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {"success": True, "data": self.read_serializer_class(profile).data},
            status=status.HTTP_200_OK,
        )

    @transaction.atomic()
    def partial_update(self, request, *args, **kwargs):
        profile = self.get_queryset().first()
        if not profile:
            return Response(
                {"success": False, "message": "Profile not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = request.data.get("data")
        if data:
            data = json.loads(data)
        else:
            data = {}

        profile_image = request.FILES.get("profile_image")
        if profile_image:
            request.user.upload_profile_image(profile_image)

        serializer = self.update_serializer_class(
            profile, data=data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"success": True, "data": self.read_serializer_class(profile).data},
            status=status.HTTP_200_OK,
        )


class OrganizationGalleryViewSet(BaseModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    http_method_names = ["get", "post", "delete", "head", "options"]

    profile_model = None
    gallery_model = None
    profile_fk_field = None
    gallery_serializer_class = None
    profile_not_found_message = "Profile not found"

    def get_queryset(self):
        return self.gallery_model.objects.filter(
            **{f"{self.profile_fk_field}__user": self.request.user},
            deleted=False,
        )

    def list(self, request, *args, **kwargs):
        images = self.get_queryset()
        return Response(
            {
                "success": True,
                "data": self.gallery_serializer_class(images, many=True).data,
            },
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        profile = self.profile_model.objects.filter(user=request.user).first()
        if not profile:
            return Response(
                {"success": False, "message": self.profile_not_found_message},
                status=status.HTTP_404_NOT_FOUND,
            )

        images = request.FILES.getlist("images")
        if not images:
            return Response(
                {"success": False, "message": "Please Upload at least one image"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        current_count = profile.gallery_images.count()
        if current_count + len(images) > 10:
            return Response(
                {"success": False, "message": "Maximum 10 images allowed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        uploaded_images = []
        for image in images:
            gallery = self.gallery_model(**{self.profile_fk_field: profile})
            gallery.save(user=request.user)
            gallery.upload_gallery_image(image)
            uploaded_images.append(self.gallery_serializer_class(gallery).data)

        return Response(
            {
                "success": True,
                "message": "Images uploaded successfully",
                "data": uploaded_images,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        image = self.get_queryset().filter(id=kwargs.get("pk")).first()
        if not image:
            return Response(
                {"success": False, "message": "Image not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if image.image:
            delete_uploaded_file(image.image)
        image.delete()
        return Response(
            {"success": True, "message": "Image deleted successfully"},
            status=status.HTTP_200_OK,
        )
