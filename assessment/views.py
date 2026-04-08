from django.db import models, transaction
from django.db.models import Sum
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.core.cache import cache

from assessment.models import Option, Question, UserResponse
from assessment.serializers import (
    AssessmentSubmitSerializer,
    QuestionSerializer,
    UserResponseSerializer,
)


class QuestionViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Question.objects.filter(is_active=True).order_by("id")
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]


class UserResponseViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = UserResponse.objects.all().order_by("id")
    serializer_class = UserResponseSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]


class ApiAssessmentQuestionsViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    GET /api/assessment/questions/
    - Returns questions filtered to the logged-in user's education level.
    - For 12th-grade users, also filters by their selected stream (if set).
    - Groups questions by dimension.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = QuestionSerializer

    def _get_user_profile(self, user):
        from user_profile.models import UserProfile

        try:
            return UserProfile.objects.select_related("education_level", "stream").get(
                user=user
            )
        except UserProfile.DoesNotExist:
            return None

    def get_queryset(self):
        user = self.request.user
        profile = self._get_user_profile(user)
        edu_level = getattr(profile, "education_level", None) if profile else None
        user_stream = getattr(profile, "stream", None) if profile else None

        qs = (
            Question.objects.filter(is_active=True)
            .prefetch_related("options", "mapped_domains", "mapped_streams")
            .select_related("education_level", "target_stream")
        )

        if edu_level is not None:
            # Show questions tagged to this exact education level OR truly generic (no level tag)
            # Q(education_level=edu_level) handles level-specific questions
            # Q(education_level__isnull=True) handles generic questions with no level restriction
            # Questions tagged to OTHER levels are automatically excluded by this filter
            qs = qs.filter(
                models.Q(education_level=edu_level)
                | models.Q(education_level__isnull=True)
            )
            HIGHER_SECONDARY_CODE = "higher_secondary"
            level_code = (edu_level.level_code or "").lower()
            if level_code == HIGHER_SECONDARY_CODE and user_stream is not None:
                qs = qs.filter(
                    models.Q(target_stream=user_stream)
                    | models.Q(target_stream__isnull=True)
                )

        return qs.order_by("dimension", "id")

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        grouped = {}
        for q in qs:
            grouped.setdefault(q.dimension, []).append(q)
        data = {
            dim: self.get_serializer(items, many=True).data
            for dim, items in grouped.items()
        }
        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)


class ApiAssessmentSubmitViewSet(viewsets.GenericViewSet):
    """
    POST /api/assessment/submit/
    Body:
      { "responses": [ { "question_id": 1, "option_id": 2 } ] }
    Logic:
      - bulk insert/update UserResponse for logged-in user
      - validate question exists
      - validate option belongs to question
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = AssessmentSubmitSerializer
    from utils.throttles import PerUserBurstRateThrottle

    throttle_classes = [PerUserBurstRateThrottle]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        # Auto-save education_level and stream to profile if provided alongside responses.
        # This lets the frontend send everything in one call instead of two.
        education_level_id = request.data.get("education_level")
        stream_id = request.data.get("stream")
        if education_level_id or stream_id:
            from user_profile.models import UserProfile
            from education_level.models import EducationLevel
            from stream.models import Stream
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            if education_level_id:
                try:
                    edu = EducationLevel.objects.get(id=education_level_id, is_active=True, deleted=False)
                    profile.education_level = edu
                except EducationLevel.DoesNotExist:
                    return Response(
                        {"success": False, "message": {"education_level": "Invalid education level."}, "data": {}},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            if stream_id:
                try:
                    stream = Stream.objects.get(id=stream_id, is_active=True, deleted=False)
                    profile.stream = stream
                except Stream.DoesNotExist:
                    return Response(
                        {"success": False, "message": {"stream": "Invalid stream."}, "data": {}},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            profile.save()

        ser = self.get_serializer(data=request.data)
        if not ser.is_valid():
            return Response(
                {"success": False, "message": ser.errors, "data": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        responses = ser.validated_data.get("responses") or []
        if not responses:
            return Response(
                {
                    "success": False,
                    "message": {"responses": ["This field is required."]},
                    "data": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        question_ids = [r["question_id"] for r in responses]
        option_ids = [r["option_id"] for r in responses]

        questions = Question.objects.filter(id__in=question_ids).only(
            "id", "dimension", "is_active"
        )
        q_by_id = {q.id: q for q in questions}
        missing_questions = sorted({qid for qid in question_ids if qid not in q_by_id})
        if missing_questions:
            return Response(
                {
                    "success": False,
                    "message": {
                        "question_id": f"Invalid question_id(s): {missing_questions}"
                    },
                    "data": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        options = Option.objects.filter(id__in=option_ids).only(
            "id", "question_id", "score_value"
        )
        opt_by_id = {o.id: o for o in options}
        missing_options = sorted({oid for oid in option_ids if oid not in opt_by_id})
        if missing_options:
            return Response(
                {
                    "success": False,
                    "message": {
                        "option_id": f"Invalid option_id(s): {missing_options}"
                    },
                    "data": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate option belongs to question
        invalid_pairs = []
        for r in responses:
            qid = r["question_id"]
            oid = r["option_id"]
            opt = opt_by_id.get(oid)
            if not opt or opt.question_id != qid:
                invalid_pairs.append({"question_id": qid, "option_id": oid})
        if invalid_pairs:
            return Response(
                {
                    "success": False,
                    "message": {
                        "responses": "Option does not belong to the question.",
                        "invalid": invalid_pairs,
                    },
                    "data": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Existing responses for this user/questions
        existing = UserResponse.objects.filter(
            user=request.user, question_id__in=question_ids
        ).only(
            "id",
            "question_id",
            "selected_option_id",
            "score_value",
        )
        existing_by_qid = {ur.question_id: ur for ur in existing}

        to_create = []
        to_update = []
        for r in responses:
            qid = r["question_id"]
            oid = r["option_id"]
            opt = opt_by_id[oid]
            ur = existing_by_qid.get(qid)
            if ur is None:
                to_create.append(
                    UserResponse(
                        user=request.user,
                        question_id=qid,
                        selected_option_id=oid,
                        score_value=opt.score_value,
                    )
                )
            else:
                ur.selected_option_id = oid
                ur.score_value = opt.score_value
                to_update.append(ur)

        if to_create:
            UserResponse.objects.bulk_create(to_create, ignore_conflicts=True)
        if to_update:
            UserResponse.objects.bulk_update(
                to_update, ["selected_option", "score_value"]
            )

        # Invalidate per-user recommendations cache (safe, no-op if cache backend unavailable)
        try:
            from utils.cache_keys import recommendation_key

            cache.delete(recommendation_key(request.user.id))
        except Exception:
            pass

        return Response(
            {
                "success": True,
                "message": "Responses saved",
                "data": {"submitted": len(responses)},
            },
            status=status.HTTP_200_OK,
        )


class ApiAssessmentSummaryViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    GET /api/assessment/summary/
    Returns score per dimension (simple sum of saved responses).
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def list(self, request, *args, **kwargs):
        rows = (
            UserResponse.objects.filter(user=request.user)
            .values("question__dimension")
            .annotate(score=Sum("score_value"))
            .order_by("question__dimension")
        )
        data = {r["question__dimension"]: (r["score"] or 0) for r in rows}
        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)
