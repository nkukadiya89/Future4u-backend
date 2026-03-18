import json
import re
from datetime import date

from decouple import config
from django.contrib.auth import logout
from django.http import JsonResponse


class PasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.user.is_authenticated:
            company_id = request.user.company.id
            if company_id:
                today_date = date.today()

                password_last_changed = request.user.password_last_changed.date()
                days_since_password_changed = (today_date - password_last_changed).days

                password_expired = days_since_password_changed > int(
                    config("PASSWORD_CHANGE_DUE_DAYS")
                )
                if password_expired:
                    logout(request)
                    response_data = {
                        "message": "Your Password is Expired, "
                        "Need to Change Your Password"
                    }
                    return JsonResponse(response_data, status=200)

        return response


class TitleCaseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if "application/json" in response.get("Content-Type", ""):
            try:
                data = json.loads(response.content.decode("utf-8"))
                self.capitalize_values(data)

                response.content = json.dumps(data).encode("utf-8")
                response["Content-Length"] = len(response.content)
            except ValueError:
                # Handle the case where response is not JSON serializable
                pass

        return response

    def capitalize_values(self, data):
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str):
                    # Capitalize words that do not contain special characters
                    data[key] = " ".join(
                        word.capitalize() if re.match(r"^[A-Za-z]+$", word) else word
                        for word in value.split()
                    )
                elif isinstance(value, (dict, list)):
                    # Recursively capitalize values of nested dictionaries and lists
                    self.capitalize_values(value)

        elif isinstance(data, list):
            for item in data:
                # Recursively capitalize values of list items
                self.capitalize_values(item)
