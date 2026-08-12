import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from city.models import City
from country.models import Country
from state.models import State
from user_profile.models import (
    CorporateProfile,
    InstituteProfile,
    ParentProfile,
    ProfessionalProfile,
    SchoolCollegeProfile,
    StudentProfile,
)

User = get_user_model()


class AdminUserArchiveAPITests(TestCase):
    """
    Admin archive list should return the full role-specific profile data
    (not just the User model fields) for every role.
    """

    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="archive_admin@example.com",
            password="pass12345",
            first_name="Admin",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

        self.country = Country.objects.create(
            name="India",
            code="IN",
            phone_code="91",
            created_by=self.admin,
            updated_by=self.admin,
        )
        self.state = State.objects.create(
            name="Gujarat",
            country=self.country,
            created_by=self.admin,
            updated_by=self.admin,
        )
        self.city = City.objects.create(
            name="Ahmedabad",
            country=self.country,
            state=self.state,
            created_by=self.admin,
            updated_by=self.admin,
        )

    def _archive_user(self, email, user_type):
        user = User.objects.create_user(
            email=email,
            username=email.split("@")[0],
            password="pass12345",
            user_type=user_type,
            is_active=False,
            status="inactive",
            deleted=True,
            deleted_at="2026-01-01T00:00:00Z",
            deleted_by=self.admin,
        )
        return user

    def test_archive_list_returns_student_profile_data(self):
        user = self._archive_user("arch_student@example.com", User.Role.STUDENT)
        StudentProfile.objects.create(
            user=user,
            medium="english",
            education_level=None,
            stream=None,
            skills=["Python", "Django"],
        )

        url = reverse("admin_users_archive-list")
        resp = self.client.get(url, {"user_type": User.Role.STUDENT})

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        rows = resp.data["results"]["data"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["user"], user.id)
        self.assertEqual(row["medium"], "english")
        self.assertEqual(row["skills"], ["Python", "Django"])
        self.assertNotIn("username", row)
        self.assertNotIn("is_superuser", row)
        self.assertNotIn("is_staff", row)

    def test_archive_list_returns_corporate_profile_data(self):
        user = self._archive_user("arch_corp@example.com", User.Role.CORPORATE)
        CorporateProfile.objects.create(
            user=user,
            company_name="Acme Corp",
            employees=100,
            website="https://acme.example.com",
        )

        url = reverse("admin_users_archive-list")
        resp = self.client.get(url, {"user_type": User.Role.CORPORATE})

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        rows = resp.data["results"]["data"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["company_name"], "Acme Corp")
        self.assertEqual(row["employees"], 100)
        self.assertEqual(row["website"], "https://acme.example.com")
        self.assertIsNotNone(row["deleted_at"])
        self.assertEqual(row["deleted_by"]["email"], "archive_admin@example.com")
        self.assertNotIn("deleted_by_name", row)
        self.assertNotIn("username", row)
        self.assertNotIn("is_superuser", row)
        self.assertNotIn("is_staff", row)

    def test_archive_list_returns_professional_profile_data(self):
        user = self._archive_user("arch_prof@example.com", User.Role.PROFESSIONAL)
        ProfessionalProfile.objects.create(
            user=user,
            employment_type="salaried_employee",
            years_of_experience="3_5_years",
            current_job_title="Backend Engineer",
        )

        url = reverse("admin_users_archive-list")
        resp = self.client.get(url, {"user_type": User.Role.PROFESSIONAL})

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        rows = resp.data["results"]["data"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["employment_type"], "salaried_employee")
        self.assertEqual(row["current_job_title"], "Backend Engineer")
        self.assertNotIn("username", row)
        self.assertNotIn("is_superuser", row)
        self.assertNotIn("is_staff", row)

    def test_archive_list_empty_when_no_profile_record(self):
        self._archive_user("arch_noprofile@example.com", User.Role.STUDENT)

        url = reverse("admin_users_archive-list")
        resp = self.client.get(url, {"user_type": User.Role.STUDENT})

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        rows = resp.data["results"]["data"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertNotIn("username", row)
        self.assertNotIn("is_superuser", row)
        self.assertEqual(row["deleted_by"]["id"], self.admin.id)
        self.assertIsNotNone(row["deleted_at"])

    def test_archive_list_returns_parent_profile_data(self):
        user = self._archive_user("arch_parent@example.com", User.Role.PARENT)
        ParentProfile.objects.create(
            user=user,
            relationship="father",
        )

        url = reverse("admin_users_archive-list")
        resp = self.client.get(url, {"user_type": User.Role.PARENT})

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        rows = resp.data["results"]["data"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["relationship"], "father")
        self.assertEqual(row["user"], user.id)
        self.assertNotIn("username", row)
        self.assertNotIn("is_superuser", row)
        self.assertNotIn("is_staff", row)

    def test_archive_list_returns_school_college_profile_data(self):
        user = self._archive_user("arch_school@example.com", User.Role.SCHOOL_COLLEGE)
        SchoolCollegeProfile.objects.create(
            user=user,
            institute_name="Green Valley School",
            board="CBSE",
        )

        url = reverse("admin_users_archive-list")
        resp = self.client.get(url, {"user_type": User.Role.SCHOOL_COLLEGE})

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        rows = resp.data["results"]["data"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["institute_name"], "Green Valley School")
        self.assertEqual(row["board"], "CBSE")
        self.assertNotIn("username", row)
        self.assertNotIn("is_superuser", row)
        self.assertNotIn("is_staff", row)

    def test_archive_list_no_pagination_returns_profile_data(self):
        user = self._archive_user("arch_nopage@example.com", User.Role.STUDENT)
        StudentProfile.objects.create(
            user=user,
            medium="hindi",
        )

        url = reverse("admin_users_archive-list")
        resp = self.client.get(
            url,
            {"user_type": User.Role.STUDENT, "no_pagination": "1"},
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("data", resp.data)
        rows = resp.data["data"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["medium"], "hindi")

    def test_archive_list_requires_admin(self):
        plain_user = User.objects.create_user(
            email="plain_archive@example.com",
            username="plain_archive",
            password="pass12345",
            user_type=User.Role.STUDENT,
            is_active=True,
            status="active",
        )
        self.client.force_authenticate(user=plain_user)

        url = reverse("admin_users_archive-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_archive_list_search_by_company_name(self):
        user_a = self._archive_user("arch_corp_a@example.com", User.Role.CORPORATE)
        CorporateProfile.objects.create(user=user_a, company_name="Acme Corp")
        user_b = self._archive_user("arch_corp_b@example.com", User.Role.CORPORATE)
        CorporateProfile.objects.create(user=user_b, company_name="Zenith Labs")

        url = reverse("admin_users_archive-list")
        resp = self.client.get(
            url,
            {"user_type": User.Role.CORPORATE, "search": "acme"},
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        rows = resp.data["results"]["data"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["company_name"], "Acme Corp")

    def test_archive_list_search_by_institute_name(self):
        user = self._archive_user("arch_inst@example.com", User.Role.INSTITUTE)
        InstituteProfile.objects.create(user=user, institute_name="Stanford Tech")

        url = reverse("admin_users_archive-list")
        resp = self.client.get(
            url,
            {"user_type": User.Role.INSTITUTE, "search": "stanford"},
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        rows = resp.data["results"]["data"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["institute_name"], "Stanford Tech")

    def test_archive_list_ordering_by_company_name(self):
        user_a = self._archive_user("arch_corp_a@example.com", User.Role.CORPORATE)
        CorporateProfile.objects.create(user=user_a, company_name="Zeta Corp")
        user_b = self._archive_user("arch_corp_b@example.com", User.Role.CORPORATE)
        CorporateProfile.objects.create(user=user_b, company_name="Alpha Corp")

        url = reverse("admin_users_archive-list")
        resp = self.client.get(
            url,
            {
                "user_type": User.Role.CORPORATE,
                "ordering": "corporate_profile__company_name",
            },
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        rows = resp.data["results"]["data"]
        names = [row["company_name"] for row in rows]
        self.assertEqual(names, ["Alpha Corp", "Zeta Corp"])

    def test_archive_list_ordering_by_institute_name(self):
        user_a = self._archive_user("arch_inst_a@example.com", User.Role.INSTITUTE)
        InstituteProfile.objects.create(user=user_a, institute_name="Zeta Institute")
        user_b = self._archive_user("arch_inst_b@example.com", User.Role.INSTITUTE)
        InstituteProfile.objects.create(user=user_b, institute_name="Alpha Institute")

        url = reverse("admin_users_archive-list")
        resp = self.client.get(
            url,
            {
                "user_type": User.Role.INSTITUTE,
                "ordering": "institute_profile__institute_name",
            },
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        rows = resp.data["results"]["data"]
        names = [row["institute_name"] for row in rows]
        self.assertEqual(names, ["Alpha Institute", "Zeta Institute"])

    def test_archive_list_search_across_roles(self):
        corp = self._archive_user("arch_search_corp@example.com", User.Role.CORPORATE)
        CorporateProfile.objects.create(user=corp, company_name="Acme Corp")
        inst = self._archive_user("arch_search_inst@example.com", User.Role.INSTITUTE)
        InstituteProfile.objects.create(user=inst, institute_name="Acme Institute")

        url = reverse("admin_users_archive-list")
        resp = self.client.get(url, {"search": "acme"})

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        rows = resp.data["results"]["data"]
        names = [row.get("company_name") or row.get("institute_name") for row in rows]
        self.assertEqual(sorted(names), ["Acme Corp", "Acme Institute"])


class OrganizationProfessionalAPITests(TestCase):
    def setUp(self):
        self.corporate = User.objects.create_user(
            email="corp_manager@example.com",
            username="corp_manager",
            password="pass12345",
            user_type=User.Role.CORPORATE,
            is_active=True,
            status="active",
        )
        self.student = User.objects.create_user(
            email="plain_student@example.com",
            username="plain_student",
            password="pass12345",
            user_type=User.Role.STUDENT,
            is_active=True,
            status="active",
        )

        self.country = Country.objects.create(
            name="India",
            code="IN",
            phone_code="91",
            created_by=self.corporate,
            updated_by=self.corporate,
        )
        self.state = State.objects.create(
            name="Gujarat",
            country=self.country,
            created_by=self.corporate,
            updated_by=self.corporate,
        )
        self.city = City.objects.create(
            name="Ahmedabad",
            country=self.country,
            state=self.state,
            created_by=self.corporate,
            updated_by=self.corporate,
        )

        self.client = APIClient()

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def _payload(self, **overrides):
        payload = {
            "email": "professional_one@example.com",
            "first_name": "Prof",
            "last_name": "One",
            "phone": "9876543210",
            "country": self.country.id,
            "state": self.state.id,
            "city": self.city.id,
            "address": "Test Street",
        }
        payload.update(overrides)
        return payload

    def _create_professional(self, **overrides):
        url = reverse("organization_professionals-list")
        return self.client.post(
            url,
            {"data": json.dumps(self._payload(**overrides))},
            format="multipart",
        )

    # ---------- Permissions ----------

    def test_unauthenticated_denied(self):
        url = reverse("organization_professionals-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_corporate_denied(self):
        self._auth(self.student)
        url = reverse("organization_professionals-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ---------- Create ----------

    @patch("user.tasks.send_password_setup_link_task")
    def test_corporate_creates_professional(self, mock_task):
        self._auth(self.corporate)
        resp = self._create_professional()

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data["success"])

        professional = User.objects.get(email="professional_one@example.com")
        self.assertEqual(professional.user_type, User.Role.PROFESSIONAL)
        self.assertEqual(professional.created_by, self.corporate)
        self.assertEqual(professional.status, "pending")
        self.assertFalse(professional.is_active)
        self.assertTrue(professional.must_change_password)
        self.assertTrue(ProfessionalProfile.objects.filter(user=professional).exists())
        mock_task.delay.assert_called_once()

    @patch("user.tasks.send_password_setup_link_task")
    def test_create_duplicate_email_rejected(self, mock_task):
        self._auth(self.corporate)
        self._create_professional()

        resp = self._create_professional(email="professional_one@example.com")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", resp.data)

    def test_create_invalid_json_rejected(self):
        self._auth(self.corporate)
        url = reverse("organization_professionals-list")
        resp = self.client.post(url, {"data": "{not-json"}, format="multipart")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_location_rejected(self):
        self._auth(self.corporate)
        resp = self._create_professional(country=999999)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ---------- List scoping ----------

    @patch("user.tasks.send_password_setup_link_task")
    def test_list_scoped_to_corporate(self, mock_task):
        self._auth(self.corporate)
        self._create_professional()

        other_corporate = User.objects.create_user(
            email="other_corp@example.com",
            username="other_corp",
            password="pass12345",
            user_type=User.Role.CORPORATE,
            is_active=True,
            status="active",
        )
        other_user = User.objects.create_user(
            email="other_corp_prof@example.com",
            username="other_corp_prof",
            password="pass12345",
            user_type=User.Role.PROFESSIONAL,
            is_active=True,
            status="active",
            created_by=other_corporate,
        )

        url = reverse("organization_professionals-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        emails = [row["email"] for row in resp.data["results"]["data"]]
        self.assertIn("professional_one@example.com", emails)
        self.assertNotIn(other_user.email, emails)

    @patch("user.tasks.send_password_setup_link_task")
    def test_retrieve_own_professional(self, mock_task):
        self._auth(self.corporate)
        created = self._create_professional()
        professional_id = created.data["professional_id"]

        url = reverse("organization_professionals-detail", args=[professional_id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["data"]["email"], "professional_one@example.com")

    @patch("user.tasks.send_password_setup_link_task")
    def test_cannot_retrieve_other_corporate_professional(self, mock_task):
        self._auth(self.corporate)
        other_corporate = User.objects.create_user(
            email="other_corp2@example.com",
            username="other_corp2",
            password="pass12345",
            user_type=User.Role.CORPORATE,
            is_active=True,
            status="active",
        )
        stranger = User.objects.create_user(
            email="stranger_prof@example.com",
            username="stranger_prof",
            password="pass12345",
            user_type=User.Role.PROFESSIONAL,
            is_active=True,
            status="active",
            created_by=other_corporate,
        )

        url = reverse("organization_professionals-detail", args=[stranger.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ---------- Bulk upload ----------

    @patch("user.organization_professional_views.bulk_upload_user_task")
    def test_bulk_upload_dispatches_task(self, mock_task):
        self._auth(self.corporate)
        csv_body = (
            "First Name,Last Name,Email,Phone,Referral Code,Country,State,City\n"
            "Bulk,Prof,bulk_prof@example.com,9876543211,,India,Gujarat,Ahmedabad\n"
        )
        f = SimpleUploadedFile(
            "pros.csv", csv_body.encode("utf-8"), content_type="text/csv"
        )
        url = reverse("organization_professionals-bulk-upload")
        resp = self.client.post(url, {"file": f}, format="multipart")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["success"])
        mock_task.delay.assert_called_once()
        args, kwargs = mock_task.delay.call_args
        self.assertEqual(args[0].split(".")[-1], "csv")
        self.assertEqual(args[1], self.corporate.id)
        self.assertEqual(args[2], User.Role.PROFESSIONAL)
        self.assertTrue(kwargs["skip_referral"])
        self.assertTrue(kwargs["skip_profile_fields"])
        self.assertNotIn("forced_referred_by", kwargs)

    def test_bulk_upload_missing_columns_rejected(self):
        self._auth(self.corporate)
        csv_body = "First Name,Email\n" "Bulk,bulk_bad@example.com\n"
        f = SimpleUploadedFile(
            "bad.csv", csv_body.encode("utf-8"), content_type="text/csv"
        )
        url = reverse("organization_professionals-bulk-upload")
        resp = self.client.post(url, {"file": f}, format="multipart")

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
