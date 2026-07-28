from rest_framework import status
from rest_framework.response import Response

from email_utils.send_email import send_mail


class ListEnvelopeMixin:
    """list with {success, data} envelope (shared by BaseModelViewSet)."""

    # When True, return a plain Response if pagination does not apply (LanguageViewSet).
    list_unpaginated_fallback = False

    def envelope_list_response(self, request, queryset):
        queryset = self.filter_queryset(queryset)
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.get_serializer(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = self.get_serializer(queryset, many=True)
        payload = {"success": True, "data": serializer.data}
        if self.list_unpaginated_fallback:
            return Response(payload)
        return self.get_paginated_response(payload)

    def list(self, request, *args, **kwargs):
        return self.envelope_list_response(request, self.get_queryset())


class SuccessEnvelopeMixin(ListEnvelopeMixin):
    """list / retrieve / update / partial_update with {success, data} envelope."""

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"success": True, "data": serializer.data})

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=False)
        if serializer.is_valid():
            serializer.save()
            return Response({"success": True, "data": serializer.data})
        return Response(
            {"success": False, "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"success": True, "data": serializer.data})
        return Response(
            {"success": False, "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


class MappingSuccessEnvelopeMixin(SuccessEnvelopeMixin):
    """Alias for mapping viewsets; same envelope as SuccessEnvelopeMixin."""


class PartialUpdateFromUpdateMixin:
    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)


class RetrieveSuccessEnvelopeMixin:
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )


class CreatePasswordEmailMixin:
    def send_email(self, user, context):
        if user:
            send_mail(
                "Future4U Security Alert For Create New Password",
                "reset-pass.html",
                context,
            )


class MethodNotAllowedListMixin:
    def list(self, request, *args, **kwargs):
        return Response(
            {"success": False, "message": "Method not allowed"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class SaveUpdatedByMixin:
    def perform_create(self, serializer):
        serializer.save(updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
