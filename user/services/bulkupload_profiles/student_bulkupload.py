import pandas as pd
from django.core.exceptions import ValidationError
from education_level.models import EducationLevel
from stream.models import Stream
from language_master.models import Language
from user_profile.models import StudentProfile

class StudentBulkUpload:
    REQUIRED_COLUMNS = [
    ]

    STREAM_REQUIRED_LEVEL_CODES = {
    "higher_secondary",
    "iti",
    "diploma",
    "graduation",
    "post_graduation",
    }

    VALID_MEDIUMS = [
        "english", "hindi", "gujarati", "marathi", "tamil",
        "telugu", "kannada", "bengali", "punjabi", "odia",
        "malayalam", "urdu",
    ]

    @classmethod
    def preload(cls):
        return{
            "education_levels":{
                obj.display_name.strip().lower():obj
                for obj in EducationLevel.objects.filter(is_active=True)
            },
            "streams":{
                obj.stream_code.strip().lower():obj
                for obj in Stream.objects.filter(is_active=True)
            },
            "languages":{
                obj.name.strip().lower():obj
                for obj in Language.objects.filter(deleted=False)
            },
        }
    
    @classmethod
    def validate_row(cls, row, masters):
        medium = str(row.get("Medium", "")).strip().lower()

        if medium and medium not in cls.VALID_MEDIUMS:
            raise ValidationError(
                f"Invalid medium '{medium}'. Allowed: english, hindi, gujarati, marathi, tamil, telugu, kannada, bengali, punjabi, odia, malayalam, urdu"
            )
        
        education_level = None
        education_level_code = str(row.get("Education Level", "")).strip().lower()

        if education_level_code:
            education_level = masters["education_levels"].get(education_level_code)
            if not education_level:
                raise ValidationError(
                    f"Invalid Education Level code '{row.get('Education Level')}'"
                )
            
        stream = None
        stream_value = row.get("Stream")
        stream_code = "" if pd.isna(stream_value) else str(stream_value).strip().lower()

        if(education_level_code in cls.STREAM_REQUIRED_LEVEL_CODES and not stream_code):
             raise ValidationError(f"Stream is required for education level '{education_level_code}'.")
        if stream_code:
            stream = masters["streams"].get(stream_code)
            if not stream:
                raise ValidationError(
                    f"Invalid Stream code '{row.get('Stream')}'"
                )
        languages = []
        language_value = row.get("Language")

        if not pd.isna(language_value) and str(language_value).strip():
            language_names = [
                item.strip().lower()
                for item in str(language_value).split(",")
                if item.strip()
            ]

            for lang_name in language_names:
                language = masters["languages"].get(lang_name)
                if not language:
                    raise ValidationError(f"Invalid language '{lang_name}'")

                languages.append(language)

        return {
            "medium": medium or None,
            "education_level": education_level,
            "stream": stream,
            "languages": languages,
        }
    @classmethod
    def create_profile(cls, user, profile_data):
        profile = StudentProfile.objects.create(
            user=user,
            medium=profile_data.get("medium"),
            education_level=profile_data.get("education_level"),
            stream=profile_data.get("stream"),
        )

        languages = profile_data.get("languages", [])
        if languages:
            profile.language.set(languages)

        return profile