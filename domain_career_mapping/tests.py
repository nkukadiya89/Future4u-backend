import uuid

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from career.models import Career
from domain.models import Domain
from domain_career_mapping.models import DomainCareerMapping
from education_level.models import EducationLevel

User = get_user_model()


class DomainCareerMappingAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="dcm_tester@example.com",
            username="dcm_tester",
            password="pass12345",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.edu = EducationLevel.objects.create(
            level_code="dcmsec",
            display_name="Secondary",
            sequence_order=9800,
            min_age=13,
            max_age=16,
            is_active=True,
            created_by=self.user,
        )
        self.domain = Domain.objects.create(
            domain_code="dcm_domain",
            domain_name="DCM Domain",
            parent_acceptance_level=3,
            future_relevance_score=80,
            is_active=True,
            created_by=self.user,
        )
        self.career = Career.objects.create(
            career_code="dcm_career",
            career_name="DCM Career",
            min_education_level=self.edu,
            is_active=True,
            created_by=self.user,
        )

    def _payload(self, **extra):
        return {
            "domain": str(self.domain.pk),
            "career": str(self.career.pk),
            "weight_score": 85,
            "is_active": True,
            **extra,
        }

    def test_model_constraints(self):
        obj = DomainCareerMapping.objects.create(
            domain=self.domain,
            career=self.career,
            weight_score=50,
            is_active=True,
            created_by=self.user,
        )
        self.assertIn("DCM Domain", str(obj))

    def test_crud_and_soft_delete_and_restore(self):
        r = self.client.post(reverse("domain-career-mapping-list"), self._payload(), format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        pk = r.data["data"]["id"]

        r = self.client.delete(reverse("domain-career-mapping-detail", args=[pk]))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(DomainCareerMapping.objects.get(pk=pk).deleted)

        r = self.client.post(reverse("domain-career-mapping-bulk-restore"), {"ids": [pk]}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(DomainCareerMapping.objects.get(pk=pk).deleted)

    def test_duplicate_validation(self):
        url = reverse("domain-career-mapping-list")
        self.client.post(url, self._payload(), format="json")
        r = self.client.post(url, self._payload(), format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weight_validation(self):
        r = self.client.post(reverse("domain-career-mapping-list"), self._payload(weight_score=101), format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bulk_upload(self):
        c2 = Career.objects.create(
            career_code=f"dcm_career_{uuid.uuid4().hex[:6]}",
            career_name="Second Career",
            min_education_level=self.edu,
            is_active=True,
            created_by=self.user,
        )
        csv_body = (
            "domain_code,career_code,weight_score,is_active\n"
            f"{self.domain.domain_code},{self.career.career_code},80,1\n"
            f"{self.domain.domain_code},{c2.career_code},not_a_number,1\n"
        )
        f = SimpleUploadedFile("dcm.csv", csv_body.encode("utf-8"), content_type="text/csv")
        r = self.client.post(reverse("domain-career-mapping-bulk-import"), {"file": f}, format="multipart")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertIn("success_count", r.data)
        self.assertIn("error_count", r.data)
        self.assertIn("error_details", r.data)

    def test_permissions(self):
        anon = APIClient()
        r = anon.get(reverse("domain-career-mapping-list"))
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

