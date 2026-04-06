import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from assessment.models import Option, Question
from education_level.models import EducationLevel
from stream.models import Stream


User = get_user_model()


class RecommendationAdminQATests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Admin user
        cls.admin = User.objects.create_superuser(
            email="admin@example.com",
            username="admin",
            password="pass12345",
        )

        # A "student" user to run QA on
        cls.student = User.objects.create_user(
            email="student@example.com",
            username="student",
            password="pass12345",
        )

        # Minimal master data for overrides
        cls.edu_10 = EducationLevel.objects.create(
            level_code="secondary",
            display_name="10th",
            sequence_order=2,
            min_age=14,
            max_age=16,
            is_active=True,
            deleted=False,
        )
        cls.edu_12 = EducationLevel.objects.create(
            level_code="higher_secondary",
            display_name="12th",
            sequence_order=3,
            min_age=16,
            max_age=18,
            is_active=True,
            deleted=False,
        )
        cls.edu_grad = EducationLevel.objects.create(
            level_code="graduation",
            display_name="Graduation",
            sequence_order=6,
            min_age=20,
            max_age=25,
            is_active=True,
            deleted=False,
        )

        cls.stream_science = Stream.objects.create(
            id=uuid.uuid4(),
            stream_code="science",
            stream_name="Science",
            sequence_order=1,
            is_active=True,
            deleted=False,
        )

        # Create 5 questions per dimension with 5 options each
        for dim in ("interest", "aptitude", "personality", "work_style"):
            for i in range(5):
                q = Question.objects.create(
                    question_text=f"{dim} question {i}",
                    dimension=dim,
                    signal_strength=3,
                    is_active=True,
                )
                for score in range(1, 6):
                    Option.objects.create(
                        question=q,
                        option_text=f"opt {score}",
                        score_value=score,
                    )

    def setUp(self):
        self.client.force_login(self.admin)

    def _qa_url(self, user_id, edu_id=None, stream_id=None):
        base = reverse("admin:recommendation-qa")
        q = f"?user={user_id}"
        if edu_id:
            q += f"&education_level={edu_id}"
        if stream_id:
            q += f"&stream={stream_id}"
        return base + q

    def test_admin_qa_get_renders(self):
        url = self._qa_url(self.student.id, self.edu_grad.id, self.stream_science.id)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Recommendation QA")

    def test_admin_qa_post_submits_answers(self):
        url = self._qa_url(self.student.id, self.edu_grad.id, self.stream_science.id)
        # Load page to get questions list deterministically
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        # Build answers: pick score 5 for each question
        post = {"_qa_submit": "1"}
        for q in Question.objects.filter(is_active=True)[:20]:
            opt = Option.objects.filter(question=q, score_value=5).first()
            post[f"q_{q.id}"] = str(opt.id)

        r2 = self.client.post(url, data=post)
        self.assertEqual(r2.status_code, 200)
        self.assertContains(r2, "Assessment responses saved")

    def test_admin_qa_tiers_do_not_error(self):
        # Validate separate education levels render without error
        for edu in (self.edu_10, self.edu_12, self.edu_grad):
            url = self._qa_url(self.student.id, edu.id, self.stream_science.id)
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200)

