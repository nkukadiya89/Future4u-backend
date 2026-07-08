import pandas as pd
from django.db import transaction
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from country.models import Country
from state.models import State
from city.models import City
from user.models import User
from user.services.registration_service import setup_web_user_password
from user.services.bulkupload_profiles.student_bulkupload import StudentBulkUpload
from user.services.bulkupload_profiles.school_colleges_bulkupload import SchoolCollegeBulkUpload
from user.services.bulkupload_profiles.institute_bulkupload import InstituteBulkUpload
from user.services.bulkupload_profiles.corporate_bulkupload import CorporateBulkUpload
from user.services.bulkupload_profiles.working_professional_bulkupload import WorkingProfessionalBulkUpload

class BulkUserUploadService:
    REQUIRED_COLUMNS = [
        "First Name",
        "Last Name",
        "Email",
        "Phone",
        "Referral Code",
        "Country",
        "State",
        "City",
    ]
    @classmethod
    def get_required_columns(cls, user_type):
        required_columns = cls.REQUIRED_COLUMNS.copy()

        if user_type == User.Role.STUDENT:
            required_columns += StudentBulkUpload.REQUIRED_COLUMNS

        elif user_type == User.Role.SCHOOL_COLLEGE:
            required_columns += SchoolCollegeBulkUpload.REQUIRED_COLUMNS

        elif user_type == User.Role.INSTITUTE:
            required_columns += InstituteBulkUpload.REQUIRED_COLUMNS
        
        elif user_type == User.Role.CORPORATE:
            required_columns += CorporateBulkUpload.REQUIRED_COLUMNS

        elif user_type == User.Role.PROFESSIONAL:
            required_columns += WorkingProfessionalBulkUpload.REQUIRED_COLUMNS

        return required_columns
    
    @classmethod
    def process(cls, file, request_user, user_type):
        df = cls._read_file(file)

        valid_roles = [role.value for role in User.Role]
        if user_type not in valid_roles:
            raise ValidationError(
                f"Invalid user_type. Allowed: {', '.join(valid_roles)}"
            )
        required_columns = cls.get_required_columns(user_type)

        profile_service = None
        profile_masters = {}

        if user_type == User.Role.STUDENT:
            profile_service = StudentBulkUpload
            profile_masters = StudentBulkUpload.preload()

        elif user_type == User.Role.SCHOOL_COLLEGE:
            profile_service = SchoolCollegeBulkUpload
            profile_masters = SchoolCollegeBulkUpload.preload()
        
        elif user_type == User.Role.INSTITUTE:
            profile_service = InstituteBulkUpload
            profile_masters = InstituteBulkUpload.preload()
            
        elif user_type == User.Role.CORPORATE:
            profile_service = CorporateBulkUpload
            profile_masters = CorporateBulkUpload.preload()

        elif user_type == User.Role.PROFESSIONAL:
            profile_service = WorkingProfessionalBulkUpload
            profile_masters = WorkingProfessionalBulkUpload.preload()

        cls._validate_headers(df, required_columns)

        total_records = len(df)
        inserted = 0
        failed = 0
        skipped = 0

        errors = []

        seen_emails = set()
        seen_phones = set()

        countries = {
            c.name.strip().lower(): c for c in Country.objects.all()
        }
        states = {
            (s.country_id, s.name.strip().lower()): s for s in State.objects.all()
        }
        cities = {
            (c.state_id, c.name.strip().lower()): c for c in City.objects.all()
        }
        all_state_names = {name for (_, name) in states.keys()}
        all_city_names = {name for (_, name) in cities.keys()}

        existing_emails = {
            email.lower()
            for email in User.objects.filter(deleted=False).values_list("email", flat=True)
            if email
        }
        existing_phones = set(
            User.objects.filter(deleted=False)
            .exclude(phone__isnull=True)
            .exclude(phone="")
            .values_list("phone", flat=True)
        )

        for index, row in df.iterrows():
            row_number = int(index) + 2

            try:
                email = str(row.get("Email", "")).strip().lower()
                phone = str(row.get("Phone", "")).strip()

                if email:
                    if email in seen_emails:
                        skipped += 1
                        continue
                    seen_emails.add(email)

                if phone:
                    if phone in seen_phones:
                        skipped += 1
                        continue
                    seen_phones.add(phone)

                required_fields = {
                    "First Name": row.get("First Name"),
                    "Email": row.get("Email"),
                    "Country": row.get("Country"),
                    "State": row.get("State"),
                    "City": row.get("City"),
                    "Phone": row.get("Phone"),
                }
                missing_fields = []

                for field, value in required_fields.items():
                    if pd.isna(value) or str(value).strip() == "":
                        missing_fields.append(field)

                if missing_fields:
                    failed += 1
                    errors.append(
                        {
                            "row": row_number,
                            "email": email,
                            "message": f"Missing required fields: {', '.join(missing_fields)}",
                        }
                    )
                    continue

                try:
                    validate_email(email)
                except ValidationError:
                    failed += 1
                    errors.append(
                        {
                            "row": row_number,
                            "email": email,
                            "message": "Invalid email format",
                        }
                    )
                    continue

                if not phone.isdigit():
                    failed += 1
                    errors.append(
                        {
                            "row": row_number,
                            "email": email,
                            "message": "Phone must contain only digits",
                        }
                    )
                    continue

                if len(phone) < 10 or len(phone) > 15:
                    failed += 1
                    errors.append(
                        {
                            "row": row_number,
                            "email": email,
                            "message": "Phone must be between 10 and 15 digits",
                        }
                    )
                    continue

                if email in existing_emails:
                    skipped += 1
                    continue

                if phone in existing_phones:
                    skipped += 1
                    continue

                country_name = str(row["Country"]).strip().lower()
                country = countries.get(country_name)

                if not country:
                    failed += 1
                    errors.append(
                        {
                            "row": row_number,
                            "email": email,
                            "message": f"Country '{row['Country']}' does not exist.",
                        }
                    )
                    continue

                state_name = str(row["State"]).strip().lower()
                state = states.get((country.id, state_name))

                if not state:
                    failed += 1
                    state_exists = state_name in all_state_names
                    if state_exists:
                        message = (
                            f"State '{row['State']}' does not belong to "
                            f"country '{row['Country']}'"
                        )
                    else:
                        message = f"State '{row['State']}' does not exists."

                    errors.append(
                        {
                            "row": row_number,
                            "email": email,
                            "message": message,
                        }
                    )
                    continue

                city_name = str(row["City"]).strip().lower()
                city = cities.get((state.id, city_name))

                if not city:
                    failed += 1
                    city_exists = city_name in all_city_names

                    if city_exists:
                        message = (
                            f"City '{row['City']}' does not belong to "
                            f"state '{row['State']}'"
                        )
                    else:
                        message = f"City '{row['City']}' does not exist."

                    errors.append(
                        {
                            "row": row_number,
                            "email": email,
                            "message": message,
                        }
                    )
                    continue
                profile_data = {}
                if profile_service:
                    profile_data = profile_service.validate_row(row, profile_masters)

                referral_code = str(row.get("Referral Code", "") or "").strip()
                referred_by = None
                if user_type in [User.Role.STUDENT, User.Role.PROFESSIONAL] and referral_code:
                    referred_by = User.objects.filter(
                        referral_code__iexact = referral_code,
                        user_type__in = [
                            User.Role.SCHOOL_COLLEGE,
                            User.Role.INSTITUTE,
                            User.Role.CORPORATE,
                        ],
                        deleted=False,
                    ).first()
                    if not referred_by:
                        failed += 1
                        errors.append(
                            {
                                "row": row_number,
                                "email": email,
                                "message": "Invalid referral code.",
                            }
                        )
                        continue
                if user_type in [User.Role.STUDENT, User.Role.PROFESSIONAL]:
                    profile_data["referred_by"] = referred_by
                with transaction.atomic():
                    user = User.objects.create(
                        first_name=str(row.get("First Name", "")).strip(),
                        last_name=str(row.get("Last Name", "")).strip(),
                        about_me=str(row.get("About Me", "")).strip(),
                        email=email,
                        phone=phone,
                        user_type=user_type,
                        referral_code = referral_code if user_type in [
                            User.Role.SCHOOL_COLLEGE,
                            User.Role.INSTITUTE,
                            User.Role.CORPORATE,
                        ] else None,
                        country=country,
                        states=state,
                        city=city,
                        address=str(row.get("Address", "")).strip() or None,
                        created_by=request_user,
                        terms_accepted=True,
                    )

                    if profile_service:
                        profile_service.create_profile(user, profile_data)

                    setup_web_user_password(user)

                    existing_emails.add(email)
                    existing_phones.add(phone)
                    inserted += 1

            except Exception as e:
                failed += 1
                errors.append(
                    {
                        "row": row_number,
                        "email": email if "email" in locals() else None,
                        "message": str(e),
                    }
                )

        return {
            "total_records": int(total_records),
            "inserted": inserted,
            "failed": failed,
            "skipped": skipped,
            "errors": errors,
        }
    @classmethod
    def process_file_path(cls, file_path, request_user, user_type):
        with open(file_path, "rb") as file:
            return cls.process(file, request_user,user_type)

    @classmethod
    def _read_file(cls, file):
        filename = file.name.lower()
        try:
            if filename.endswith(".csv"):
                return pd.read_csv(file)

            if filename.endswith((".xlsx", ".xls")):
                return pd.read_excel(file)
        except Exception:
            raise ValidationError(
                "Unsupported file type. Only CSV, XLS and XLSX are allowed."
            )
        raise ValidationError("Only CSV, XLS and XLSX files are allowed.")

    @classmethod
    def _validate_headers(cls, df, required_columns=None):
        required_columns = required_columns or cls.REQUIRED_COLUMNS
        uploaded_columns = [col.strip() for col in df.columns]

        missing_columns = [
            column
            for column in required_columns
            if column not in uploaded_columns
        ]

        if missing_columns:
            raise ValidationError(
                f"Missing required columns: {', '.join(missing_columns)}"
            )

