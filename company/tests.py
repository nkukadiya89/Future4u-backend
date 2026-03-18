from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from business_category.models import BusinessCategory
from company.models import Company
from user.models import CustomGroup


class BaseAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="tester@example.com", first_name="Tester", password="pass1234"
        )
        self.client.force_authenticate(user=self.user)
        self.category = BusinessCategory.objects.create(business_category="IT")
        self.admin_group = CustomGroup.objects.create(name="Company Admin", group_name="Company Admin")
        self.alog_patcher = patch("activity_log.models.ActivityLog.log", new=MagicMock())
        self.alog_patcher.start()

    def tearDown(self):
        if hasattr(self, "alog_patcher"):
            self.alog_patcher.stop()

    def create_company(self, **kwargs):
        defaults = dict(
            name="Acme Corp",
            person_name="Alice",
            email="alice@acme.com",
            phone="9999999999",
            gst_no="22AAAAA0000A1Z5",
            business_category=self.category,
            status="pending",
        )
        defaults.update(kwargs)
        return Company.objects.create(**defaults)


class CompanyModelTests(BaseAPITest):
    def test_str(self):
        c = self.create_company(name="Foo")
        self.assertEqual(str(c), "Foo")

    @patch("company.models.upload_file_to_bucket", return_value=("/path/logo.png", "presigned"))
    @patch("company.models.delete_uploaded_file")
    def test_upload_company_logo_presentation_replaces_file(self, mock_delete, mock_upload):
        c = self.create_company(company_logo="/old/logo.png")
        f = SimpleUploadedFile("logo.png", b"img", content_type="image/png")
        c.upload_company_logo_presentation(f)
        mock_delete.assert_called_once_with("/old/logo.png")
        mock_upload.assert_called_once()
        self.assertEqual(c.company_logo, "/path/logo.png")


class CompanySerializerValidationTests(BaseAPITest):
    def test_uniqueness_validation(self):
        self.create_company(name="Unique", email="u@x.com", phone="1111111111")
        url = reverse("company-list")
        import json as _json

        payload = {
            "form_data": _json.dumps(
                {
                    "name": "Unique",
                    "person_name": "Bob",
                    "email": "u@x.com",
                    "phone": "1111111111",
                    "gst_no": "22BBBBB0000B1Z5",
                }
            )
        }
        with patch("company.views.send_mail"):
            resp = self.client.post(url, data=payload, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class CompanyViewSetCRUDTests(BaseAPITest):
    @patch("company.serializer.create_company_role_family", return_value={"success": True, "company_group": []})
    @patch("company.views.send_mail")
    def test_create_company_success(self, _mail, _role):
        url = reverse("company-list")
        logo = SimpleUploadedFile("logo.png", b"data", content_type="image/png")
        data = {
            "name": "NewCo",
            "person_name": "Neo",
            "email": "neo@newco.com",
            "phone": "8888888888",
            "gst_no": "22CCCCC0000C1Z5",
        }
        import json as _json

        payload = {"form_data": _json.dumps(data), "company_logo": logo}
        with patch("company.models.upload_file_to_bucket", return_value=("/path/n.png", "url")):
            resp = self.client.post(url, data=payload, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data["success"])

    def test_list_companies_with_and_without_pagination(self):
        for i in range(3):
            self.create_company(name=f"C{i}", email=f"c{i}@x.com", phone=f"900000000{i}")
        url = reverse("company-list")
        r1 = self.client.get(url)
        self.assertEqual(r1.status_code, 200)
        r2 = self.client.get(url + "?no_pagination=1")
        self.assertEqual(r2.status_code, 200)
        self.assertIn("data", r2.data)

    def test_retrieve_update_destroy_company(self):
        c = self.create_company()
        detail = reverse("company-detail", args=[c.id])
        r = self.client.get(detail)
        self.assertEqual(r.status_code, 200)

        import json as _json

        new_data = {"phone": "7777777777", "person_name": "Updated"}
        payload = {"form_data": _json.dumps(new_data)}
        r2 = self.client.patch(detail, data=payload, format="multipart")
        self.assertEqual(r2.status_code, 200)
        c.refresh_from_db()
        self.assertEqual(c.phone, "7777777777")

        r3 = self.client.delete(detail)
        self.assertEqual(r3.status_code, 200)
        c.refresh_from_db()
        self.assertTrue(c.deleted)


class CompanyCustomActionsTests(BaseAPITest):
    @patch("company.views.delete_uploaded_file")
    def test_company_logo_delete_when_present(self, mock_delete):
        c = self.create_company(company_logo="/x/y.png")
        url = reverse("company-company-logo-delete", args=[c.id])
        r = self.client.patch(url)
        self.assertEqual(r.status_code, 200)
        mock_delete.assert_called_once_with("/x/y.png")

    def test_company_logo_delete_when_absent(self):
        c = self.create_company(company_logo=None)
        url = reverse("company-company-logo-delete", args=[c.id])
        r = self.client.patch(url)
        self.assertEqual(r.status_code, 400)

    def test_get_company_basic_info_and_404(self):
        c = self.create_company()
        url = f"/company/{c.id}/company-basic-info/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertIn("company_name", r.data)
        r2 = self.client.get("/company/99999/company-basic-info/")
        self.assertEqual(r2.status_code, 404)

    @patch("company.models.upload_file_to_bucket", return_value=("/new/logo.png", "url"))
    def test_update_company_basic_info(self, _):
        c = self.create_company()
        url = reverse("company-update-company-basic-info", args=[c.id])
        import json as _json

        fd = {
            "company_name": "Renamed",
            "person_name": "P",
            "email": "p@x.com",
            "phone": "6666666666",
            "gst_no": "22DDDDD0000D1Z5",
            "gst_address_city": "Ahmedabad",
        }
        payload = {"form_data": _json.dumps(fd)}
        r = self.client.patch(url, data=payload, format="multipart")
        self.assertEqual(r.status_code, 200)
        c.refresh_from_db()
        self.assertEqual(c.name, "Renamed")

    def test_change_company_password_validations_and_success(self):
        c = self.create_company()
        u = get_user_model().objects.create_user(email="admin@acme.com", password="old")
        u.company = c
        u.role = 1
        u.save()
        url = reverse("company-change-company-password", args=[c.id])
        r1 = self.client.patch(url, {"new_password": "a", "re_enter_password": "b"}, format="json")
        self.assertEqual(r1.status_code, 400)
        r2 = self.client.patch(url, {"new_password": "newpass", "re_enter_password": "newpass"}, format="json")
        self.assertEqual(r2.status_code, 200)

    def test_update_company_status_edge_cases_and_success(self):
        url = "/company/update-status/"
        r1 = self.client.patch(url, {"status": "active"}, format="json")
        self.assertEqual(r1.status_code, 400)
        r2 = self.client.patch(url, {"company_id": 1}, format="json")
        self.assertEqual(r2.status_code, 400)
        r3 = self.client.patch(url, {"company_id": 999, "status": "active"}, format="json")
        self.assertIn(r3.status_code, (404,))
        c = self.create_company()
        r4 = self.client.patch(url, {"company_id": c.id, "status": "active"}, format="json")
        self.assertEqual(r4.status_code, 200)
        c.refresh_from_db()
        self.assertTrue(c.is_active)


class CompanyArchiveRestoreTests(BaseAPITest):
    def test_archive_and_restore_single_and_multiple(self):
        c1 = self.create_company(name="A1", email="a1@x.com", phone="9000000001")
        c2 = self.create_company(name="A2", email="a2@x.com", phone="9000000002")
        arch_url = reverse("company_archive-list")
        res = self.client.post(arch_url, {"deleted": [c1.id, c2.id]}, format="json")
        self.assertEqual(res.status_code, 200)
        c1.refresh_from_db()
        c2.refresh_from_db()
        self.assertTrue(c1.deleted and c2.deleted)
        rest_url = reverse("company_restore-list")
        with patch("company.serializer.get_client_ip", return_value="127.0.0.1"):
            res2 = self.client.post(rest_url, {"deleted": [c1.id, c2.id]}, format="json")
        self.assertEqual(res2.status_code, 200)
        c1.refresh_from_db()
        c2.refresh_from_db()
        self.assertFalse(c1.deleted or c2.deleted)

    def test_archive_invalid_company(self):
        arch_url = reverse("company_archive-list")
        res = self.client.post(arch_url, {"deleted": [123456]}, format="json")
        self.assertEqual(res.status_code, 400)


class CreateCompanyAccountTests(BaseAPITest):
    @patch("company.serializer.create_company_role_family", return_value={"success": True, "company_group": []})
    @patch("email_utils.send_email.send_mail")
    def test_public_create_company_account(self, _mail, _role):
        self.client.force_authenticate(user=None)
        url = reverse("create_company_account-list")
        payload = {
            "name": "PublicCo",
            "person_name": "Paul",
            "email": "paul@public.co",
            "phone": 9991112222,
        }
        res = self.client.post(url, data=payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
