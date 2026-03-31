from django.test import TestCase

# Create your tests here.


class RecommendationEngineServiceTests(TestCase):
    def _make_user(self, *, email="u1@example.com", password="pass1234"):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        return User.objects.create_user(
            email=email,
            password=password,
            first_name="Test",
            last_name="User",
            is_active=True,
        )

    def _make_education_level(self, *, code="graduation", seq=5):
        from education_level.models import EducationLevel

        return EducationLevel.objects.create(
            level_code=code,
            display_name=code.title(),
            sequence_order=seq,
            min_age=0,
            max_age=99,
            is_active=True,
            deleted=False,
        )

    def _make_stream(self, *, code="science"):
        from stream.models import Stream

        return Stream.objects.create(
            stream_code=code,
            stream_name=code.title(),
            sequence_order=1,
            parent_safe_label=False,
            traditional_equivalent="",
            description="",
            is_active=True,
            deleted=False,
        )

    def _make_domain(self, *, code="engineering", name="Engineering", frs=80):
        from domain.models import Domain

        return Domain.objects.create(
            domain_code=code,
            domain_name=name,
            parent_acceptance_level=3,
            future_relevance_score=frs,
            description="",
            is_active=True,
            deleted=False,
        )

    def _make_skill(self, *, code="python", name="Python"):
        from skill.models import Skill

        return Skill.objects.create(
            skill_code=code,
            skill_name=name,
            skill_type="technical",
            description="",
            is_active=True,
            deleted=False,
        )

    def _make_career(self, *, code="software_engineer", name="Software Engineer", min_edu=None, max_edu=None):
        from career.models import Career

        return Career.objects.create(
            career_code=code,
            career_name=name,
            description="",
            min_education_level=min_edu,
            max_education_level=max_edu,
            is_active=True,
            deleted=False,
        )

    def _make_profile(self, *, user, edu, stream):
        from user_profile.models import UserProfile

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.education_level = edu
        profile.stream = stream
        profile.save()
        return profile

    def _make_assessment(self, *, user):
        from assessment.models import Option, Question, UserResponse

        dims = ["interest", "aptitude", "personality", "work_style"]
        for d in dims:
            q = Question.objects.create(question_text=f"{d} q1", dimension=d, is_active=True)
            o1 = Option.objects.create(question=q, option_text="opt", score_value=5)
            UserResponse.objects.create(user=user, question=q, selected_option=o1, score_value=5)

    def test_user_with_full_data(self):
        from services.recommendation_engine_service import generate_recommendation
        from stream_domain_mapping.models import StreamDomainMapping
        from domain_skill_mapping.models import DomainSkillMapping
        from domain_career_mapping.models import DomainCareerMapping
        from user_skill.models import UserSkill

        user = self._make_user(email="full@example.com")
        edu = self._make_education_level(seq=5)
        stream = self._make_stream(code="science")
        self._make_profile(user=user, edu=edu, stream=stream)

        domain = self._make_domain(code="engineering", name="Engineering", frs=85)
        skill = self._make_skill(code="python", name="Python")
        career = self._make_career(min_edu=edu)

        StreamDomainMapping.objects.create(stream=stream, domain=domain, weight_score=90, is_primary=True, is_active=True, deleted=False)
        DomainSkillMapping.objects.create(domain=domain, skill=skill, weight_score=80, is_core=True, is_active=True, deleted=False)
        DomainCareerMapping.objects.create(domain=domain, career=career, weight_score=70, is_active=True, deleted=False)

        self._make_assessment(user=user)
        UserSkill.objects.create(user=user, skill=skill, proficiency_score=10, is_active=True, deleted=False)

        out = generate_recommendation(user.id)
        self.assertIn("top_domains", out)
        self.assertIn("top_careers", out)
        self.assertIn("skill_gaps", out)
        self.assertTrue(len(out["top_domains"]) >= 1)
        self.assertTrue(len(out["top_careers"]) >= 1)
        self.assertTrue(len(out["skill_gaps"]) >= 1)

    def test_missing_assessment_falls_back_neutral(self):
        from services.recommendation_engine_service import generate_recommendation
        from stream_domain_mapping.models import StreamDomainMapping

        user = self._make_user(email="neutral@example.com")
        edu = self._make_education_level(seq=5)
        stream = self._make_stream(code="science2")
        self._make_profile(user=user, edu=edu, stream=stream)

        domain = self._make_domain(code="business", name="Business", frs=60)
        StreamDomainMapping.objects.create(stream=stream, domain=domain, weight_score=50, is_primary=True, is_active=True, deleted=False)

        out = generate_recommendation(user.id)
        self.assertEqual(out.get("message"), "ok")
        self.assertEqual(len(out["top_domains"]), 1)

    def test_no_user_skills_marks_unknown_gaps(self):
        from services.recommendation_engine_service import generate_recommendation
        from stream_domain_mapping.models import StreamDomainMapping
        from domain_skill_mapping.models import DomainSkillMapping

        user = self._make_user(email="noskills@example.com")
        edu = self._make_education_level(seq=5)
        stream = self._make_stream(code="science3")
        self._make_profile(user=user, edu=edu, stream=stream)

        domain = self._make_domain(code="design", name="Design", frs=75)
        skill = self._make_skill(code="communication", name="Communication")

        StreamDomainMapping.objects.create(stream=stream, domain=domain, weight_score=80, is_primary=True, is_active=True, deleted=False)
        DomainSkillMapping.objects.create(domain=domain, skill=skill, weight_score=60, is_core=True, is_active=True, deleted=False)

        out = generate_recommendation(user.id)
        self.assertTrue(any(x["gap_level"] == "UNKNOWN" for x in out["skill_gaps"]))

    def test_empty_mappings_returns_safe_empty(self):
        from services.recommendation_engine_service import generate_recommendation

        user = self._make_user(email="emptymap@example.com")
        edu = self._make_education_level(seq=5)
        stream = self._make_stream(code="science4")
        self._make_profile(user=user, edu=edu, stream=stream)

        out = generate_recommendation(user.id)
        self.assertEqual(out["top_domains"], [])
        self.assertEqual(out["top_careers"], [])
        self.assertEqual(out["skill_gaps"], [])
