import uuid

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from domain.models import Domain
from education_level.models import EducationLevel
from stream.models import Stream
from stream_domain_mapping.models import StreamDomainMapping

User = get_user_model()


class StreamDomainMappingAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="sdm_tester@example.com",
            username="sdm_tester",
            password="pass12345",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.edu = EducationLevel.objects.create(
            level_code="sdmsec",
            display_name="Secondary",
            sequence_order=9800,
            min_age=13,
            max_age=16,
            is_active=True,
            created_by=self.user,
        )
        self.stream = Stream.objects.create(
            stream_code="sdm_stream",
            stream_name="SDM Stream",
            sequence_order=9400,
            parent_safe_label=True,
            education_level=self.edu,
            is_active=True,
            created_by=self.user,
        )
        self.domain = Domain.objects.create(
            domain_code="sdm_domain",
            domain_name="SDM Domain",
            parent_acceptance_level=3,
            future_relevance_score=80,
            is_active=True,
            created_by=self.user,
        )

    def _payload(self, **extra):
        return {
            "stream": str(self.stream.pk),
            "domain": str(self.domain.pk),
            "weight_score": 85,
            "is_primary": True,
            "is_active": True,
            **extra,
        }

    def test_model_constraints(self):
        obj = StreamDomainMapping.objects.create(
            stream=self.stream,
            domain=self.domain,
            weight_score=50,
            is_primary=True,
            is_active=True,
            created_by=self.user,
        )
        self.assertIn("SDM Stream", str(obj))

    def test_crud_and_soft_delete(self):
        r = self.client.post(
            reverse("stream-domain-mapping-list"), self._payload(), format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        pk = r.data["data"]["id"]

        r = self.client.get(reverse("stream-domain-mapping-detail", args=[pk]))
        self.assertEqual(r.status_code, status.HTTP_200_OK)

        r = self.client.patch(
            reverse("stream-domain-mapping-detail", args=[pk]),
            {"weight_score": 91},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"]["weight_score"], 91)

        r = self.client.delete(reverse("stream-domain-mapping-detail", args=[pk]))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(StreamDomainMapping.objects.get(pk=pk).deleted)

    def test_duplicate_validation(self):
        url = reverse("stream-domain-mapping-list")
        self.client.post(url, self._payload(), format="json")
        r = self.client.post(url, self._payload(), format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_search_ordering(self):
        d2 = Domain.objects.create(
            domain_code="sdm_domain_2",
            domain_name="Robotics",
            parent_acceptance_level=3,
            future_relevance_score=70,
            is_active=True,
            created_by=self.user,
        )
        self.client.post(
            reverse("stream-domain-mapping-list"),
            self._payload(weight_score=20),
            format="json",
        )
        self.client.post(
            reverse("stream-domain-mapping-list"),
            self._payload(domain=str(d2.pk), weight_score=99),
            format="json",
        )
        r = self.client.get(
            reverse("stream-domain-mapping-list"),
            {
                "stream": str(self.stream.pk),
                "search": "Robotics",
                "ordering": "-weight_score",
            },
        )
        payload = r.data.get("results", r.data)
        rows = payload.get("data", r.data.get("data", []))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["domain_name"], "Robotics")

    def test_dropdown_by_stream(self):
        d2 = Domain.objects.create(
            domain_code="sdm_domain_3",
            domain_name="Finance",
            parent_acceptance_level=3,
            future_relevance_score=70,
            is_active=True,
            created_by=self.user,
        )
        self.client.post(
            reverse("stream-domain-mapping-list"),
            self._payload(weight_score=25),
            format="json",
        )
        self.client.post(
            reverse("stream-domain-mapping-list"),
            self._payload(domain=str(d2.pk), weight_score=88),
            format="json",
        )
        r = self.client.get(
            reverse(
                "stream-domain-mapping-by-stream",
                kwargs={"stream_id": str(self.stream.pk)},
            )
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(
            r.data["data"][0]["weight_score"], r.data["data"][1]["weight_score"]
        )

    def test_bulk_upload(self):
        d2 = Domain.objects.create(
            domain_code="sdm_domain_4",
            domain_name="Economics",
            parent_acceptance_level=3,
            future_relevance_score=70,
            is_active=True,
            created_by=self.user,
        )
        csv_body = (
            "stream_code,domain_code,weight_score,is_primary,is_active\n"
            f"{self.stream.stream_code},{self.domain.domain_code},80,1,1\n"
            f"{self.stream.stream_code},{d2.domain_code},not_a_number,0,1\n"
        )
        f = SimpleUploadedFile(
            "sdm.csv", csv_body.encode("utf-8"), content_type="text/csv"
        )
        r = self.client.post(
            reverse("stream-domain-mapping-bulk-import"),
            {"file": f},
            format="multipart",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertIn("success_count", r.data)
        self.assertIn("error_count", r.data)
        self.assertIn("error_details", r.data)

    def test_permissions(self):
        anon = APIClient()
        r = anon.get(reverse("stream-domain-mapping-list"))
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_bulk_archive_restore_and_archived(self):
        d2 = Domain.objects.create(
            domain_code=f"sdm_domain_{uuid.uuid4().hex[:6]}",
            domain_name="Bulk Domain",
            parent_acceptance_level=2,
            future_relevance_score=60,
            is_active=True,
            created_by=self.user,
        )
        p1 = self.client.post(
            reverse("stream-domain-mapping-list"),
            self._payload(weight_score=45),
            format="json",
        ).data["data"]["id"]
        p2 = self.client.post(
            reverse("stream-domain-mapping-list"),
            self._payload(domain=str(d2.pk), weight_score=55),
            format="json",
        ).data["data"]["id"]

        r = self.client.post(
            reverse("stream-domain-mapping-bulk-archive"),
            {"ids": [p1, p2]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        r = self.client.get(reverse("stream-domain-mapping-archived"))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        r = self.client.post(
            reverse("stream-domain-mapping-bulk-restore"), {"ids": [p1]}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
