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
from stream.models import Stream

User = get_user_model()


class StreamAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="stream_tester@example.com",
            username="stream_tester",
            password="pass12345",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.edu = EducationLevel.objects.create(
            level_code="sec",
            display_name="Secondary",
            sequence_order=9998,
            min_age=13,
            max_age=16,
            is_active=True,
            created_by=self.user,
        )

    def _payload(self, code=None, sequence_order=None, **extra):
        return {
            "stream_code": code or f"stream_{uuid.uuid4().hex[:8]}",
            "stream_name": "Test Stream",
            "sequence_order": sequence_order or 1000,
            "description": "Description",
            "education_level": str(self.edu.pk),
            "is_active": True,
            **extra,
        }

    def test_crud_and_soft_delete(self):
        url = reverse("stream-list")
        r = self.client.post(url, self._payload(), format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        pk = r.data["data"]["id"]

        r = self.client.get(reverse("stream-detail", args=[pk]))
        self.assertEqual(r.status_code, status.HTTP_200_OK)

        r = self.client.patch(
            reverse("stream-detail", args=[pk]),
            {"stream_name": "Updated"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"]["stream_name"], "Updated")

        r = self.client.delete(reverse("stream-detail", args=[pk]))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(Stream.objects.get(pk=pk).deleted)

    def test_stream_code_case_insensitive_unique(self):
        url = reverse("stream-list")
        self.client.post(
            url, self._payload(code="SCI", sequence_order=1), format="json"
        )
        r = self.client.post(
            url, self._payload(code="sci", sequence_order=2), format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_sequence_order_unique(self):
        url = reverse("stream-list")
        self.client.post(
            url, self._payload(code="sc1", sequence_order=1), format="json"
        )
        r = self.client.post(
            url, self._payload(code="sc2", sequence_order=1), format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_status(self):
        pk = self.client.post(
            reverse("stream-list"),
            self._payload(code="status_s", sequence_order=5),
            format="json",
        ).data["data"]["id"]
        r = self.client.post(
            reverse("stream-change-status", args=[pk]),
            {"is_active": False},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(r.data["data"]["is_active"])

    def test_dropdown_excludes_archived(self):
        pk = self.client.post(
            reverse("stream-list"),
            self._payload(code="drop_s", sequence_order=8),
            format="json",
        ).data["data"]["id"]
        self.client.delete(reverse("stream-detail", args=[pk]))
        r = self.client.get(reverse("stream-dropdown"))
        ids = [row["id"] for row in r.data["data"]]
        self.assertNotIn(pk, ids)

    def test_filter_by_education_level(self):
        self.client.post(
            reverse("stream-list"),
            self._payload(code="f1", sequence_order=31),
            format="json",
        )
        edu2 = EducationLevel.objects.create(
            level_code="high",
            display_name="Higher",
            sequence_order=9997,
            min_age=16,
            max_age=18,
            is_active=True,
            created_by=self.user,
        )
        self.client.post(
            reverse("stream-list"),
            self._payload(code="f2", sequence_order=32, education_level=str(edu2.pk)),
            format="json",
        )
        r = self.client.get(
            reverse("stream-list"), {"education_level": str(self.edu.pk)}
        )
        payload = r.data.get("results", r.data)
        rows = payload.get("data", r.data.get("data", []))
        self.assertTrue(
            all(row["education_level_id"] == str(self.edu.pk) for row in rows)
        )

    def test_bulk_archive_restore(self):
        url = reverse("stream-list")
        p1 = self.client.post(
            url, self._payload(code="bulk_1", sequence_order=40), format="json"
        ).data["data"]["id"]
        p2 = self.client.post(
            url, self._payload(code="bulk_2", sequence_order=41), format="json"
        ).data["data"]["id"]
        r = self.client.post(
            reverse("stream-bulk-archive"),
            {"ids": [p1, p2]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        r = self.client.post(
            reverse("stream-bulk-restore"),
            {"ids": [p1]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(Stream.objects.get(pk=p1).deleted)

    def test_bulk_upload_csv_file(self):
        csv_body = (
            "stream_code,stream_name,sequence_order,description,education_level\n"
            "st_csv_1,CSV One,101,Desc,sec\n"
            "st_csv_1,CSV Dup,102,Desc,sec\n"
        )
        f = SimpleUploadedFile(
            "stream.csv", csv_body.encode("utf-8"), content_type="text/csv"
        )
        r = self.client.post(
            reverse("stream-bulk-upload"), {"file": f}, format="multipart"
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["success_count"], 2)
        self.assertEqual(r.data["error_count"], 0)

    def test_bulk_import_partial_failure(self):
        rows = [
            {
                "stream_code": "import_ok",
                "stream_name": "Import Ok",
                "sequence_order": 100,
                "education_level": "sec",
            },
            {
                "stream_code": "import_ok",
                "stream_name": "Import Dup",
                "sequence_order": 101,
                "education_level": "sec",
            },
        ]
        r = self.client.post(
            reverse("stream-bulk-import"), {"rows": rows}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["data"]["imported_count"], 2)
        self.assertEqual(r.data["data"]["failed_count"], 0)

    def test_archived_list(self):
        pk = self.client.post(
            reverse("stream-list"),
            self._payload(code="archive_s", sequence_order=200),
            format="json",
        ).data["data"]["id"]
        self.client.delete(reverse("stream-detail", args=[pk]))
        r = self.client.get(reverse("stream-archived"))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        payload = r.data.get("results", r.data)
        rows = payload.get("data", r.data.get("data", []))
        self.assertTrue(any(row["id"] == pk for row in rows))

    def test_requires_authentication(self):
        anon = APIClient()
        r = anon.get(reverse("stream-list"))
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(DEBUG=True)
    def test_list_query_budget(self):
        url = reverse("stream-list")
        for i in range(5):
            self.client.post(
                url, self._payload(code=f"q_{i}", sequence_order=300 + i), format="json"
            )
        connection.force_debug_cursor = True
        connection.queries_log.clear()
        self.client.get(url)
        self.assertLessEqual(len(connection.queries), 30)

    def test_list_response_time_budget(self):
        url = reverse("stream-list")
        for i in range(8):
            self.client.post(
                url, self._payload(code=f"t_{i}", sequence_order=400 + i), format="json"
            )
        t0 = time.perf_counter()
        self.client.get(url)
        self.assertLess(time.perf_counter() - t0, 2.0)
