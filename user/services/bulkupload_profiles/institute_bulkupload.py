# user/services/bulkupload_profiles/institute_bulkupload.py

import pandas as pd
from user_profile.models import InstituteProfile


class InstituteBulkUpload:
    REQUIRED_COLUMNS = [
        "Institute Name",
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
        courses_value = row.get("Courses Offered")

        courses_offered = []
        if not pd.isna(courses_value) and str(courses_value).strip():
            courses_offered = [
                item.strip() for item in str(courses_value).split(",") if item.strip()
            ]

        return {
            "institute_name": cls.clean(row.get("Institute Name")),
            "student_trained": cls.clean_int(row.get("Student Trained")),
            "placements": cls.clean_int(row.get("Placements")),
            "about_us": cls.clean(row.get("About Us")),
            "courses_offered": courses_offered,
            "website": cls.clean(row.get("Website")),
        }

    @classmethod
    def create_profile(cls, user, profile_data):
        return InstituteProfile.objects.create(
            user=user,
            institute_name=profile_data.get("institute_name"),
            student_trained=profile_data.get("student_trained"),
            placements=profile_data.get("placements"),
            about_us=profile_data.get("about_us"),
            courses_offered=profile_data.get("courses_offered", []),
            website=profile_data.get("website"),
        )
