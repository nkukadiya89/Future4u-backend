"""
Resume Builder Django views.

Endpoints:
  POST /api/resume/generate/
    - Reads the logged-in user's profile (StudentProfile or ProfessionalProfile)
    - Accepts optional `template` query param: standard | professional (default: professional)
    - Accepts optional `photo` file upload
    - Returns a PDF file download

  GET /api/resume/preview/
    - Returns the resume data as JSON (useful for frontend preview / debugging)
"""

from __future__ import annotations

import logging
import tempfile
import os

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.http import HttpResponse
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from activity_log.services import log_event
from resume_builder.services import (
    build_student_resume_data,
    build_professional_resume_data,
    build_child_resume_data,
    generate_resume_pdf,
)

logger = logging.getLogger(__name__)


def _get_profile(user, child_id=None):
    """
    Return (profile, resume_type) for the logged-in user.
    Supports student, working_professional, and parent (via child_id).
    """
    from user_profile.models import StudentProfile, ProfessionalProfile, ChildProfile, ParentProfile

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


class ResumeGenerateView(APIView):
    """
    POST /api/resume/generate/

    Generates and returns a PDF resume for the logged-in user.

    Query params:
      - template: standard | professional  (default: professional)

    Form data (optional):
      - photo: image file (jpg/png)
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, *args, **kwargs):
        user = request.user
        template = request.query_params.get("template", "professional").strip()
        if template not in ("standard", "professional"):
            return Response(
                {
                    "success": False,
                    "message": "template must be 'standard' or 'professional'",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        child_id = request.query_params.get("child_id")
        profile, resume_type = _get_profile(user, child_id=child_id)
        if profile is None and resume_type is None:
            return Response(
                {
                    "success": False,
                    "message": "Resume generation is only available for Student, Professional, and Parent users.",
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

        # Build resume data dict from profile
        if resume_type == "fresher":
            resume_data = build_student_resume_data(profile, user, template=template)
        elif resume_type == "child":
            resume_data = build_child_resume_data(profile, template=template)
        else:
            resume_data = build_professional_resume_data(
                profile, user, template=template
            )

        # Handle optional photo upload
        tmp_photo_path = None
        photo = request.FILES.get("photo")
        if photo:
            suffix = os.path.splitext(photo.name)[-1] or ".jpg"
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            try:
                for chunk in photo.chunks():
                    tmp.write(chunk)
                tmp.flush()
                tmp_photo_path = tmp.name
            finally:
                tmp.close()
            resume_data["personal_info"]["photo"] = tmp_photo_path

        try:
            pdf_bytes = generate_resume_pdf(resume_data)
        except ValueError as exc:
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
            msg = str(exc)
            if "insufficient_quota" in msg or "429" in msg:
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
            return Response(
                {
                    "success": False,
                    "message": "Failed to generate resume. Please try again.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        finally:
            if tmp_photo_path and os.path.exists(tmp_photo_path):
                os.unlink(tmp_photo_path)

        if resume_type == "child":
            child_name = f"{profile.first_name} {profile.last_name}".strip()
            name = child_name.replace(" ", "_") if child_name else "child_resume"
        else:
            name = (user.full_name or user.email).replace(" ", "_")
        filename = f"{name}_resume.pdf"
        logger.info("Resume generated for user=%s template=%s", user.id, template)

        log_event(
            event="ai.resume_generated",
            description=f"AI resume generated for user {user.email}, template={template}",
            user=user,
            entity_type="resume",
            entity_id=user.id,
            request=request,
        )

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f"attachment; filename={filename}"
        return response


class ResumePreviewView(APIView):
    """
    GET /api/resume/preview/

    Returns the resume data as JSON — useful for frontend preview or debugging.
    Does NOT call AI or generate PDF.

    Query params:
      - template: standard | professional  (default: professional)
    """

    permission_classes = [IsAuthenticated]
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
                    "message": "Resume preview is only available for Student, Professional, and Parent users.",
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
