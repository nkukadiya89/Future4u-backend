from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from user.models import CustomGroup, RoleFamily

User = get_user_model()


class GroupPermissionsAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="testuser@example.com",
            username="testuser",
            password="testpass",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.role_family = RoleFamily.objects.create(
            family_name="School",
            created_by=self.user,
            updated_by=self.user,
        )

        self.group = CustomGroup.objects.create(
            name="Teacher",
            group_name="Teacher",
            role_family=self.role_family,
            created_by=self.user,
        )

        self.permission = Permission.objects.filter(content_type_id__gt=5).first()
        if self.permission:
            self.group.permissions.add(self.permission)

    def test_get_role_permissions_response_shape(self):
        url = reverse("get_group_permission-list") + "get-role-permissions/"
        response = self.client.get(url, {"group_id": self.group.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("response", response.data)
        self.assertIn("user_group_permissions", response.data["response"])

        group_permissions = response.data["response"]["user_group_permissions"]
        self.assertIsInstance(group_permissions, list)
        self.assertEqual(len(group_permissions), 1)

        item = group_permissions[0]
        self.assertEqual(item["group_id"], self.group.id)
        self.assertEqual(item["group_role_family"], "School")
        self.assertEqual(item["group_name"], "Teacher")
        self.assertIn("permissions", item)

        permissions = item["permissions"]
        self.assertIsInstance(permissions, list)
        if self.permission:
            self.assertEqual(permissions[0]["permission_id"], self.permission.id)
            self.assertEqual(permissions[0]["is_checked"], True)
