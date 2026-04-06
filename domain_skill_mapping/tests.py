import uuid

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from domain.models import Domain
from domain_skill_mapping.models import DomainSkillMapping
from skill.models import Skill, SkillType

User = get_user_model()


class DomainSkillMappingAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="dsm_tester@example.com",
            username="dsm_tester",
            password="pass12345",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.domain = Domain.objects.create(
            domain_code="dsm_domain",
            domain_name="DSM Domain",
            parent_acceptance_level=3,
            future_relevance_score=80,
            is_active=True,
            created_by=self.user,
        )
        self.skill = Skill.objects.create(
            skill_code="dsm_skill",
            skill_name="DSM Skill",
            skill_type=SkillType.TECHNICAL,
            is_active=True,
            created_by=self.user,
        )

    def _payload(self, **extra):
        return {
            "domain": str(self.domain.pk),
            "skill": str(self.skill.pk),
            "weight_score": 85,
            "is_core": True,
            "is_active": True,
            **extra,
        }

    def test_model_constraints(self):
        obj = DomainSkillMapping.objects.create(
            domain=self.domain,
            skill=self.skill,
            weight_score=50,
            is_core=True,
            is_active=True,
            created_by=self.user,
        )
        self.assertIn("DSM Domain", str(obj))

    def test_crud_and_soft_delete(self):
        r = self.client.post(
            reverse("domain-skill-mapping-list"), self._payload(), format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        pk = r.data["data"]["id"]

        r = self.client.get(reverse("domain-skill-mapping-detail", args=[pk]))
        self.assertEqual(r.status_code, status.HTTP_200_OK)

        r = self.client.patch(
            reverse("domain-skill-mapping-detail", args=[pk]),
            {"weight_score": 91},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data["data"]["weight_score"], 91)

        r = self.client.delete(reverse("domain-skill-mapping-detail", args=[pk]))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(DomainSkillMapping.objects.get(pk=pk).deleted)

    def test_duplicate_validation(self):
        url = reverse("domain-skill-mapping-list")
        self.client.post(url, self._payload(), format="json")
        r = self.client.post(url, self._payload(), format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_search_ordering(self):
        s2 = Skill.objects.create(
            skill_code="dsm_skill_2",
            skill_name="Robotics",
            skill_type=SkillType.TECHNICAL,
            is_active=True,
            created_by=self.user,
        )
        self.client.post(
            reverse("domain-skill-mapping-list"),
            self._payload(weight_score=20),
            format="json",
        )
        self.client.post(
            reverse("domain-skill-mapping-list"),
            self._payload(skill=str(s2.pk), weight_score=99),
            format="json",
        )
        r = self.client.get(
            reverse("domain-skill-mapping-list"),
            {
                "domain": str(self.domain.pk),
                "search": "Robotics",
                "ordering": "-weight_score",
            },
        )
        payload = r.data.get("results", r.data)
        rows = payload.get("data", r.data.get("data", []))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["skill_name"], "Robotics")

    def test_dropdown_by_domain(self):
        s2 = Skill.objects.create(
            skill_code="dsm_skill_3",
            skill_name="Finance",
            skill_type=SkillType.ANALYTICAL,
            is_active=True,
            created_by=self.user,
        )
        self.client.post(
            reverse("domain-skill-mapping-list"),
            self._payload(weight_score=25),
            format="json",
        )
        self.client.post(
            reverse("domain-skill-mapping-list"),
            self._payload(skill=str(s2.pk), weight_score=88),
            format="json",
        )
        r = self.client.get(
            reverse(
                "domain-skill-mapping-by-domain",
                kwargs={"domain_id": str(self.domain.pk)},
            )
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(
            r.data["data"][0]["weight_score"], r.data["data"][1]["weight_score"]
        )

    def test_bulk_upload(self):
        s2 = Skill.objects.create(
            skill_code="dsm_skill_4",
            skill_name="Excel",
            skill_type=SkillType.ANALYTICAL,
            is_active=True,
            created_by=self.user,
        )
        csv_body = (
            "domain_code,skill_code,weight_score,is_core,is_active\n"
            f"{self.domain.domain_code},{self.skill.skill_code},80,1,1\n"
            f"{self.domain.domain_code},{s2.skill_code},not_a_number,0,1\n"
        )
        f = SimpleUploadedFile(
            "dsm.csv", csv_body.encode("utf-8"), content_type="text/csv"
        )
        r = self.client.post(
            reverse("domain-skill-mapping-bulk-import"), {"file": f}, format="multipart"
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertIn("success_count", r.data)
        self.assertIn("error_count", r.data)
        self.assertIn("error_details", r.data)

    def test_permissions(self):
        anon = APIClient()
        r = anon.get(reverse("domain-skill-mapping-list"))
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_bulk_delete_restore_and_deleted(self):
        s2 = Skill.objects.create(
            skill_code=f"dsm_skill_{uuid.uuid4().hex[:6]}",
            skill_name="Bulk Skill",
            skill_type=SkillType.SOFT,
            is_active=True,
            created_by=self.user,
        )
        p1 = self.client.post(
            reverse("domain-skill-mapping-list"),
            self._payload(weight_score=45),
            format="json",
        ).data["data"]["id"]
        p2 = self.client.post(
            reverse("domain-skill-mapping-list"),
            self._payload(skill=str(s2.pk), weight_score=55),
            format="json",
        ).data["data"]["id"]

        r = self.client.post(
            reverse("domain-skill-mapping-bulk-delete"),
            {"ids": [p1, p2]},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        r = self.client.get(reverse("domain-skill-mapping-deleted"))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        r = self.client.post(
            reverse("domain-skill-mapping-bulk-restore"), {"ids": [p1]}, format="json"
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
