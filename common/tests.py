from django.test import TestCase


class RecommendationEngineServiceTests(TestCase):
    """Smoke tests for the new RecommendationEngineService."""

    def _make_user(self, *, email="u1@example.com"):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.create_user(email=email, password="pass1234", is_active=True)

    def _make_education_level(self, *, code="graduation", seq=6):
        from education_level.models import EducationLevel
        return EducationLevel.objects.create(
            level_code=code, display_name=code.title(),
            sequence_order=seq, min_age=0, max_age=99,
            is_active=True, deleted=False,
        )

    def _make_profile(self, *, user, edu):
        from user_profile.models import UserProfile
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.education_level = edu
        profile.save()
        return profile

    def test_no_profile_returns_fallback(self):
        from services.recommendation_engine_service import RecommendationEngineService
        user = self._make_user(email="noprofile@example.com")
        result = RecommendationEngineService().recommend(user_id=user.id)
        self.assertIsNone(result["recommendation_type"])
        self.assertEqual(result["domain_ranking"], [])

    def test_no_responses_returns_fallback(self):
        from services.recommendation_engine_service import RecommendationEngineService
        user = self._make_user(email="noresponses@example.com")
        edu = self._make_education_level(code="graduation", seq=6)
        self._make_profile(user=user, edu=edu)
        result = RecommendationEngineService().recommend(user_id=user.id)
        self.assertIsNone(result.get("top_career"))
        self.assertEqual(result["domain_ranking"], [])

    def test_result_always_has_counsellor(self):
        from services.recommendation_engine_service import RecommendationEngineService
        user = self._make_user(email="counsellor@example.com")
        result = RecommendationEngineService().recommend(user_id=user.id)
        self.assertIn("counsellor", result)
        self.assertIn("label", result["counsellor"])
