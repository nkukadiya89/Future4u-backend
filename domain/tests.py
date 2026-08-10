import time
import uuid

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from domain.models import Domain

User = get_user_model()


class DomainAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="domain_tester@example.com",
            username="domain_tester",
            password="pass12345",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _payload(self, code=None, name=None, **extra):
        return {
            "domain_code": code or f"d_{uuid.uuid4().hex[:8]}",
            "domain_name": "Test Domain" if name is None else name,
            "description": "desc",
            "is_active": True,
            **extra,
        }

    def test_crud_and_soft_delete(self):
        url = reverse("domain-list")
        r = self.client.post(url, self._payload(), format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        pk = r.data["data"]["id"]

        r = self.client.get(reverse("domain-detail", args=[pk]))
        self.assertEqual(r.status_code, status.HTTP_200_OK)

        r = self.client.patch(
            reverse("domain-detail", args=[pk]),
            {"domain_name": "Updated"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"]["domain_name"], "Updated")

        r = self.client.delete(reverse("domain-detail", args=[pk]))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(Domain.objects.get(pk=pk).deleted)

    def test_domain_code_case_insensitive_unique(self):
        url = reverse("domain-list")
        self.client.post(url, self._payload(code="AbC"), format="json")
        r = self.client.post(url, self._payload(code="abc"), format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_domain_name_required(self):
        url = reverse("domain-list")
        r = self.client.post(
            url,
            self._payload(name=""),
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_circular_parent_rejected(self):
        url = reverse("domain-list")
        a = self.client.post(url, self._payload(code="p_a"), format="json").data[
            "data"
        ]["id"]
        b = self.client.post(
            url,
            self._payload(code="p_b", parent_id=a),
            format="json",
        ).data["data"]["id"]
        r = self.client.patch(
            reverse("domain-detail", args=[a]),
            {"parent_id": b},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_archive_blocked_with_active_child(self):
        url = reverse("domain-list")
        a = self.client.post(url, self._payload(code="root_z"), format="json").data[
            "data"
        ]["id"]
        self.client.post(
            url,
            self._payload(code="child_z", parent_id=a),
            format="json",
        )
        r = self.client.delete(reverse("domain-detail", args=[a]))
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_status(self):
        pk = self.client.post(
            reverse("domain-list"), self._payload(), format="json"
        ).data["data"]["id"]
        r = self.client.post(
            reverse("domain-change-status", args=[pk]),
            {"is_active": False},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(r.data["data"]["is_active"])

    def test_dropdown_excludes_archived(self):
        pk = self.client.post(
            reverse("domain-list"), self._payload(), format="json"
        ).data["data"]["id"]
        self.client.delete(reverse("domain-detail", args=[pk]))
        r = self.client.get(reverse("domain-dropdown"))
        ids = [row["id"] for row in r.data["data"]]
        self.assertNotIn(pk, ids)

    def test_tree_shape(self):
        url = reverse("domain-list")
        root = self.client.post(url, self._payload(code="tree_r"), format="json").data[
            "data"
        ]["id"]
        self.client.post(
            url,
            self._payload(code="tree_c", parent_id=root),
            format="json",
        )
        r = self.client.get(reverse("domain-tree"))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        roots = [n for n in r.data["data"] if n["domain_code"] == "tree_r"]
        self.assertEqual(len(roots), 1)
        self.assertTrue(roots[0]["children"])

    def test_bulk_archive_restore(self):
        url = reverse("domain-list")
        p1 = self.client.post(url, self._payload(code="bulk_1"), format="json").data[
            "data"
        ]["id"]
        p2 = self.client.post(url, self._payload(code="bulk_2"), format="json").data[
            "data"
        ]["id"]
        r = self.client.post(
            reverse("domain-bulk-archive"),
            {"ids": [p1, p2]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        r = self.client.post(
            reverse("domain-bulk-restore"),
            {"ids": [p1]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertFalse(Domain.objects.get(pk=p1).deleted)

    def test_bulk_upload_csv_file(self):
        csv_body = (
            "domain_code,domain_name,parent,description,domain_image,is_active\n"
            "csv_up_1,One,,x,,1\n"
            "csv_up_1,Duplicate,,y,,1\n"
        )
        f = SimpleUploadedFile(
            "d.csv", csv_body.encode("utf-8"), content_type="text/csv"
        )
        r = self.client.post(
            reverse("domain-bulk-upload"), {"file": f}, format="multipart"
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["success_count"], 1)
        self.assertEqual(r.data["error_count"], 1)
        self.assertTrue(r.data["error_details"])

    def test_bulk_import_partial_failure(self):
        url = reverse("domain-bulk-import")
        rows = [
            {
                "domain_code": "imp_ok",
                "domain_name": "OK",
            },
            {
                "domain_code": "imp_ok",
                "domain_name": "Dup",
            },
        ]
        r = self.client.post(url, {"rows": rows}, format="json")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["data"]["imported_count"], 1)
        self.assertEqual(r.data["data"]["failed_count"], 1)

    def test_archived_list(self):
        pk = self.client.post(
            reverse("domain-list"), self._payload(), format="json"
        ).data["data"]["id"]
        self.client.delete(reverse("domain-detail", args=[pk]))
        r = self.client.get(reverse("domain-archived"))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        payload = r.data.get("results", r.data)
        rows = payload.get("data", r.data.get("data", []))
        self.assertTrue(any(row["id"] == pk for row in rows))

    @override_settings(DEBUG=True)
    def test_list_query_budget(self):
        url = reverse("domain-list")
        for i in range(5):
            self.client.post(url, self._payload(code=f"q_{i}"), format="json")
        connection.force_debug_cursor = True
        connection.queries_log.clear()
        self.client.get(url)
        self.assertLessEqual(len(connection.queries), 30)

    def test_list_filtered_by_parent_id(self):
        url = reverse("domain-list")
        root = self.client.post(url, self._payload(code="cat_root"), format="json").data["data"]["id"]
        other = self.client.post(url, self._payload(code="cat_other"), format="json").data["data"]["id"]
        child = self.client.post(url, self._payload(code="cat_child", parent_id=root), format="json").data["data"]["id"]

        r = self.client.get(url, {"parent_id": root})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        ids = [row["id"] for row in r.data["results"]["data"]]
        self.assertIn(child, ids)
        self.assertNotIn(root, ids)
        self.assertNotIn(other, ids)

    def test_list_invalid_parent_id_does_not_crash(self):
        url = reverse("domain-list")
        self.client.post(url, self._payload(code="no_crash"), format="json")
        r = self.client.get(url, {"parent_id": "not-a-uuid"})
        self.assertEqual(r.data["results"]["data"], [])
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_dropdown_invalid_parent_id_does_not_crash(self):
        url = reverse("domain-dropdown")
        r = self.client.get(url, {"parent_id": "not-a-uuid"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"], [])

    def test_list_root_only(self):
        url = reverse("domain-list")
        root = self.client.post(url, self._payload(code="ro_r"), format="json").data["data"]["id"]
        self.client.post(url, self._payload(code="ro_c", parent_id=root), format="json")
        r = self.client.get(url, {"root_only": "1"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        ids = [row["id"] for row in r.data["results"]["data"]]
        self.assertIn(root, ids)

    def test_list_response_time_budget(self):
        url = reverse("domain-list")
        for i in range(8):
            self.client.post(url, self._payload(code=f"t_{i}"), format="json")
        t0 = time.perf_counter()
        self.client.get(url)
        self.assertLess(time.perf_counter() - t0, 2.0)
