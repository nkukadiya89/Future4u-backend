from django.core.cache import cache
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from assessment.models import (
    AssessmentAttempt,
    AssessmentInterestCategory,
    Option,
    Question,
    UserResponse,
)
from assessment.serializers import (
    AssessmentSubmitSerializer,
    QuestionSerializer,
    StudentInterestCategorySerializer,
    StudentInterestSaveSerializer,
)
from education_level.models import EducationLevel
from stream.models import Stream
from user_profile.models import StudentProfile
from utils.cache_keys import recommendation_key
from utils.throttles import PerUserBurstRateThrottle


DEFAULT_MIN_SIGNAL = 4
DEFAULT_LIMIT_PER_DIMENSION = 5


def success_response(data=None, message=""):
    return Response(
        {"success": True, "message": message, "data": data if data is not None else {}},
        status=status.HTTP_200_OK,
    )


def error_response(message, response_status=status.HTTP_400_BAD_REQUEST):
    return Response(
        {"success": False, "message": message, "data": {}},
        status=response_status,
    )


def get_student_profile(user):
    return StudentProfile.objects.filter(user=user).first()


def get_latest_attempt(user):
    return AssessmentAttempt.objects.filter(user=user).order_by("-created_at").first()


def get_latest_completed_attempt(user):
    return (
        AssessmentAttempt.objects.filter(user=user, completed_at__isnull=False)
        .order_by("-completed_at")
        .first()
    )


def get_or_create_current_attempt(user):
    latest_attempt = get_latest_attempt(user)
    if latest_attempt and latest_attempt.completed_at is None:
        return latest_attempt

    attempt_count = AssessmentAttempt.objects.filter(user=user).count()
    return AssessmentAttempt.objects.create(
        user=user,
        attempt_number=attempt_count + 1,
    )


def get_student_questions(request, with_options=True, dimension=None):
    profile = get_student_profile(request.user)
    education_level = profile.education_level if profile else None
    stream = profile.stream if profile else None

    questions = Question.objects.filter(is_active=True)

    if with_options:
        questions = questions.select_related(
            "education_level",
            "target_stream",
        ).prefetch_related(
            "options",
            "mapped_domains",
            "mapped_streams",
        )
    else:
        questions = questions.only(
            "id",
            "dimension",
            "education_level",
            "target_stream",
            "signal_strength",
        )

    if education_level:
        questions = questions.filter(
            models.Q(education_level=education_level)
            | models.Q(education_level__isnull=True)
        )

        is_higher_secondary = (
            (education_level.level_code or "").lower() == "higher_secondary"
        )
        if is_higher_secondary and stream:
            questions = questions.filter(
                models.Q(target_stream=stream)
                | models.Q(target_stream__isnull=True)
            )

    questions = questions.filter(signal_strength__gte=DEFAULT_MIN_SIGNAL)

    if dimension:
        questions = questions.filter(dimension=dimension)

    return questions.order_by("dimension", "id")


def get_required_question_ids(request):
    questions = get_student_questions(request, with_options=False)

    grouped = {}
    for question in questions:
        grouped.setdefault(question.dimension, [])
        if len(grouped[question.dimension]) < DEFAULT_LIMIT_PER_DIMENSION:
            grouped[question.dimension].append(question.id)

    required_ids = set()
    for question_ids in grouped.values():
        required_ids.update(question_ids)

    return required_ids


class StudentInterestCategoriesViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = StudentInterestCategorySerializer

    def get_queryset(self):
        return AssessmentInterestCategory.objects.filter(
            is_active=True,
            deleted=False,
        ).order_by("sequence_order", "category_name")

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return success_response(serializer.data)


class StudentInterestViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = StudentInterestSaveSerializer

    def list(self, request, *args, **kwargs):
        attempt = get_latest_attempt(request.user)
        interests = AssessmentInterestCategory.objects.none()
        if attempt:
            interests = attempt.domain_interests.filter(is_active=True, deleted=False)
        data = StudentInterestCategorySerializer(interests, many=True).data
        return success_response(data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return error_response(serializer.errors)

        attempt = get_or_create_current_attempt(request.user)
        attempt.domain_interests.set(serializer.validated_data["domain_interests"])
        cache.delete(recommendation_key(request.user.id))

        interests = attempt.domain_interests.filter(is_active=True, deleted=False)
        data = StudentInterestCategorySerializer(interests, many=True).data
        return success_response(data, "Interest areas saved")


class StudentAssessmentQuestionsViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = QuestionSerializer

    def get_questions(self, request):
        return get_student_questions(
            request,
            dimension=request.query_params.get("dimension"),
        )

    def list(self, request, *args, **kwargs):
        questions = self.get_questions(request)

        data = {}
        for question in questions:
            data.setdefault(question.dimension, [])
            if len(data[question.dimension]) < DEFAULT_LIMIT_PER_DIMENSION:
                data[question.dimension].append(question)

        for dimension, items in data.items():
            data[dimension] = self.get_serializer(items, many=True).data

        return success_response(data)


class StudentAssessmentSubmitViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = AssessmentSubmitSerializer
    throttle_classes = [PerUserBurstRateThrottle]

    def save_profile_fields(self, request):
        education_level_id = request.data.get("education_level")
        stream_id = request.data.get("stream")

        if not education_level_id and not stream_id:
            return None

        profile = get_student_profile(request.user)
        if not profile:
            return "Student profile not found."

        if education_level_id:
            education_level = EducationLevel.objects.filter(
                id=education_level_id,
                is_active=True,
                deleted=False,
            ).first()
            if not education_level:
                return {"education_level": "Invalid education level."}
            profile.education_level = education_level

        if stream_id:
            stream = Stream.objects.filter(
                id=stream_id,
                is_active=True,
                deleted=False,
            ).first()
            if not stream:
                return {"stream": "Invalid stream."}
            profile.stream = stream

        profile.save()
        return None

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        profile_error = self.save_profile_fields(request)
        if profile_error:
            response_status = (
                status.HTTP_404_NOT_FOUND
                if isinstance(profile_error, str)
                else status.HTTP_400_BAD_REQUEST
            )
            return error_response(profile_error, response_status)

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return error_response(serializer.errors)

        responses = serializer.validated_data.get("responses") or []
        if not responses:
            return error_response({"responses": ["This field is required."]})

        question_ids = []
        option_ids = []
        for item in responses:
            question_ids.append(item["question_id"])
            option_ids.append(item["option_id"])

        required_question_ids = get_required_question_ids(request)
        submitted_question_ids = set(question_ids)
        if submitted_question_ids != required_question_ids:
            return error_response(
                {
                    "responses": "Incomplete assessment.",
                    "missing_question_ids": sorted(
                        required_question_ids - submitted_question_ids
                    ),
                    "extra_question_ids": sorted(
                        submitted_question_ids - required_question_ids
                    ),
                }
            )

        if len(set(question_ids)) != len(question_ids):
            return error_response("Duplicate question answers are not allowed.")

        options = Option.objects.filter(id__in=option_ids).only(
            "id",
            "question_id",
            "score_value",
        )
        options_by_id = {option.id: option for option in options}

        if len(options_by_id) != len(set(option_ids)):
            return error_response("Invalid option selected.")

        for item in responses:
            option = options_by_id[item["option_id"]]
            if option.question_id != item["question_id"]:
                return error_response("Option does not belong to the question.")

        attempt = get_or_create_current_attempt(request.user)
        attempt.responses.all().delete()

        user_responses = []
        for item in responses:
            option = options_by_id[item["option_id"]]
            user_responses.append(
                UserResponse(
                    user=request.user,
                    attempt=attempt,
                    question_id=item["question_id"],
                    selected_option_id=item["option_id"],
                    score_value=option.score_value,
                )
            )

        UserResponse.objects.bulk_create(user_responses)
        attempt.completed_at = timezone.now()
        attempt.save(update_fields=["completed_at"])
        cache.delete(recommendation_key(request.user.id))

        return success_response({"submitted": len(responses)}, "Responses saved")


class StudentAssessmentStatusViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def list(self, request, *args, **kwargs):
        latest_attempt = get_latest_attempt(request.user)
        attempt_count = AssessmentAttempt.objects.filter(user=request.user).count()
        answered_count = 0

        if latest_attempt:
            answered_count = UserResponse.objects.filter(attempt=latest_attempt).count()

        data = {
            "status": (
                "complete"
                if latest_attempt and latest_attempt.completed_at
                else "incomplete"
            ),
            "attempt_count": attempt_count,
            "answered": answered_count,
        }
        return success_response(data)


class StudentAssessmentSummaryViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def list(self, request, *args, **kwargs):
        latest_attempt = get_latest_completed_attempt(request.user)
        responses = (
            UserResponse.objects.filter(attempt=latest_attempt)
            if latest_attempt
            else UserResponse.objects.filter(user=request.user)
        )

        rows = (
            responses
            .values("question__dimension")
            .annotate(score=Sum("score_value"))
            .order_by("question__dimension")
        )

        data = {}
        for row in rows:
            data[row["question__dimension"]] = row["score"] or 0

        return success_response(data)
