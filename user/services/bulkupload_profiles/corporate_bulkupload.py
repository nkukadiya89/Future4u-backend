import pandas as pd
from user_profile.models import CorporateProfile


class CorporateBulkUpload:
    REQUIRED_COLUMNS = [
        "Company Name",
    ]

    @classmethod
    def preload(cls):
        return {}

    @staticmethod
    def clean(value):
        if pd.isna(value):
            return None

        value = str(value).strip()
        return value or None

    @staticmethod
    def clean_int(value):
        if pd.isna(value) or str(value).strip() == "":
            return None

        return int(value)

    @classmethod
    def validate_row(cls, row, masters):
        return {
            "company_name": cls.clean(row.get("Company Name")),
            "open_job": cls.clean_int(row.get("Open Job")),
            "employees": cls.clean_int(row.get("Employees")),
            "years_in_business": cls.clean_int(
                row.get("Years In Business")
            ),
            "about_us": cls.clean(row.get("About Us")),
            "website": cls.clean(row.get("Website")),
        }

    @classmethod
    def create_profile(cls, user, profile_data):
        return CorporateProfile.objects.create(
            user=user,
            company_name=profile_data.get("company_name"),
            open_job=profile_data.get("open_job"),
            employees=profile_data.get("employees"),
            years_in_business=profile_data.get(
                "years_in_business"
            ),
            about_us=profile_data.get("about_us"),
            website=profile_data.get("website"),
        )