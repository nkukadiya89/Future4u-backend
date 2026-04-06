import time
import uuid

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.db.utils import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from skill.models import Skill

User = get_user_model()


class SkillModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="skill_model_tester@example.com",
            username="skill_model_tester",
            password="pass12345",
        )

    def test_str_returns_skill_name(self):
        obj = Skill.objects.create(
            skill_code="str_skill",
            skill_name="String Skill",
            skill_type="technical",
            created_by=self.user,
        )
        self.assertEqual(str(obj), "String Skill")

    def test_case_insensitive_unique_constraint(self):
        Skill.objects.create(
            skill_code="ABC",
            skill_name="First",
            skill_type="technical",
            created_by=self.user,
        )
        with self.assertRaises(IntegrityError):
            Skill.objects.create(
                skill_code="abc",
                skill_name="Second",
                skill_type="technical",
                created_by=self.user,
            )


class SkillAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="skill_tester@example.com",
            username="skill_tester",
            password="pass12345",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _payload(self, code=None, name=None, **extra):
        return {
            "skill_code": code or f"s_{uuid.uuid4().hex[:8]}",
            "skill_name": name or "Test Skill",
            "skill_type": "technical",
            "description": "desc",
            "is_active": True,
            **extra,
        }

    def test_crud_and_soft_delete(self):
        url = reverse("skill-list")
        r = self.client.post(url, self._payload(), format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        pk = r.data["data"]["id"]

        r = self.client.get(reverse("skill-detail", args=[pk]))
        self.assertEqual(r.status_code, status.HTTP_200_OK)

        r = self.client.patch(
            reverse("skill-detail", args=[pk]),
            {"skill_name": "Updated"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"]["skill_name"], "Updated")

        r = self.client.delete(reverse("skill-detail", args=[pk]))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(Skill.objects.get(pk=pk).deleted)

    def test_skill_code_case_insensitive_unique(self):
        url = reverse("skill-list")
        self.client.post(url, self._payload(code="AbC"), format="json")
        r = self.client.post(url, self._payload(code="abc"), format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_skill_type_rejected(self):
        url = reverse("skill-list")
        r = self.client.post(
            url,
            self._payload(skill_type="invalid_type"),
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_status(self):
        pk = self.client.post(
            reverse("skill-list"), self._payload(), format="json"
        ).data["data"]["id"]
        r = self.client.post(
            reverse("skill-change-status", args=[pk]),
            {"is_active": False},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(r.data["data"]["is_active"])

    def test_dropdown_active_only(self):
        p1 = self.client.post(
            reverse("skill-list"), self._payload(code="dd_1"), format="json"
        ).data["data"]["id"]
        p2 = self.client.post(
            reverse("skill-list"),
            self._payload(code="dd_2", is_active=False),
            format="json",
        ).data["data"]["id"]
        self.client.delete(reverse("skill-detail", args=[p1]))
        r = self.client.get(reverse("skill-dropdown"))
        ids = [row["id"] for row in r.data["data"]]
        self.assertNotIn(p1, ids)
        self.assertNotIn(p2, ids)

    def test_filter_search_and_archived(self):
        self.client.post(
            reverse("skill-list"),
            self._payload(code="py_01", name="Python", skill_type="technical"),
            format="json",
        )
        archived = self.client.post(
            reverse("skill-list"),
            self._payload(code="soft_01", name="Communication", skill_type="soft"),
            format="json",
        ).data["data"]["id"]
        self.client.delete(reverse("skill-detail", args=[archived]))

        r = self.client.get(
            reverse("skill-list") + "?skill_type=technical&search=py_01"
        )
        payload = r.data.get("results", r.data)
        rows = payload.get("data", r.data.get("data", []))
        self.assertTrue(any(row["skill_code"] == "py_01" for row in rows))

        r = self.client.get(reverse("skill-archived"))
        payload = r.data.get("results", r.data)
        rows = payload.get("data", r.data.get("data", []))
        self.assertTrue(any(row["id"] == archived for row in rows))

    def test_bulk_archive_restore(self):
        url = reverse("skill-list")
        p1 = self.client.post(url, self._payload(code="bulk_1"), format="json").data[
            "data"
        ]["id"]
        p2 = self.client.post(url, self._payload(code="bulk_2"), format="json").data[
            "data"
        ]["id"]
        r = self.client.post(
            reverse("skill-bulk-archive"),
            {"ids": [p1, p2]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        r = self.client.post(
            reverse("skill-bulk-restore"),
            {"ids": [p1]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(Skill.objects.get(pk=p1).deleted)

    def test_bulk_upload_csv_file(self):
        csv_body = (
            "skill_code,skill_name,skill_type,description,is_active\n"
            "python,Python,technical,lang,1\n"
            "python,Duplicate,technical,lang,1\n"
        )
        f = SimpleUploadedFile(
            "s.csv", csv_body.encode("utf-8"), content_type="text/csv"
        )
        r = self.client.post(
            reverse("skill-bulk-upload"), {"file": f}, format="multipart"
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["success_count"], 1)
        self.assertEqual(r.data["error_count"], 1)
        self.assertTrue(r.data["error_details"])

    def test_bulk_import_partial_failure(self):
        url = reverse("skill-bulk-import")
        rows = [
            {
                "skill_code": "imp_ok",
                "skill_name": "OK",
                "skill_type": "technical",
            },
            {
                "skill_code": "imp_bad",
                "skill_name": "Bad",
                "skill_type": "invalid",
            },
        ]
        r = self.client.post(url, {"rows": rows}, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["data"]["imported_count"], 1)
        self.assertEqual(r.data["data"]["failed_count"], 1)

    @override_settings(DEBUG=True)
    def test_list_query_budget(self):
        url = reverse("skill-list")
        for i in range(5):
            self.client.post(url, self._payload(code=f"q_{i}"), format="json")
        connection.force_debug_cursor = True
        connection.queries_log.clear()
        self.client.get(url)
        self.assertLessEqual(len(connection.queries), 30)

    def test_list_response_time_budget(self):
        url = reverse("skill-list")
        for i in range(8):
            self.client.post(url, self._payload(code=f"t_{i}"), format="json")
        t0 = time.perf_counter()
        self.client.get(url)
        self.assertLess(time.perf_counter() - t0, 2.0)
