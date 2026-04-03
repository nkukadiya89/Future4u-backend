"""
Assessment system tests — education-level aware flow.

Covers:
  - 10th  (secondary)     → questions filtered, recommendation returns stream_ranking
  - 12th  (higher_secondary) → questions filtered by stream, recommendation returns domain ranking
  - ITI                   → questions filtered, recommendation returns entry-level careers
  - Diploma               → questions filtered, recommendation returns entry-level careers
  - Graduation            → questions filtered, recommendation returns full career scores
  - Post Graduation       → questions filtered, recommendation returns advanced careers
  - PhD (doctorate)       → questions filtered, recommendation returns research careers
  - Professional          → questions filtered, recommendation returns upskilling domains

Run with:
    python manage.py test assessment --verbosity=2
"""

import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from assessment.models import Option, Question, UserResponse
from assessment.services.recommendation_engine_service import RecommendationEngineService
from domain.models import Domain
from education_level.models import EducationLevel
from stream.models import Stream
from user_profile.models import UserProfile

User = get_user_model()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(email_prefix):
    return User.objects.create_user(
        email=f"{email_prefix}_{uuid.uuid4().hex[:6]}@test.com",
        password="testpass123",
        first_name="Test",
        is_active=True,
    )


def make_education_level(code, display, seq):
    # Use high sequence numbers to avoid collisions with real data in test DB
    obj, _ = EducationLevel.objects.get_or_create(
        level_code=code,
        defaults=dict(display_name=display, sequence_order=seq, min_age=10, max_age=50, is_active=True),
    )
    return EducationLevel.objects.get(pk=obj.pk)  # always return fresh from DB


def make_stream(code, name, seq, edu_level, parent_safe=True):
    return Stream.objects.get_or_create(
        stream_code=code,
        defaults=dict(
            stream_name=name,
            sequence_order=seq,
            parent_safe_label=parent_safe,
            education_level=edu_level,
            is_active=True,
        ),
    )[0]


def make_domain(code, name):
    """
    Create a Domain using raw SQL to handle any extra NOT NULL columns
    (e.g. suggested_degrees, counselor_note) that may exist in the DB
    from previous migrations but aren't yet on the ORM model.
    Falls back to ORM get if the domain already exists.
    """
    from django.db import connection

    try:
        return Domain.objects.get(domain_code=code)
    except Domain.DoesNotExist:
        pass

    import uuid as _uuid
    from django.utils import timezone

    domain_id = _uuid.uuid4()
    now = timezone.now()

    # Get all columns for the domain table to detect extra NOT NULL ones
    with connection.cursor() as c:
        c.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='domain' AND is_nullable='NO' "
            "AND column_default IS NULL "
            "AND column_name NOT IN ("
            "  'id','domain_code','domain_name','parent_acceptance_level',"
            "  'future_relevance_score','description','created_at',"
            "  'deleted','is_active'"
            ")"
        )
        extra_notnull = [r[0] for r in c.fetchall()]

    # Build extra column assignments with empty string defaults
    extra_cols = ", ".join(extra_notnull)
    extra_vals = ", ".join(["''"] * len(extra_notnull))
    extra_clause = f", {extra_cols}" if extra_cols else ""
    extra_val_clause = f", {extra_vals}" if extra_vals else ""

    with connection.cursor() as c:
        c.execute(
            f"INSERT INTO domain (id, domain_code, domain_name, parent_acceptance_level, "
            f"future_relevance_score, description, created_at, deleted, is_active"
            f"{extra_clause}) "
            f"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s{extra_val_clause})",
            [str(domain_id), code, name, 1, 80, name, now, False, True],
        )

    return Domain.objects.get(domain_code=code)


def make_question(text, dimension, edu_level, mapped_domains=None, mapped_streams=None, target_stream=None, signal=3):
    q = Question.objects.create(
        question_text=text,
        dimension=dimension,
        education_level=edu_level,
        target_stream=target_stream,
        signal_strength=signal,
        is_active=True,
    )
    if mapped_domains:
        q.mapped_domains.set(mapped_domains)
    if mapped_streams:
        q.mapped_streams.set(mapped_streams)
    return q


def make_option(question, text, score):
    return Option.objects.create(question=question, option_text=text, score_value=score)


def answer_questions(user, questions, score=5):
    """Answer all given questions with the given score (default: max = Strongly Agree)."""
    for q in questions:
        opt = make_option(q, "Strongly Agree", score)
        UserResponse.objects.get_or_create(
            user=user,
            question=q,
            defaults=dict(selected_option=opt, score_value=score),
        )


# ---------------------------------------------------------------------------
# Base test case with shared fixtures
# ---------------------------------------------------------------------------

class AssessmentBaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Education levels
        cls.edu_secondary = make_education_level("secondary", "Secondary (10th)", 2)
        cls.edu_higher_sec = make_education_level("higher_secondary", "Higher Secondary (12th)", 3)
        cls.edu_iti = make_education_level("iti", "ITI / Vocational", 4)
        cls.edu_diploma = make_education_level("diploma", "Diploma", 5)
        cls.edu_grad = make_education_level("graduation", "Graduation", 6)
        cls.edu_pg = make_education_level("post_graduation", "Post Graduation", 7)
        cls.edu_phd = make_education_level("doctorate", "Doctorate (PhD)", 8)
        cls.edu_professional = make_education_level("professional", "Professional", 9)

        # Streams (for 10th recommendations + 12th filtering)
        cls.stream_science = make_stream("science", "Science", 8001, cls.edu_higher_sec)
        cls.stream_commerce = make_stream("commerce", "Commerce", 8002, cls.edu_higher_sec)
        cls.stream_arts = make_stream("arts", "Arts", 8003, cls.edu_higher_sec)
        cls.stream_sports = make_stream("sports", "Sports", 8004, cls.edu_higher_sec)

        # Domains
        cls.domain_ai = make_domain("ai_data_test", "AI & Data")
        cls.domain_fintech = make_domain("fintech_test", "Fintech")
        cls.domain_manufacturing = make_domain("manufacturing_test", "Manufacturing")
        cls.domain_cloud = make_domain("cloud_test", "Cloud Computing")
        cls.domain_sports_tech = make_domain("sports_tech_test", "Sports Tech")
        cls.domain_legaltech = make_domain("legaltech_test", "Legal Tech")


# ---------------------------------------------------------------------------
# 1. Question filtering tests
# ---------------------------------------------------------------------------

class QuestionFilteringTests(AssessmentBaseTestCase):
    """Verify that GET /api/assessment/questions/ returns only level-appropriate questions."""

    def setUp(self):
        # Refresh education level objects from DB to ensure PKs are current
        self.edu_secondary = EducationLevel.objects.get(level_code="secondary")
        self.edu_higher_sec = EducationLevel.objects.get(level_code="higher_secondary")
        self.edu_grad = EducationLevel.objects.get(level_code="graduation")
        self.stream_science = Stream.objects.get(stream_code="science")
        self.stream_commerce = Stream.objects.get(stream_code="commerce")

    def _client_for(self, edu_level, stream=None):
        user = make_user("qfilter")
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.education_level = edu_level
        if stream:
            profile.stream = stream
        profile.save()
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def _all_question_ids(self, client):
        r = client.get(reverse("api_assessment_questions-list"))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        ids = set()
        for questions in r.data["data"].values():
            for q in questions:
                ids.add(q["id"])
        return ids

    def test_10th_user_sees_only_secondary_and_generic_questions(self):
        uid = uuid.uuid4().hex[:6]
        q_secondary = make_question(f"10th only Q {uid}", "interest", self.edu_secondary,
                                    mapped_streams=[self.stream_science])
        q_grad = make_question(f"Grad only Q {uid}", "interest", self.edu_grad,
                               mapped_domains=[self.domain_ai])
        # Note: generic (null level) questions are intentionally shown to all users

        client = self._client_for(self.edu_secondary)
        ids = self._all_question_ids(client)

        self.assertIn(q_secondary.id, ids)
        self.assertNotIn(q_grad.id, ids)  # grad-tagged question must NOT appear for 10th user

    def test_12th_science_user_sees_science_and_untagged_12th_questions(self):
        uid = uuid.uuid4().hex[:6]
        q_science = make_question(f"12th science Q {uid}", "interest", self.edu_higher_sec,
                                  mapped_domains=[self.domain_ai],
                                  target_stream=self.stream_science)
        q_commerce = make_question(f"12th commerce Q {uid}", "interest", self.edu_higher_sec,
                                   mapped_domains=[self.domain_fintech],
                                   target_stream=self.stream_commerce)
        q_any_12th = make_question(f"12th generic Q {uid}", "aptitude", self.edu_higher_sec,
                                   mapped_domains=[self.domain_ai])

        client = self._client_for(self.edu_higher_sec, stream=self.stream_science)
        ids = self._all_question_ids(client)

        self.assertIn(q_science.id, ids)
        self.assertIn(q_any_12th.id, ids)
        self.assertNotIn(q_commerce.id, ids)  # commerce-stream question must NOT appear for science user

    def test_grad_user_does_not_see_10th_questions(self):
        uid = uuid.uuid4().hex[:6]
        q_10th = make_question(f"10th Q {uid}", "interest", self.edu_secondary,
                               mapped_streams=[self.stream_science])
        q_grad = make_question(f"Grad Q {uid}", "interest", self.edu_grad,
                               mapped_domains=[self.domain_ai])

        client = self._client_for(self.edu_grad)
        ids = self._all_question_ids(client)

        self.assertNotIn(q_10th.id, ids)  # 10th question must NOT appear for grad user
        self.assertIn(q_grad.id, ids)

    def test_unauthenticated_returns_401(self):
        r = APIClient().get(reverse("api_assessment_questions-list"))
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_questions_grouped_by_dimension(self):
        make_question("Interest Q", "interest", self.edu_grad, mapped_domains=[self.domain_ai])
        make_question("Aptitude Q", "aptitude", self.edu_grad, mapped_domains=[self.domain_ai])

        client = self._client_for(self.edu_grad)
        r = client.get(reverse("api_assessment_questions-list"))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        # Response data keys should be dimension names
        for key in r.data["data"]:
            self.assertIn(key, ["interest", "aptitude", "personality", "work_style"])


# ---------------------------------------------------------------------------
# 2. Submit + Recommendation tests per education level
# ---------------------------------------------------------------------------

class BaseRecommendationTest(AssessmentBaseTestCase):
    """Shared submit helper."""

    def _submit(self, client, responses):
        return client.post(
            reverse("api_assessment_submit-list"),
            {"responses": responses},
            format="json",
        )

    def _recommend(self, client):
        return client.get(reverse("api_assessment_summary-recommendation"))

    def _setup_user(self, edu_level, stream=None):
        user = make_user("rec")
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.education_level = edu_level
        if stream:
            profile.stream = stream
        profile.save()
        client = APIClient()
        client.force_authenticate(user=user)
        return user, client


class TenthGradeRecommendationTests(BaseRecommendationTest):
    """10th grade → should recommend streams, not careers."""

    def test_recommendation_type_is_stream(self):
        user, client = self._setup_user(self.edu_secondary)

        # Create science-signalling questions
        questions = [
            make_question(f"10th science Q{i}", "interest", self.edu_secondary,
                          mapped_streams=[self.stream_science], signal=4)
            for i in range(4)
        ]
        answer_questions(user, questions, score=5)

        result = RecommendationEngineService().recommend(user_id=user.id)
        self.assertEqual(result["recommendation_type"], "stream")
        self.assertIn("stream_ranking", result)
        self.assertFalse(result.get("career_scores"))  # no career scores for 10th

    def test_top_stream_matches_answered_questions(self):
        user, client = self._setup_user(self.edu_secondary)

        # Answer science questions with max score, sports with low score
        sci_qs = [
            make_question(f"sci Q{i}", "interest", self.edu_secondary,
                          mapped_streams=[self.stream_science], signal=4)
            for i in range(3)
        ]
        sports_qs = [
            make_question(f"sports Q{i}", "interest", self.edu_secondary,
                          mapped_streams=[self.stream_sports], signal=4)
            for i in range(3)
        ]
        answer_questions(user, sci_qs, score=5)
        answer_questions(user, sports_qs, score=1)

        result = RecommendationEngineService().recommend(user_id=user.id)
        self.assertEqual(result["recommendation_type"], "stream")
        ranking = result["stream_ranking"]
        top = ranking[0]["stream_code"]
        self.assertEqual(top, "science")

    def test_no_responses_returns_fallback(self):
        user, _ = self._setup_user(self.edu_secondary)
        result = RecommendationEngineService().recommend(user_id=user.id)
        self.assertIsNone(result["top_career"])
        self.assertEqual(result["domain_ranking"], [])


class TwelfthGradeRecommendationTests(BaseRecommendationTest):
    """12th grade → should recommend college domains."""

    def test_recommendation_type_is_college_domain(self):
        user, client = self._setup_user(self.edu_higher_sec, stream=self.stream_science)

        questions = [
            make_question(f"12th sci Q{i}", "interest", self.edu_higher_sec,
                          mapped_domains=[self.domain_ai], target_stream=self.stream_science, signal=4)
            for i in range(4)
        ]
        answer_questions(user, questions, score=5)

        result = RecommendationEngineService().recommend(user_id=user.id)
        self.assertEqual(result["recommendation_type"], "college_domain")
        self.assertIn("domain_ranking", result)
        self.assertFalse(result.get("career_scores"))

    def test_top_domain_reflects_answered_questions(self):
        user, client = self._setup_user(self.edu_higher_sec, stream=self.stream_commerce)

        fintech_qs = [
            make_question(f"fintech Q{i}", "interest", self.edu_higher_sec,
                          mapped_domains=[self.domain_fintech], target_stream=self.stream_commerce, signal=4)
            for i in range(4)
        ]
        answer_questions(user, fintech_qs, score=5)

        result = RecommendationEngineService().recommend(user_id=user.id)
        self.assertEqual(result["recommendation_type"], "college_domain")
        self.assertEqual(result["domain_ranking"][0]["domain_code"], "fintech_test")


class ITIRecommendationTests(BaseRecommendationTest):
    """ITI → entry-level career recommendations."""

    def test_recommendation_type_is_career_and_entry_level_flag(self):
        user, _ = self._setup_user(self.edu_iti)

        questions = [
            make_question(f"iti Q{i}", "interest", self.edu_iti,
                          mapped_domains=[self.domain_manufacturing], signal=4)
            for i in range(4)
        ]
        answer_questions(user, questions, score=5)

        result = RecommendationEngineService().recommend(user_id=user.id)
        self.assertEqual(result["recommendation_type"], "career")
        self.assertTrue(result.get("is_entry_level"))
        self.assertIn("domain_ranking", result)


class DiplomaRecommendationTests(BaseRecommendationTest):
    """Diploma → entry-level career recommendations."""

    def test_diploma_is_entry_level(self):
        user, _ = self._setup_user(self.edu_diploma)

        questions = [
            make_question(f"dip Q{i}", "aptitude", self.edu_diploma,
                          mapped_domains=[self.domain_manufacturing], signal=4)
            for i in range(4)
        ]
        answer_questions(user, questions, score=5)

        result = RecommendationEngineService().recommend(user_id=user.id)
        self.assertEqual(result["recommendation_type"], "career")
        self.assertTrue(result.get("is_entry_level"))


class GraduationRecommendationTests(BaseRecommendationTest):
    """Graduation → full career recommendations."""

    def test_recommendation_type_is_career_not_entry_level(self):
        user, _ = self._setup_user(self.edu_grad)

        questions = [
            make_question(f"grad Q{i}", "interest", self.edu_grad,
                          mapped_domains=[self.domain_ai], signal=4)
            for i in range(4)
        ]
        answer_questions(user, questions, score=5)

        result = RecommendationEngineService().recommend(user_id=user.id)
        self.assertEqual(result["recommendation_type"], "career")
        self.assertFalse(result.get("is_entry_level"))
        self.assertIn("domain_ranking", result)

    def test_top_domain_is_most_answered(self):
        user, _ = self._setup_user(self.edu_grad)

        ai_qs = [
            make_question(f"ai Q{i}", "interest", self.edu_grad,
                          mapped_domains=[self.domain_ai], signal=5)
            for i in range(5)
        ]
        cloud_qs = [
            make_question(f"cloud Q{i}", "interest", self.edu_grad,
                          mapped_domains=[self.domain_cloud], signal=2)
            for i in range(2)
        ]
        answer_questions(user, ai_qs, score=5)
        answer_questions(user, cloud_qs, score=2)

        result = RecommendationEngineService().recommend(user_id=user.id)
        top = result["domain_ranking"][0]["domain_code"]
        self.assertEqual(top, "ai_data_test")


class PostGradRecommendationTests(BaseRecommendationTest):
    """Post Graduation → advanced career recommendations, not entry level."""

    def test_pg_is_not_entry_level(self):
        user, _ = self._setup_user(self.edu_pg)

        questions = [
            make_question(f"pg Q{i}", "interest", self.edu_pg,
                          mapped_domains=[self.domain_ai], signal=5)
            for i in range(4)
        ]
        answer_questions(user, questions, score=5)

        result = RecommendationEngineService().recommend(user_id=user.id)
        self.assertEqual(result["recommendation_type"], "career")
        self.assertFalse(result.get("is_entry_level"))


class PhDRecommendationTests(BaseRecommendationTest):
    """PhD → research-oriented career recommendations."""

    def test_phd_recommendation(self):
        user, _ = self._setup_user(self.edu_phd)

        questions = [
            make_question(f"phd Q{i}", "interest", self.edu_phd,
                          mapped_domains=[self.domain_ai], signal=5)
            for i in range(4)
        ]
        answer_questions(user, questions, score=5)

        result = RecommendationEngineService().recommend(user_id=user.id)
        self.assertEqual(result["recommendation_type"], "career")
        self.assertFalse(result.get("is_entry_level"))
        self.assertGreater(len(result["domain_ranking"]), 0)


class ProfessionalRecommendationTests(BaseRecommendationTest):
    """Professional → upskilling domain recommendations."""

    def test_professional_recommendation(self):
        user, _ = self._setup_user(self.edu_professional)

        questions = [
            make_question(f"pro Q{i}", "interest", self.edu_professional,
                          mapped_domains=[self.domain_cloud], signal=4)
            for i in range(4)
        ]
        answer_questions(user, questions, score=5)

        result = RecommendationEngineService().recommend(user_id=user.id)
        self.assertEqual(result["recommendation_type"], "career")
        self.assertFalse(result.get("is_entry_level"))
        self.assertEqual(result["domain_ranking"][0]["domain_code"], "cloud_test")


# ---------------------------------------------------------------------------
# 3. Submit API tests
# ---------------------------------------------------------------------------

class AssessmentSubmitAPITests(BaseRecommendationTest):
    """Test the POST /api/assessment/submit/ endpoint."""

    def test_submit_valid_responses(self):
        user, client = self._setup_user(self.edu_grad)
        q = make_question("Submit Q", "interest", self.edu_grad, mapped_domains=[self.domain_ai])
        opt = make_option(q, "Agree", 4)

        r = self._submit(client, [{"question_id": q.id, "option_id": opt.id}])
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.data["success"])
        self.assertEqual(r.data["data"]["submitted"], 1)

    def test_submit_invalid_question_id(self):
        _, client = self._setup_user(self.edu_grad)
        r = self._submit(client, [{"question_id": 999999, "option_id": 1}])
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(r.data["success"])

    def test_submit_option_not_belonging_to_question(self):
        _, client = self._setup_user(self.edu_grad)
        q1 = make_question("Q1", "interest", self.edu_grad, mapped_domains=[self.domain_ai])
        q2 = make_question("Q2", "interest", self.edu_grad, mapped_domains=[self.domain_ai])
        opt2 = make_option(q2, "Agree", 4)

        r = self._submit(client, [{"question_id": q1.id, "option_id": opt2.id}])
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_submit_empty_responses(self):
        _, client = self._setup_user(self.edu_grad)
        r = self._submit(client, [])
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_submit_updates_existing_response(self):
        user, client = self._setup_user(self.edu_grad)
        q = make_question("Update Q", "interest", self.edu_grad, mapped_domains=[self.domain_ai])
        opt1 = make_option(q, "Agree", 4)
        opt2 = make_option(q, "Strongly Agree", 5)

        self._submit(client, [{"question_id": q.id, "option_id": opt1.id}])
        self._submit(client, [{"question_id": q.id, "option_id": opt2.id}])

        ur = UserResponse.objects.get(user=user, question=q)
        self.assertEqual(ur.score_value, 5)

    def test_submit_requires_auth(self):
        q = make_question("Auth Q", "interest", self.edu_grad, mapped_domains=[self.domain_ai])
        opt = make_option(q, "Agree", 4)
        r = APIClient().post(
            reverse("api_assessment_submit-list"),
            {"responses": [{"question_id": q.id, "option_id": opt.id}]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# 4. Summary API tests
# ---------------------------------------------------------------------------

class AssessmentSummaryAPITests(BaseRecommendationTest):
    def test_summary_returns_dimension_scores(self):
        user, client = self._setup_user(self.edu_grad)
        q = make_question("Summary Q", "interest", self.edu_grad, mapped_domains=[self.domain_ai])
        opt = make_option(q, "Agree", 4)
        UserResponse.objects.create(user=user, question=q, selected_option=opt, score_value=4)

        r = client.get(reverse("api_assessment_summary-list"))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("interest", r.data["data"])
        self.assertEqual(r.data["data"]["interest"], 4)

    def test_recommendation_endpoint_on_summary(self):
        user, client = self._setup_user(self.edu_grad)
        questions = [
            make_question(f"rec Q{i}", "interest", self.edu_grad, mapped_domains=[self.domain_ai], signal=4)
            for i in range(3)
        ]
        answer_questions(user, questions, score=5)

        r = self._recommend(client)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.data["success"])
        self.assertIn("recommendation_type", r.data["data"])


# ---------------------------------------------------------------------------
# 5. Edge cases
# ---------------------------------------------------------------------------

class EdgeCaseTests(BaseRecommendationTest):
    def test_user_without_profile_gets_fallback(self):
        user = make_user("noprofile")
        # No UserProfile created
        result = RecommendationEngineService().recommend(user_id=user.id)
        self.assertIsNone(result["recommendation_type"])
        self.assertEqual(result["domain_ranking"], [])

    def test_user_with_profile_but_no_education_level(self):
        user = make_user("noedu")
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.education_level = None
        profile.save()
        result = RecommendationEngineService().recommend(user_id=user.id)
        # Falls through to career path with no responses → fallback
        self.assertIsNone(result.get("top_career"))

    def test_10th_user_gets_no_career_scores(self):
        user, _ = self._setup_user(self.edu_secondary)
        questions = [
            make_question(f"10th Q{i}", "interest", self.edu_secondary,
                          mapped_streams=[self.stream_science])
            for i in range(3)
        ]
        answer_questions(user, questions, score=5)
        result = RecommendationEngineService().recommend(user_id=user.id)
        self.assertFalse(result.get("career_scores"))

    def test_12th_user_gets_no_career_scores(self):
        user, _ = self._setup_user(self.edu_higher_sec, stream=self.stream_arts)
        questions = [
            make_question(f"12th Q{i}", "interest", self.edu_higher_sec,
                          mapped_domains=[self.domain_legaltech])
            for i in range(3)
        ]
        answer_questions(user, questions, score=5)
        result = RecommendationEngineService().recommend(user_id=user.id)
        self.assertFalse(result.get("career_scores"))
