import time
import uuid

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from education_level.models import EducationLevel

User = get_user_model()


class EducationLevelAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="education_level_tester@example.com",
            username="education_level_tester",
            password="pass12345",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _payload(self, code=None, sequence_order=None, **extra):
        return {
            "level_code": code or f"level_{uuid.uuid4().hex[:8]}",
            "display_name": "Test Level",
            "sequence_order": sequence_order or 1000,
            "is_active": True,
            **extra,
        }

    def test_crud_and_soft_delete(self):
        url = reverse("education-level-list")
        r = self.client.post(url, self._payload(), format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        pk = r.data["data"]["id"]

        r = self.client.get(reverse("education-level-detail", args=[pk]))
        self.assertEqual(r.status_code, status.HTTP_200_OK)

        r = self.client.patch(
            reverse("education-level-detail", args=[pk]),
            {"display_name": "Updated"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"]["display_name"], "Updated")

        r = self.client.delete(reverse("education-level-detail", args=[pk]))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(EducationLevel.objects.get(pk=pk).deleted)

    def test_level_code_case_insensitive_unique(self):
        url = reverse("education-level-list")
        self.client.post(
            url, self._payload(code="10TH", sequence_order=1), format="json"
        )
        r = self.client.post(
            url, self._payload(code="10th", sequence_order=2), format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_sequence_order_unique(self):
        url = reverse("education-level-list")
        self.client.post(
            url, self._payload(code="10th", sequence_order=1), format="json"
        )
        r = self.client.post(
            url, self._payload(code="12th", sequence_order=1), format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_status(self):
        pk = self.client.post(
            reverse("education-level-list"),
            self._payload(code="status_l", sequence_order=5),
            format="json",
        ).data["data"]["id"]
        r = self.client.post(
            reverse("education-level-change-status", args=[pk]),
            {"is_active": False},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(r.data["data"]["is_active"])

    def test_dropdown_excludes_archived(self):
        pk = self.client.post(
            reverse("education-level-list"),
            self._payload(code="drop_l", sequence_order=8),
            format="json",
        ).data["data"]["id"]
        self.client.delete(reverse("education-level-detail", args=[pk]))
        r = self.client.get(reverse("education-level-dropdown"))
        ids = [row["id"] for row in r.data["data"]]
        self.assertNotIn(pk, ids)

    def test_reorder(self):
        url = reverse("education-level-list")
        a = self.client.post(
            url, self._payload(code="10th", sequence_order=10), format="json"
        ).data["data"]["id"]
        b = self.client.post(
            url, self._payload(code="12th", sequence_order=11), format="json"
        ).data["data"]["id"]
        r = self.client.post(
            reverse("education-level-reorder"),
            {
                "orders": [
                    {"id": a, "sequence_order": 20},
                    {"id": b, "sequence_order": 21},
                ]
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(EducationLevel.objects.get(pk=a).sequence_order, 20)
        self.assertEqual(EducationLevel.objects.get(pk=b).sequence_order, 21)

    def test_bulk_archive_restore(self):
        url = reverse("education-level-list")
        p1 = self.client.post(
            url, self._payload(code="bulk_1", sequence_order=30), format="json"
        ).data["data"]["id"]
        p2 = self.client.post(
            url, self._payload(code="bulk_2", sequence_order=31), format="json"
        ).data["data"]["id"]
        r = self.client.post(
            reverse("education-level-bulk-archive"),
            {"ids": [p1, p2]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        r = self.client.post(
            reverse("education-level-bulk-restore"),
            {"ids": [p1]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(EducationLevel.objects.get(pk=p1).deleted)

    def test_bulk_upload_csv_file(self):
        csv_body = (
            "level_code,display_name,sequence_order\n"
            "l_csv_1,CSV One,101\n"
            "l_csv_1,CSV Dup,102\n"
        )
        f = SimpleUploadedFile(
            "education_level.csv", csv_body.encode("utf-8"), content_type="text/csv"
        )
        r = self.client.post(
            reverse("education-level-bulk-upload"), {"file": f}, format="multipart"
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["success_count"], 1)
        self.assertEqual(r.data["error_count"], 1)
        self.assertTrue(r.data["error_details"])

    def test_bulk_import_partial_failure(self):
        rows = [
            {
                "level_code": "import_ok",
                "display_name": "Import Ok",
                "sequence_order": 100,
            },
            {
                "level_code": "import_ok",
                "display_name": "Import Dup",
                "sequence_order": 101,
            },
        ]
        r = self.client.post(
            reverse("education-level-bulk-import"), {"rows": rows}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["data"]["imported_count"], 1)
        self.assertEqual(r.data["data"]["failed_count"], 1)

    def test_archived_list(self):
        pk = self.client.post(
            reverse("education-level-list"),
            self._payload(code="archive_l", sequence_order=200),
            format="json",
        ).data["data"]["id"]
        self.client.delete(reverse("education-level-detail", args=[pk]))
        r = self.client.get(reverse("education-level-archived"))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        payload = r.data.get("results", r.data)
        rows = payload.get("data", r.data.get("data", []))
        self.assertTrue(any(row["id"] == pk for row in rows))

    @override_settings(DEBUG=True)
    def test_list_query_budget(self):
        url = reverse("education-level-list")
        for i in range(5):
            self.client.post(
                url, self._payload(code=f"q_{i}", sequence_order=300 + i), format="json"
            )
        connection.force_debug_cursor = True
        connection.queries_log.clear()
        self.client.get(url)
        self.assertLessEqual(len(connection.queries), 30)

    def test_list_response_time_budget(self):
        url = reverse("education-level-list")
        for i in range(8):
            self.client.post(
                url, self._payload(code=f"t_{i}", sequence_order=400 + i), format="json"
            )
        t0 = time.perf_counter()
        self.client.get(url)
        self.assertLess(time.perf_counter() - t0, 2.0)
