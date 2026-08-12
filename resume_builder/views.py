"""Resume Builder Django views — Path B (JSON Resume backend).

Endpoints:
  GET  /api/resume/templates/        — active template registry (no AI)
  POST /api/resume/generate/         — full AI pipeline → stored GeneratedResume
                                        → canonical JSON Resume (no PDF)
  GET  /api/resume/                  — current user's resume history (paginated)
  GET  /api/resume/{resume_id}/      — stored canonical JSON Resume (ownership enforced)
  POST /api/resume/{resume_id}/pdf/  — render a stored resume to PDF (no AI, no tokens)
  GET  /api/resume/preview/          — raw resume source data as JSON (no AI)
"""

from __future__ import annotations

import logging

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from resume_builder.models import GeneratedResume, ResumeTemplate
from resume_builder.resume_services.generator import build_resume
from resume_builder.resume_services.json_resume import resume_json_to_template_data
from resume_builder.serializers import (
    GeneratedResumeDetailSerializer,
    GeneratedResumeListSerializer,
    ResumeTemplateSerializer,
)
from resume_builder.services import (
    ResumeEditError,
    ResumeTokenError,
    ResumeValidationError,
    apply_resume_edits,
    build_child_resume_data,
    build_professional_resume_data,
    build_student_resume_data,
    generate_resume_json,
)
from user.permissions import IsIndividualUser
from utils.pagination import Pagination

logger = logging.getLogger(__name__)


def _get_profile(user, child_id=None):
    """
    Return (profile, resume_type) for the logged-in user.
    Supports student, working_professional, and parent (via child_id).
    """
    from user_profile.models import (
        ChildProfile,
        ParentProfile,
        ProfessionalProfile,
        StudentProfile,
    )

    role = getattr(user, "user_type", None)

    if child_id and role == user.Role.PARENT:
        try:
            child = (
                ChildProfile.objects.select_related("education_level", "stream")
                .prefetch_related("language")
                .get(id=child_id, parent_profile__user=user, deleted=False)
            )
            return child, "child"
        except ChildProfile.DoesNotExist:
            return None, "child"

    if role == user.Role.STUDENT:
        try:
            return (
                StudentProfile.objects.select_related(
                    "education_level",
                    "stream",
                    "user__country",
                    "user__states",
                    "user__city",
                )
                .prefetch_related("language")
                .get(user=user),
                "fresher",
            )
        except StudentProfile.DoesNotExist:
            return None, "fresher"

    if role == user.Role.PROFESSIONAL:
        try:
            return (
                ProfessionalProfile.objects.select_related(
                    "education_level", "user__country", "user__states", "user__city"
                )
                .prefetch_related("language")
                .get(user=user),
                "professional",
            )
        except ProfessionalProfile.DoesNotExist:
            return None, "professional"

    return None, None


class ResumeTemplatesView(APIView):
    """GET /api/resume/templates/ — active template registry metadata."""

    permission_classes = [IsAuthenticated, IsIndividualUser]
    authentication_classes = [JWTAuthentication]

    def get(self, request, *args, **kwargs):
        queryset = (
            ResumeTemplate.objects.filter(is_active=True, deleted=False)
            .order_by("sort_order", "code")
        )
        return Response(
            {"success": True, "data": ResumeTemplateSerializer(queryset, many=True).data},
            status=status.HTTP_200_OK,
        )


class ResumeGenerateView(APIView):
    """
    POST /api/resume/generate/

    Runs the full AI pipeline, stores a GeneratedResume, and returns the
    canonical JSON Resume. Template selection never affects AI generation
    and never consumes extra tokens (template is presentation metadata).
    """

    permission_classes = [IsAuthenticated, IsIndividualUser]
    authentication_classes = [JWTAuthentication]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, *args, **kwargs):
        user = request.user
        template = str(
            request.data.get("template")
            or request.query_params.get("template")
            or "professional"
        ).strip()

        valid_templates = list(
            ResumeTemplate.objects.filter(is_active=True, deleted=False)
            .order_by("sort_order", "code")
            .values_list("code", flat=True)
        )
        if template not in valid_templates:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Invalid template. Choose from: "
                        f"{', '.join(valid_templates) or 'none'}."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        child_id = request.data.get("child_id") or request.query_params.get("child_id")
        profile, resume_type = _get_profile(user, child_id=child_id)
        if profile is None and resume_type is None:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Resume generation is only available for Student, "
                        "Professional, and Parent users."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if profile is None:
            return Response(
                {
                    "success": False,
                    "message": "Profile not found. Please complete your profile first.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            record = generate_resume_json(
                profile,
                user,
                resume_type,
                template=template,
                request=request,
            )
        except ResumeTokenError as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )
        except ResumeValidationError as exc:
            logger.warning(
                "Resume validation failed user=%s resume_type=%s errors=%s",
                user.id,
                resume_type,
                exc,
            )
            return Response(
                {
                    "success": False,
                    "message": "Generated resume failed validation. Please try again.",
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except ValueError as exc:
            msg = str(exc)
            if "429" in msg or "insufficient_quota" in msg:
                return Response(
                    {
                        "success": False,
                        "message": "Resume AI is busy right now. Please try again shortly.",
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            if "401" in msg or "invalid_api_key" in msg:
                return Response(
                    {
                        "success": False,
                        "message": "Resume AI is temporarily unavailable.",
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            logger.error("Resume generation error: %s", exc)
            return Response(
                {
                    "success": False,
                    "message": "Unable to generate resume right now. Please try again.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as exc:
            logger.exception("Unexpected resume generation error")
            return Response(
                {
                    "success": False,
                    "message": "Failed to generate resume. Please try again.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(
            "Resume generated user=%s template=%s resume_id=%s",
            user.id,
            template,
            record.id,
        )
        return Response(
            {"success": True, "data": GeneratedResumeDetailSerializer(record).data},
            status=status.HTTP_200_OK,
        )


class ResumeHistoryView(APIView):
    """GET /api/resume/ — current user's generated resumes, newest first."""

    permission_classes = [IsAuthenticated, IsIndividualUser]
    authentication_classes = [JWTAuthentication]

    def get(self, request, *args, **kwargs):
        queryset = (
            GeneratedResume.objects.filter(user=request.user, deleted=False)
            .order_by("-created_at", "-id")
        )
        paginator = Pagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = GeneratedResumeListSerializer(page, many=True)
        return Response(
            {
                "success": True,
                "count": paginator.page.paginator.count,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class ResumeDetailView(APIView):
    """
    GET   /api/resume/{resume_id}/ — stored canonical JSON Resume.
    PATCH /api/resume/{resume_id}/ — edit the generated resume in place.

    PATCH semantics: only the sections present in the body change. List sections
    are replaced wholesale; basics is merged per key. No AI call, no token
    deduction — a pure database update of the stored resume_json.
    """

    permission_classes = [IsAuthenticated, IsIndividualUser]
    authentication_classes = [JWTAuthentication]

    def get(self, request, resume_id, *args, **kwargs):
        record = get_object_or_404(
            GeneratedResume,
            id=resume_id,
            user=request.user,
            deleted=False,
        )
        return Response(
            {"success": True, "data": GeneratedResumeDetailSerializer(record).data},
            status=status.HTTP_200_OK,
        )

    def patch(self, request, resume_id, *args, **kwargs):
        record = get_object_or_404(
            GeneratedResume,
            id=resume_id,
            user=request.user,
            deleted=False,
        )

        edits = request.data.get("resume")
        if not isinstance(edits, dict) or not edits:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Provide the sections to edit under the 'resume' key, e.g. "
                        '{"resume": {"basics": {"summary": "..."}}}'
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            merged = apply_resume_edits(record, edits)
        except ResumeEditError as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ResumeValidationError as exc:
            logger.warning(
                "Resume edit validation failed user=%s resume_id=%s errors=%s",
                request.user.id,
                resume_id,
                exc,
            )
            return Response(
                {
                    "success": False,
                    "message": "Edited resume failed validation. Please fix the highlighted fields.",
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        record.resume_json = merged
        record.save(update_fields=["resume_json"])

        logger.info(
            "Resume edited user=%s resume_id=%s", request.user.id, resume_id
        )
        return Response(
            {"success": True, "data": GeneratedResumeDetailSerializer(record).data},
            status=status.HTTP_200_OK,
        )


class ResumePDFView(APIView):
    """
    POST /api/resume/{resume_id}/pdf/

    Renders a stored resume into the legacy Jinja templates. NO Groq call,
    NO token deduction — a separate operation from AI generation.
    """

    permission_classes = [IsAuthenticated, IsIndividualUser]
    authentication_classes = [JWTAuthentication]

    def post(self, request, resume_id, *args, **kwargs):
        record = get_object_or_404(
            GeneratedResume,
            id=resume_id,
            user=request.user,
            deleted=False,
        )
        template_data = resume_json_to_template_data(
            record.resume_json, record.resume_type, record.template
        )
        summary = (record.resume_json.get("basics") or {}).get("summary") or ""
        pdf_bytes = build_resume(template_data, summary)

        name = (record.resume_json.get("basics") or {}).get("name") or "resume"
        filename = f"{name.replace(' ', '_')}_{record.template}_resume.pdf"
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class ResumePreviewView(APIView):
    """
    GET /api/resume/preview/

    Returns the resume data as JSON — useful for frontend preview or debugging.
    Does NOT call AI or generate PDF.
    """

    permission_classes = [IsAuthenticated, IsIndividualUser]
    authentication_classes = [JWTAuthentication]

    def get(self, request, *args, **kwargs):
        user = request.user
        template = request.query_params.get("template", "professional").strip()

        child_id = request.query_params.get("child_id")
        profile, resume_type = _get_profile(user, child_id=child_id)
        if profile is None and resume_type is None:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Resume preview is only available for Student, "
                        "Professional, and Parent users."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if profile is None:
            return Response(
                {
                    "success": False,
                    "message": "Profile not found. Please complete your profile first.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if resume_type == "fresher":
            resume_data = build_student_resume_data(profile, user, template=template)
        elif resume_type == "child":
            resume_data = build_child_resume_data(profile, template=template)
        else:
            resume_data = build_professional_resume_data(
                profile, user, template=template
            )

        return Response(
            {"success": True, "data": resume_data}, status=status.HTTP_200_OK
        )
