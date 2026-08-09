from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from common.master_view import BaseModelViewSet


class BaseLeadNoteViewSet(BaseModelViewSet):

    lead_model = None
    lead_id_url_param = ""
    note_lead_field = ""
    provider_user_types = []
    lead_provider_field_path = ""
    audit_event_prefix = ""
    lead_display_name = ""
    lead_log_label = ""

    def _resolve_lead_provider(self, lead):
        """Return the provider user of a lead, or None (handles nullable relations)."""
        obj = lead
        for part in self.lead_provider_field_path.split("."):
            obj = getattr(obj, part, None)
            if obj is None:
                return None
        return obj

    def _get_accessible_lead(self):
        """Return the lead from the URL if the current user may add notes to it, else None."""
        lead = self.lead_model.objects.filter(
            id=self.kwargs.get(self.lead_id_url_param),
            deleted=False,
        ).first()
        if not lead:
            return None
        user = self.request.user
        if user.is_superuser:
            return lead
        if user.user_type in self.provider_user_types:
            if self._resolve_lead_provider(lead) == user:
                return lead
        return None

    def _not_found_response(self):
        return Response(
            {
                "success": False,
                "message": (
                    f"Invalid {self.lead_display_name} ID. "
                    f"Please provide a valid {self.lead_log_label}."
                ),
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    def _forbidden_response(self, action):
        return Response(
            {
                "success": False,
                "message": f"You are not allowed to {action} this note.",
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    def _lead_id_of(self, instance):
        """Return the lead id of a note instance (e.g. instance.inquiry_id)."""
        return getattr(instance, f"{self.note_lead_field}_id")

    def _log_note_event(self, action, description, lead_id, note_id=None):
        from activity_log.services import log_event

        log_event(
            event=f"{self.audit_event_prefix}.{action}",
            description=description,
            user=self.request.user,
            entity_type=self.audit_event_prefix,
            entity_id=note_id,
            metadata={f"{self.note_lead_field}_id": lead_id},
            request=self.request,
        )

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related(self.note_lead_field, "created_by")
            .filter(**{f"{self.note_lead_field}__deleted": False})
        )
        user = self.request.user
        if not user.is_superuser:
            if user.user_type in self.provider_user_types:
                provider_lookup = (
                    f"{self.note_lead_field}__"
                    f"{self.lead_provider_field_path.replace('.', '__')}"
                )
                queryset = queryset.filter(**{provider_lookup: user})
            else:
                queryset = queryset.none()
        lead_id = self.kwargs.get(self.lead_id_url_param)
        if lead_id:
            queryset = queryset.filter(**{f"{self.note_lead_field}_id": lead_id})
        return queryset.order_by("-created_at")

    def list(self, request, *args, **kwargs):
        if not self.lead_model.objects.filter(
            id=self.kwargs.get(self.lead_id_url_param), deleted=False
        ).exists():
            return self._not_found_response()
        return super().list(request, *args, **kwargs)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        lead = self._get_accessible_lead()
        if not lead:
            return self._not_found_response()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            **{self.note_lead_field: lead},
            created_by=request.user,
        )
        self._log_note_event(
            "created",
            f"Added note to {self.lead_log_label} #{lead.id}",
            lead.id,
            serializer.instance.id if serializer.instance else None,
        )
        return Response(
            {
                "success": True,
                "message": "Note added successfully",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        if instance.created_by != request.user and not request.user.is_superuser:
            return self._forbidden_response("update")

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user, updated_at=timezone.now())
        self._log_note_event(
            "updated",
            f"Updated note on {self.lead_log_label} #{self._lead_id_of(instance)}",
            self._lead_id_of(instance),
            instance.id,
        )
        return Response(
            {
                "success": True,
                "message": "Note updated successfully",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.deleted:
            return Response(
                {"success": False, "message": "Already archived"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if instance.created_by != request.user and not request.user.is_superuser:
            return self._forbidden_response("delete")

        instance.deleted = True
        instance.deleted_by = request.user
        instance.deleted_at = timezone.now()
        instance.save()
        self._log_note_event(
            "deleted",
            f"Deleted note on {self.lead_log_label} #{self._lead_id_of(instance)}",
            self._lead_id_of(instance),
            instance.id,
        )
        return Response(
            {
                "success": True,
                "message": "Note deleted successfully",
            },
            status=status.HTTP_200_OK,
        )
