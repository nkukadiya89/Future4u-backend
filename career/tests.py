import time
import uuid

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from career.models import Career
from education_level.models import EducationLevel

User = get_user_model()


class CareerAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="career_tester@example.com",
            username="career_tester",
            password="pass12345",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.edu_min = EducationLevel.objects.create(
            level_code="higher_secondary",
            display_name="Higher Secondary",
            sequence_order=9001,
            min_age=16,
            max_age=18,
            is_active=True,
            created_by=self.user,
        )
        self.edu_max = EducationLevel.objects.create(
            level_code="graduation",
            display_name="Graduation",
            sequence_order=9002,
            min_age=18,
            max_age=24,
            is_active=True,
            created_by=self.user,
        )

    def _payload(self, code=None, **extra):
        return {
            "career_code": code or f"career_{uuid.uuid4().hex[:8]}",
            "career_name": "Test Career",
            "description": "Career description",
            "min_education_level": str(self.edu_min.pk),
            "max_education_level": str(self.edu_max.pk),
            "is_active": True,
            **extra,
        }

    def test_crud_and_soft_delete(self):
        url = reverse("career-list")
        r = self.client.post(url, self._payload(), format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        pk = r.data["data"]["id"]

        r = self.client.get(reverse("career-detail", args=[pk]))
        self.assertEqual(r.status_code, status.HTTP_200_OK)

        r = self.client.patch(
            reverse("career-detail", args=[pk]),
            {"career_name": "Updated"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"]["career_name"], "Updated")

        r = self.client.delete(reverse("career-detail", args=[pk]))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(Career.objects.get(pk=pk).deleted)

    def test_career_code_case_insensitive_unique(self):
        url = reverse("career-list")
        self.client.post(url, self._payload(code="AbC"), format="json")
        r = self.client.post(url, self._payload(code="abc"), format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_education_level_mapping_validation(self):
        bad = self.client.post(
            reverse("career-list"),
            self._payload(max_education_level=str(self.edu_min.pk), min_education_level=str(self.edu_max.pk)),
            format="json",
        )
        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_status(self):
        pk = self.client.post(reverse("career-list"), self._payload(), format="json").data["data"]["id"]
        r = self.client.post(
            reverse("career-change-status", args=[pk]),
            {"is_active": False},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(r.data["data"]["is_active"])

    def test_filter_by_education_level(self):
        self.client.post(reverse("career-list"), self._payload(code="filter_a"), format="json")
        edu_other = EducationLevel.objects.create(
            level_code="post_graduation",
            display_name="Post Graduation",
            sequence_order=9003,
            min_age=21,
            max_age=28,
            is_active=True,
            created_by=self.user,
        )
        self.client.post(
            reverse("career-list"),
            self._payload(code="filter_b", min_education_level=str(edu_other.pk)),
            format="json",
        )
        r = self.client.get(reverse("career-list"), {"education_level": str(self.edu_min.pk)})
        payload = r.data.get("results", r.data)
        rows = payload.get("data", r.data.get("data", []))
        self.assertTrue(all(row["min_education_level_id"] == str(self.edu_min.pk) for row in rows))

    def test_bulk_archive_restore(self):
        url = reverse("career-list")
        p1 = self.client.post(url, self._payload(code="bulk_1"), format="json").data["data"]["id"]
        p2 = self.client.post(url, self._payload(code="bulk_2"), format="json").data["data"]["id"]
        r = self.client.post(
            reverse("career-bulk-archive"),
            {"ids": [p1, p2]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        r = self.client.post(
            reverse("career-bulk-restore"),
            {"ids": [p1]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(Career.objects.get(pk=p1).deleted)

    def test_bulk_upload_csv_file(self):
        csv_body = (
            "career_code,career_name,min_education_level,max_education_level,description,is_active\n"
            "soft_eng,Software Engineer,higher_secondary,graduation,Build systems,1\n"
            "soft_eng,Duplicate,higher_secondary,graduation,Duplicate row,1\n"
        )
        f = SimpleUploadedFile("career.csv", csv_body.encode("utf-8"), content_type="text/csv")
        r = self.client.post(reverse("career-bulk-upload"), {"file": f}, format="multipart")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["success_count"], 1)
        self.assertEqual(r.data["error_count"], 1)

    def test_bulk_import_partial_failure(self):
        rows = [
            {
                "career_code": "import_ok",
                "career_name": "Import Ok",
                "min_education_level": "higher_secondary",
                "max_education_level": "graduation",
                "is_active": True,
            },
            {
                "career_code": "import_ok",
                "career_name": "Import Dup",
                "min_education_level": "higher_secondary",
                "max_education_level": "graduation",
                "is_active": True,
            },
        ]
        r = self.client.post(reverse("career-bulk-import"), {"rows": rows}, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["data"]["imported_count"], 1)
        self.assertEqual(r.data["data"]["failed_count"], 1)

    def test_archived_list(self):
        pk = self.client.post(reverse("career-list"), self._payload(), format="json").data["data"]["id"]
        self.client.delete(reverse("career-detail", args=[pk]))
        r = self.client.get(reverse("career-archived"))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        payload = r.data.get("results", r.data)
        rows = payload.get("data", r.data.get("data", []))
        self.assertTrue(any(row["id"] == pk for row in rows))

    def test_requires_authentication(self):
        anon = APIClient()
        r = anon.get(reverse("career-list"))
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(DEBUG=True)
    def test_list_query_budget(self):
        url = reverse("career-list")
        for i in range(5):
            self.client.post(url, self._payload(code=f"q_{i}"), format="json")
        connection.force_debug_cursor = True
        connection.queries_log.clear()
        self.client.get(url)
        self.assertLessEqual(len(connection.queries), 30)

    def test_list_response_time_budget(self):
        url = reverse("career-list")
        for i in range(8):
            self.client.post(url, self._payload(code=f"t_{i}"), format="json")
        t0 = time.perf_counter()
        self.client.get(url)
        self.assertLess(time.perf_counter() - t0, 2.0)

