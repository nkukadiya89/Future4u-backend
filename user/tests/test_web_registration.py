from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from user.services.registration_service import activate_web_user_with_temporary_password

User = get_user_model()


class WebRegistrationServiceTests(TestCase):
    @patch("user.services.registration_service.send_temporary_password_email")
    def test_activate_web_user_sets_flags(self, mock_send_email):
        user = User.objects.create(
            email="webuser@example.com",
            first_name="Web",
            last_name="User",
            user_type=User.Role.STUDENT,
        )

        activate_web_user_with_temporary_password(user)

        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.email_verified)
        self.assertTrue(user.must_change_password)
        self.assertEqual(user.status, "active")
        self.assertIsNone(user.otp)
        mock_send_email.assert_called_once()


class WebRegistrationViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("user.services.registration_service.send_registration_email")
    @patch("user.services.registration_service.send_temporary_password_email")
    def test_web_register_skips_otp(self, mock_temp_email, mock_otp_email):
        from city.models import City
        from country.models import Country
        from state.models import State

        country = Country.objects.create(name="Test Country", code="TC")
        state = State.objects.create(name="Test State", country=country)
        city = City.objects.create(name="Test City", country=country, state=state)

        payload = {
            "data": (
                '{"email":"student@example.com","first_name":"Student",'
                '"user_type":"student","country":%d,"state":%d,"city":%d,'
                '"terms_accepted":true,"source":"web"}'
            )
            % (country.id, state.id, city.id)
        }

        response = self.client.post("/auth/register/", payload, format="multipart")

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["requires_password_change"])
        mock_temp_email.assert_called_once()
        mock_otp_email.assert_not_called()

        user = User.objects.get(email="student@example.com")
        self.assertTrue(user.is_active)
        self.assertTrue(user.must_change_password)
