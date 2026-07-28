import pandas as pd
from django.core.exceptions import ValidationError

from user_profile.models import ProfessionalProfile


class WorkingProfessionalBulkUpload:
    REQUIRED_COLUMNS = []

    VALID_YEARS_OF_EXPERIENCE = [
        choice[0] for choice in ProfessionalProfile.ExperienceRange.choices
    ]

    VALID_EMPLOYMENT_TYPES = [
        choice[0] for choice in ProfessionalProfile.EmploymentType.choices
    ]

    @classmethod
    def preload(cls):
        return {}

    @classmethod
    def validate_row(cls, row, masters):
        years_of_experience = None
        yoe_value = row.get("Years of Experience")
        if not pd.isna(yoe_value) and str(yoe_value).strip():
            yoe_str = str(yoe_value).strip()
            if yoe_str not in cls.VALID_YEARS_OF_EXPERIENCE:
                raise ValidationError(
                    f"Invalid Years of Experience '{yoe_str}'. "
                    f"Allowed: {', '.join(cls.VALID_YEARS_OF_EXPERIENCE)}"
                )
            years_of_experience = yoe_str

        employment_type = None
        et_value = row.get("Employment Type")
        if not pd.isna(et_value) and str(et_value).strip():
            et_str = str(et_value).strip()
            if et_str not in cls.VALID_EMPLOYMENT_TYPES:
                raise ValidationError(
                    f"Invalid Employment Type '{et_str}'. "
                    f"Allowed: {', '.join(cls.VALID_EMPLOYMENT_TYPES)}"
                )
            employment_type = et_str

        return {
            "years_of_experience": years_of_experience,
            "employment_type": employment_type,
        }

    @classmethod
    def create_profile(cls, user, profile_data):
        return ProfessionalProfile.objects.create(
            user=user,
            years_of_experience=profile_data.get("years_of_experience"),
            employment_type=profile_data.get("employment_type"),
            referred_by=profile_data.get("referred_by"),
        )
