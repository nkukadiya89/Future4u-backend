import pandas as pd
from django.core.exceptions import ValidationError

from user_profile.models import SchoolCollegeProfile


class SchoolCollegeBulkUpload:
    REQUIRED_COLUMNS = ["Institute Name"]

    @classmethod
    def preload(cls):
        return {}

    @staticmethod
    def clean(value):
        if pd.isna(value):
            return None

        value = str(value).strip()
        return value or None

    @classmethod
    def validate_row(cls, row, masters):
        courses_value = row.get("Courses Offered")

        courses_offered = []
        if not pd.isna(courses_value) and str(courses_value).strip():
            courses_offered = [
                item.strip() for item in str(courses_value).split(",") if item.strip()
            ]

        return {
            "institute_name": cls.clean(row.get("Institute Name")),
            "board": cls.clean(row.get("Board")),
            "about_us": cls.clean(row.get("About Us")),
            "courses_offered": courses_offered,
            "website": cls.clean(row.get("Website")),
        }

    @classmethod
    def create_profile(cls, user, profile_data):
        return SchoolCollegeProfile.objects.create(
            user=user,
            institute_name=profile_data.get("institute_name"),
            board=profile_data.get("board"),
            about_us=profile_data.get("about_us"),
            courses_offered=profile_data.get("courses_offered", []),
            website=profile_data.get("website"),
        )
