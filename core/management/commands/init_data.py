import csv
from os import path

from decouple import config
from django.conf import settings
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils.timezone import now

from business_category.models import BusinessCategory
from career.serializers import CareerSerializer
from career.services import career_service
from city.models import City
from country.models import Country
from domain.serializers import DomainSerializer
from domain.services import domain_service
from domain_career_mapping.serializers import DomainCareerMappingSerializer
from domain_career_mapping.services import domain_career_mapping_service
from domain_skill_mapping.serializers import DomainSkillMappingSerializer
from domain_skill_mapping.services import domain_skill_mapping_service
from education_level.serializers import EducationLevelSerializer
from education_level.services import education_level_service
from language_master.serializers import LanguageSerializer
from language_master.services import language_service
from skill.serializers import SkillSerializer
from skill.services import skill_service
from state.models import State
from stream.serializers import StreamSerializer
from stream.services import stream_service
from stream_domain_mapping.serializers import StreamDomainMappingSerializer
from stream_domain_mapping.services import stream_domain_mapping_service
from subscription.models import Subscription, SubscriptionFeature
from user.models import CustomGroup, RoleFamily, User

try:
    from city_areas.models import CityArea  # type: ignore
except Exception:  # pragma: no cover
    CityArea = None  # type: ignore


class Command(BaseCommand):
    help = "Load country data into country database"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--country", type=bool, help="Country data to be uploaded")
        parser.add_argument(
            "--zone_name", type=bool, help="ZoneName data to be uploaded"
        )
        parser.add_argument(
            "--domain", type=bool, help="Domain master data to be uploaded"
        )
        parser.add_argument(
            "--education_level", type=bool, help="Education level data to be uploaded"
        )
        parser.add_argument(
            "--skill", type=bool, help="Skill master data to be uploaded"
        )
        parser.add_argument(
            "--career", type=bool, help="Career master data to be uploaded"
        )
        parser.add_argument(
            "--assessment", type=bool, help="Assessment questions/options to be seeded"
        )

        parser.add_argument("--groups", type=bool, help="Create Groups")
        parser.add_argument("--user", type=bool, help="Create Super User")
        parser.add_argument(
            "--subscription", type=bool, help="Subscription plans data to be seeded"
        )

    def handle(self, *args, **kwargs):
        self.stdout.write("Initialise..")
        if kwargs["subscription"]:
            self.load_subscription()
            return

        # Handle specific flags
        if kwargs["groups"]:
            admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
            self.create_custom_groups(admin_user=admin_user)
            return

        if kwargs["user"]:
            self.create_super_user()
            return

        if kwargs["country"]:
            self.load_country()
            self.load_state()
            self.load_city()
            if CityArea is not None:
                self.load_city_area()
            return

        if kwargs["zone_name"]:
            self.load_state()
            return

        if kwargs["domain"]:
            self.load_domain_master()
            return

        if kwargs["education_level"]:
            self.load_education_levels()
            return

        if kwargs["skill"]:
            self.load_skills()
            return

        if kwargs["career"]:
            self.load_careers()
            return

        if kwargs["assessment"]:
            self.load_assessment_questions()
            return

        # If no specific flags, run all initialization
        if (
            kwargs["country"] is None
            and kwargs["zone_name"] is None
            and kwargs["domain"] is None
            and kwargs["education_level"] is None
            and kwargs["skill"] is None
            and kwargs["career"] is None
            and kwargs["assessment"] is None
            and kwargs["groups"] is None
            and kwargs["user"] is None
            and kwargs["subscription"] is None
        ):
            self.load_business_category()
            admin_user = self.create_super_user()
            self.create_custom_groups(admin_user=admin_user)
            self.create_role_family(admin_user=admin_user)
            self.load_country(admin_user=admin_user)
            self.load_state(admin_user=admin_user)
            self.load_city(admin_user=admin_user)
            if CityArea is not None:
                self.load_city_area()
            self.load_domain_master()
            self.load_education_levels()
            self.load_skills()
            self.load_careers()
            self.load_streams()
            self.load_stream_domain_mappings()
            self.load_domain_skill_mappings()
            self.load_domain_career_mappings()
            self.load_assessment_questions()
            self.load_domain_report_meta()
            self.load_stream_report_meta()
            self.load_domain_counsellor_knowledge()
            self.load_stream_counsellor_knowledge()
            self.load_domain_scoring_config()
            self.load_language_master()
            self.load_subscription()  # TODO: fix field mismatch with current Subscription model

    # Super User Create
    def create_super_user(self):
        self.stdout.write("Creating Super User.......")
        init_email = config("INIT_EMAIL")
        defaults = dict(
            is_superuser=True,
            is_staff=True,
            is_active=True,
            username="Future4uAdmin",
            first_name="Future4u",
            last_name="Admin",
            about_me="Admin",
            profile_image=None,
            designation="Super Admin",
            phone="9639639630",
            user_type=User.Role.SUPER_ADMIN,
            status="active",
            email_verified=True,
            terms_accepted=True,
        )
        user, created = User.objects.get_or_create(email=init_email, defaults=defaults)
        if not created:
            for k, v in defaults.items():
                setattr(user, k, v)
        new_password = config("INIT_ADMIN_PASSWORD")
        user.set_password(new_password)

        user.save()
        if created:
            self.stdout.write("Super User Created!.......")
        else:
            self.stdout.write("Super User already exists, updated profile/password.")
        return user

    # Role Family Create
    role_family_data = [
        {
            "family_name": "Future4U Family",
            "created_by": 1,
            "updated_by": 1,
        },
        {
            "family_name": "Partner Company Family",
            "created_by": 1,
            "updated_by": 1,
        },
        {
            "family_name": "Ads Agency Family",
            "created_by": 1,
            "updated_by": 1,
        },
        {
            "family_name": "EndClient Family",
            "created_by": 1,
            "updated_by": 1,
        },
    ]

    def create_role_family(self, admin_user=None):
        self.stdout.write("Creating Role Family...........")
        created_by_user = (
            admin_user
            or User.objects.filter(is_superuser=True).first()
            or User.objects.first()
        )
        if not created_by_user:
            self.stdout.write(
                self.style.WARNING("Skipping role family creation: no user found")
            )
            return []
        role_family = []

        for data in self.role_family_data:
            roles_family, created = RoleFamily.objects.update_or_create(
                family_name=data["family_name"],
                defaults={
                    "created_by": created_by_user,
                    "updated_by": created_by_user,
                },
            )
            role_family.append(roles_family)
        return role_family

    def create_custom_groups(self, admin_user=None):
        self.stdout.write("Creating Groups.......")
        user = (
            admin_user
            or User.objects.filter(is_superuser=True).first()
            or User.objects.first()
        )
        if not user:
            self.stdout.write(
                self.style.WARNING("Skipping group creation: no user found")
            )
            return

        # Create groups for each Role type
        super_admin_group, _ = CustomGroup.objects.update_or_create(
            name="Super Admin",
            defaults={"group_name": "Super Admin", "created_by": user},
        )
        student_group, _ = CustomGroup.objects.update_or_create(
            name="Student",
            defaults={"group_name": "Student", "created_by": user},
        )
        parent_group, _ = CustomGroup.objects.update_or_create(
            name="Parent",
            defaults={"group_name": "Parent", "created_by": user},
        )
        professional_group, _ = CustomGroup.objects.update_or_create(
            name="Professional",
            defaults={"group_name": "Professional", "created_by": user},
        )
        school_college_group, _ = CustomGroup.objects.update_or_create(
            name="School College",
            defaults={"group_name": "School College", "created_by": user},
        )
        institute_group, _ = CustomGroup.objects.update_or_create(
            name="Institute",
            defaults={"group_name": "Institute", "created_by": user},
        )
        corporate_group, _ = CustomGroup.objects.update_or_create(
            name="Corporate",
            defaults={"group_name": "Corporate", "created_by": user},
        )

        self.stdout.write("Custom Groups Created!.......")

        # Super Admin Permissions - Full system access
        super_admin_permissions = [
            "activity_log|Can view activity log",
            "business_category|Can add business category",
            "business_category|Can change business category",
            "business_category|Can delete business category",
            "business_category|Can view business category",
            "city|Can add city",
            "city|Can change city",
            "city|Can delete city",
            "city|Can view city",
            "city_areas|Can add city area",
            "city_areas|Can change city area",
            "city_areas|Can delete city area",
            "city_areas|Can view city area",
            "company|Can add company",
            "company|Can change company",
            "company|Can delete company",
            "company|Can view company",
            "country|Can add country",
            "country|Can change country",
            "country|Can delete country",
            "country|Can view country",
            "domain|Can add domain",
            "domain|Can change domain",
            "domain|Can delete domain",
            "domain|Can view domain",
            "education_level|Can add education level",
            "education_level|Can change education level",
            "education_level|Can delete education level",
            "education_level|Can view education level",
            "faq|Can add faq",
            "faq|Can change faq",
            "faq|Can delete faq",
            "faq|Can view faq",
            "skill|Can add skill",
            "skill|Can change skill",
            "skill|Can delete skill",
            "skill|Can view skill",
            "career|Can add career",
            "career|Can change career",
            "career|Can delete career",
            "career|Can view career",
            "state|Can add state",
            "state|Can change state",
            "state|Can delete state",
            "state|Can view state",
            "stream|Can add stream",
            "stream|Can change stream",
            "stream|Can delete stream",
            "stream|Can view stream",
            "subscription|Can add subscription",
            "subscription|Can change subscription",
            "subscription|Can delete subscription",
            "subscription|Can view subscription",
            "subscription|Can add subscription feature",
            "subscription|Can change subscription feature",
            "subscription|Can delete subscription feature",
            "subscription|Can view subscription feature",
            "user|Can add custom group",
            "user|Can change auth group permissions model",
            "user|Can change custom group",
            "user|Can change user",
            "user|Can delete auth group permissions model",
            "user|Can delete custom group",
            "user|Can view auth group permissions model",
            "user|Can view custom group",
            "user|Can view user",
            "user_profile|Can change business setting",
            "user_profile|Can view business setting",
            "assessment|Can add assessment",
            "assessment|Can change assessment",
            "assessment|Can delete assessment",
            "assessment|Can view assessment",
        ]

        # Student Permissions - View own data, assessments, recommendations
        student_permissions = [
            "assessment|Can view assessment",
            "career|Can view career",
            "domain|Can view domain",
            "education_level|Can view education level",
            "skill|Can view skill",
            "stream|Can view stream",
            "user|Can view user",
        ]

        # Parent Permissions - View linked child's data
        parent_permissions = [
            "assessment|Can view assessment",
            "career|Can view career",
            "domain|Can view domain",
            "education_level|Can view education level",
            "skill|Can view skill",
            "stream|Can view stream",
            "user|Can view user",
        ]

        # Professional Permissions - View career resources, update own profile
        professional_permissions = [
            "assessment|Can view assessment",
            "career|Can view career",
            "domain|Can view domain",
            "education_level|Can view education level",
            "skill|Can view skill",
            "stream|Can view stream",
            "user|Can change user",
            "user|Can view user",
        ]

        # School/College Permissions - Manage their students
        school_college_permissions = [
            "assessment|Can view assessment",
            "career|Can view career",
            "domain|Can view domain",
            "education_level|Can view education level",
            "skill|Can view skill",
            "stream|Can view stream",
            "user|Can view user",
        ]

        # Institute Permissions - Manage courses, grade students
        institute_permissions = [
            "assessment|Can add assessment",
            "assessment|Can change assessment",
            "assessment|Can view assessment",
            "career|Can view career",
            "domain|Can view domain",
            "education_level|Can view education level",
            "skill|Can view skill",
            "stream|Can view stream",
            "user|Can view user",
        ]

        # Corporate Permissions - Post jobs, view candidates
        corporate_permissions = [
            "assessment|Can view assessment",
            "career|Can view career",
            "domain|Can view domain",
            "education_level|Can view education level",
            "skill|Can view skill",
            "stream|Can view stream",
            "user|Can view user",
        ]

        # Assign superuser to Super Admin group
        assign_group_super_admin = CustomGroup.objects.get(name="Super Admin")
        assign_group_super_admin.user_set.add(user)

        # Assign permissions to groups
        self.assign_permissions(super_admin_group, super_admin_permissions)
        self.assign_permissions(student_group, student_permissions)
        self.assign_permissions(parent_group, parent_permissions)
        self.assign_permissions(professional_group, professional_permissions)
        self.assign_permissions(school_college_group, school_college_permissions)
        self.assign_permissions(institute_group, institute_permissions)
        self.assign_permissions(corporate_group, corporate_permissions)

    def assign_permissions(self, group, permissions):
        for permission_name in permissions:
            try:
                app_label, codename = permission_name.split("|")
                permission_obj = Permission.objects.get(
                    content_type__app_label=app_label,
                    name=codename,
                )
                group.permissions.add(permission_obj)
                self.stdout.write(
                    f"Assigned {app_label and codename} permission to {group.name} group"
                )
            except Permission.DoesNotExist:
                self.stdout.write(
                    (
                        f"Permission {permission_name} does not exist. "
                        f"Skipping assignment to {group.name} group"
                    )
                )
            except Permission.MultipleObjectsReturned:
                self.stdout.write(
                    (
                        f"Multiple permissions with the name {permission_name} exist. "
                        f"Skipping assignment to {group.name} group"
                    )
                )

    def load_business_category(self):
        self.stdout.write("Loading Business Category...")
        file_path = path.join(
            settings.BASE_DIR, "core", "management", "source", "business_categorys.csv"
        )
        with open(file_path, "r", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=",")
            BusinessCategory.objects.bulk_create(
                [
                    BusinessCategory(business_category=row["business_category"])
                    for row in reader
                ],
                ignore_conflicts=True,
            )
        self.stdout.write("Business Category data uploaded.")

    # Country Upload CSV
    def load_country(self, admin_user=None):
        self.stdout.write("Loading Country...")
        created_by_user = admin_user or User.objects.filter(is_superuser=True).first()
        file_path = path.join(
            settings.BASE_DIR, "core", "management", "source", "countrie.csv"
        )
        with open(file_path, "r", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=",")
            Country.objects.bulk_create(
                [
                    Country(
                        name=row["name"],
                        code=row["code"],
                        unicode=row["unicode"],
                        country_flag=row["flag"],
                        phone_code=row["phone_code"],
                        created_by=created_by_user,
                    )
                    for row in reader
                ],
                ignore_conflicts=True,
            )
        self.stdout.write("Country data uploaded.")

    # State Upload CSV
    def load_state(self, admin_user=None):
        self.stdout.write("Loading State...")
        created_by_user = admin_user or User.objects.filter(is_superuser=True).first()
        file_path = path.join(
            settings.BASE_DIR, "core", "management", "source", "state.csv"
        )
        with open(file_path, "r", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=",")
            states_to_create = []
            for row in reader:
                try:
                    country = Country.objects.get(name=row["country_name"])
                    states_to_create.append(
                        State(
                            name=row["name"],
                            country_id=country.id,
                            created_by=created_by_user,
                        )
                    )
                except Country.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f"Country not found: {row['country_name']}")
                    )
                    continue
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error processing state {row['name']}: {str(e)}"
                        )
                    )
                    continue

            if states_to_create:
                State.objects.bulk_create(states_to_create, ignore_conflicts=True)
        self.stdout.write("State data uploaded successfully.")

    # City Upload CSV
    def load_city(self, admin_user=None):
        self.stdout.write("Loading City....")
        created_by_user = admin_user or User.objects.filter(is_superuser=True).first()
        file_path = path.join(
            settings.BASE_DIR, "core", "management", "source", "city.csv"
        )

        states = {}
        for state in State.objects.select_related("country").all():
            key = f"{state.name.lower()}_{state.country.name.lower()}"
            states[key] = state

        cities_to_create = []

        with open(file_path, "r", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=",")

            for row in reader:
                try:
                    state_name = row["state_name"].strip().lower()
                    country_name = row["country_name"].strip().lower()
                    state_key = f"{state_name}_{country_name}"

                    state = states.get(state_key)

                    if not state:
                        continue

                    cities_to_create.append(
                        City(
                            name=row["name"].strip(),
                            state=state,
                            country=state.country,
                            created_by=created_by_user,
                        )
                    )

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error processing city '{row.get('name', 'Unknown')}': {str(e)}"
                        )
                    )
                    continue

        if cities_to_create:
            City.objects.bulk_create(cities_to_create, ignore_conflicts=True)

        self.stdout.write("City data uploaded successfully.")

    # City Area Upload CSV
    def load_city_area(self):
        if CityArea is None:
            self.stdout.write(
                self.style.WARNING("Skipping city area load: 'city_areas' app removed")
            )
            return
        self.stdout.write("Loading City Area....")
        file_path = path.join(
            settings.BASE_DIR, "core", "management", "source", "city_area.csv"
        )

        cities = {}
        for city in City.objects.select_related("state", "state__country").all():
            key = f"{city.name.lower()}_{city.state.name.lower()}_{city.state.country.name.lower()}"
            cities[key] = city

        city_areas_to_create = []

        with open(file_path, "r", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=",")

            for row in reader:
                try:
                    city_name = row["city_name"].strip().lower()
                    state_name = row["state_name"].strip().lower()
                    country_name = row["country_name"].strip().lower()
                    city_key = f"{city_name}_{state_name}_{country_name}"

                    city = cities.get(city_key)

                    if not city:
                        continue

                    city_areas_to_create.append(
                        CityArea(
                            country_id=city.state.country.id,
                            state_id=city.state.id,
                            city_id=city.id,
                            city_area_name=row["city_area"].strip(),
                            zipcode=row["zipcode"].strip(),
                            created_by=User.objects.get(id=row["created_by"]),
                        )
                    )

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error processing city area '{row.get('city_area', 'Unknown')}': {str(e)}"
                        )
                    )
                    continue

        if city_areas_to_create:
            CityArea.objects.bulk_create(city_areas_to_create, ignore_conflicts=True)

        self.stdout.write("City Area data uploaded successfully.")

    class _Req:
        __slots__ = ("user",)

        def __init__(self, user):
            self.user = user

    def _bulk_import_from_csv(self, *, file_path, serializer_class, importer):
        rows = []
        with open(file_path, "r", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=",")
            for row in reader:
                if not any((v or "").strip() for v in row.values()):
                    continue
                rows.append(dict(row))
        if not rows:
            self.stdout.write(self.style.WARNING(f"No rows found in {file_path}"))
            return
        user = (
            User.objects.filter(is_superuser=True).first()
            or User.objects.order_by("pk").first()
        )
        if not user:
            self.stdout.write(
                self.style.WARNING(
                    "Skipping import: no user available for audit fields"
                )
            )
            return
        result = importer(
            user=user,
            rows=rows,
            serializer_class=serializer_class,
            context={"request": self._Req(user)},
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Load complete ({path.basename(file_path)}): "
                f"success={result['success_count']} errors={result['error_count']}"
            )
        )

    def load_domain_master(self):
        self.stdout.write("Loading Domain Master...")
        file_path = path.join(
            settings.BASE_DIR,
            "core",
            "management",
            "source",
            "domain_master_sample.csv",
        )
        self._bulk_import_from_csv(
            file_path=file_path,
            serializer_class=DomainSerializer,
            importer=domain_service.bulk_import_domains,
        )

    def load_education_levels(self):
        self.stdout.write("Loading Education Levels...")
        file_path = path.join(
            settings.BASE_DIR,
            "core",
            "management",
            "source",
            "education_level_master_sample.csv",
        )
        self._bulk_import_from_csv(
            file_path=file_path,
            serializer_class=EducationLevelSerializer,
            importer=education_level_service.bulk_import_levels,
        )
        # Seed fallback messages and next steps from the same CSV
        from core.management.commands._master_import_utils import load_csv_rows
        from education_level.models import EducationLevel

        for row in load_csv_rows(file_path):
            code = (row.get("level_code") or "").strip().lower()
            if not code:
                continue
            EducationLevel.objects.filter(level_code=code).update(
                fallback_insight=(row.get("fallback_insight") or "").strip(),
                fallback_action=(row.get("fallback_action") or "").strip(),
                next_step_1=(row.get("next_step_1") or "").strip(),
                next_step_2=(row.get("next_step_2") or "").strip(),
                next_step_3=(row.get("next_step_3") or "").strip(),
            )

    def load_streams(self):
        self.stdout.write("Loading Streams...")
        file_path = path.join(
            settings.BASE_DIR,
            "core",
            "management",
            "source",
            "stream_master_sample.csv",
        )
        self._bulk_import_from_csv(
            file_path=file_path,
            serializer_class=StreamSerializer,
            importer=stream_service.bulk_import_streams,
        )

    def load_skills(self):
        self.stdout.write("Loading Skills...")
        file_path = path.join(
            settings.BASE_DIR, "core", "management", "source", "skill_master_sample.csv"
        )
        self._bulk_import_from_csv(
            file_path=file_path,
            serializer_class=SkillSerializer,
            importer=skill_service.bulk_import_skills,
        )

    def load_careers(self):
        self.stdout.write("Loading Careers...")
        file_path = path.join(
            settings.BASE_DIR,
            "core",
            "management",
            "source",
            "career_master_sample.csv",
        )
        self._bulk_import_from_csv(
            file_path=file_path,
            serializer_class=CareerSerializer,
            importer=career_service.bulk_import_careers,
        )

    def load_stream_domain_mappings(self):
        self.stdout.write("Loading Stream Domain Mappings...")
        file_path = path.join(
            settings.BASE_DIR,
            "core",
            "management",
            "source",
            "stream_domain_mapping_sample.csv",
        )
        self._bulk_import_from_csv(
            file_path=file_path,
            serializer_class=StreamDomainMappingSerializer,
            importer=stream_domain_mapping_service.bulk_import_mappings,
        )

    def load_domain_skill_mappings(self):
        self.stdout.write("Loading Domain Skill Mappings...")
        file_path = path.join(
            settings.BASE_DIR,
            "core",
            "management",
            "source",
            "domain_skill_mapping_sample.csv",
        )
        self._bulk_import_from_csv(
            file_path=file_path,
            serializer_class=DomainSkillMappingSerializer,
            importer=domain_skill_mapping_service.bulk_import_mappings,
        )

    def load_domain_career_mappings(self):
        self.stdout.write("Loading Domain Career Mappings...")
        file_path = path.join(
            settings.BASE_DIR,
            "core",
            "management",
            "source",
            "domain_career_mapping_sample.csv",
        )
        self._bulk_import_from_csv(
            file_path=file_path,
            serializer_class=DomainCareerMappingSerializer,
            importer=domain_career_mapping_service.bulk_import_mappings,
        )

    def load_assessment_questions(self):
        self.stdout.write("Seeding Assessment Questions...")
        call_command("seed_assessment_questions")

    def load_domain_report_meta(self):
        self.stdout.write("Loading Domain Report Meta...")
        from core.management.commands._master_import_utils import load_csv_rows
        from domain.models import DomainReportMeta

        file_path = path.join(
            settings.BASE_DIR, "core", "management", "source", "domain_report_meta.csv"
        )
        rows = load_csv_rows(file_path)
        for row in rows:
            code = (row.get("domain_code") or "").strip().lower()
            if not code:
                continue
            DomainReportMeta.objects.update_or_create(
                domain_code=code,
                defaults={
                    "degrees": (row.get("degrees") or "").strip(),
                    "careers": (row.get("careers") or "").strip(),
                    "note": (row.get("note") or "").strip(),
                    "direction_why": (row.get("direction_why") or "").strip(),
                    "how_to_choose_hint": (row.get("how_to_choose_hint") or "").strip(),
                    "next_step_1": (row.get("next_step_1") or "").strip(),
                    "next_step_2": (row.get("next_step_2") or "").strip(),
                    "next_step_3": (row.get("next_step_3") or "").strip(),
                },
            )

    def load_stream_report_meta(self):
        self.stdout.write("Loading Stream Report Meta...")
        from core.management.commands._master_import_utils import load_csv_rows
        from domain.models import StreamReportMeta

        file_path = path.join(
            settings.BASE_DIR, "core", "management", "source", "stream_report_meta.csv"
        )
        rows = load_csv_rows(file_path)
        for row in rows:
            code = (row.get("stream_code") or "").strip().lower()
            if not code:
                continue
            StreamReportMeta.objects.update_or_create(
                stream_code=code,
                defaults={
                    "why": (row.get("why") or "").strip(),
                    "subjects": (row.get("subjects") or "").strip(),
                    "careers": (row.get("careers") or "").strip(),
                    "note": (row.get("note") or "").strip(),
                    "next_step_1": (row.get("next_step_1") or "").strip(),
                    "next_step_2": (row.get("next_step_2") or "").strip(),
                    "next_step_3": (row.get("next_step_3") or "").strip(),
                },
            )

    def load_domain_counsellor_knowledge(self):
        self.stdout.write("Loading Domain Counsellor Knowledge...")
        from core.management.commands._master_import_utils import load_csv_rows
        from domain.models import DomainCounsellorKnowledge

        file_path = path.join(
            settings.BASE_DIR,
            "core",
            "management",
            "source",
            "domain_counsellor_knowledge.csv",
        )
        rows = load_csv_rows(file_path)
        for row in rows:
            code = (row.get("domain_code") or "").strip().lower()
            if not code:
                continue

            def _parse_keywords(raw):
                return [k.strip().lower() for k in (raw or "").split("|") if k.strip()]

            DomainCounsellorKnowledge.objects.update_or_create(
                domain_code=code,
                defaults={
                    "insight": (row.get("insight") or "").strip(),
                    "tradeoff": (row.get("tradeoff") or "").strip(),
                    "action": (row.get("action") or "").strip(),
                    "tension": (row.get("tension") or "").strip(),
                    "technical_keywords": _parse_keywords(
                        row.get("technical_keywords")
                    ),
                    "domain_keywords": _parse_keywords(row.get("domain_keywords")),
                },
            )

    def load_stream_counsellor_knowledge(self):
        self.stdout.write("Loading Stream Counsellor Knowledge...")
        from core.management.commands._master_import_utils import load_csv_rows
        from domain.models import StreamCounsellorKnowledge

        file_path = path.join(
            settings.BASE_DIR,
            "core",
            "management",
            "source",
            "stream_counsellor_knowledge.csv",
        )
        rows = load_csv_rows(file_path)
        for row in rows:
            code = (row.get("stream_code") or "").strip().lower()
            if not code:
                continue
            StreamCounsellorKnowledge.objects.update_or_create(
                stream_code=code,
                defaults={
                    "insight": (row.get("insight") or "").strip(),
                    "tradeoff": (row.get("tradeoff") or "").strip(),
                    "action": (row.get("action") or "").strip(),
                    "tension": (row.get("tension") or "").strip(),
                },
            )

    def load_domain_scoring_config(self):
        self.stdout.write("Loading Domain Scoring Config...")
        import json

        from core.management.commands._master_import_utils import load_csv_rows
        from domain.models import DomainScoringConfig

        file_path = path.join(
            settings.BASE_DIR,
            "core",
            "management",
            "source",
            "domain_scoring_config.csv",
        )
        if not path.exists(file_path):
            self.stdout.write(
                self.style.WARNING("domain_scoring_config.csv not found — skipping.")
            )
            return
        rows = load_csv_rows(file_path)
        for row in rows:
            code = (row.get("domain_code") or "").strip().lower()
            raw = (row.get("config") or "").strip()
            if not code or not raw:
                continue
            try:
                config = json.loads(raw)
            except json.JSONDecodeError as e:
                self.stdout.write(self.style.ERROR(f"Invalid JSON for {code}: {e}"))
                continue
            DomainScoringConfig.objects.update_or_create(
                domain_code=code,
                defaults={"config": config, "is_active": True},
            )

    def load_language_master(self):
        self.stdout.write("Loading Language Master...")
        file_path = path.join(
            settings.BASE_DIR,
            "core",
            "management",
            "source",
            "language_master_sample.csv",
        )
        self._bulk_import_from_csv(
            file_path=file_path,
            serializer_class=LanguageSerializer,
            importer=language_service.bulk_import_languages,
        )

    # Subscription Create
    subscription_data = [
        {
            "package_name": "Explorer",
            "subscription_type": "subscription",
            "subscription_price": 2800.0,
            "subscription_discount": 0.0,
            "subscription_sell_price": 2800.0,
            "plan_price": 26800.0,
            "duration_days": 365,
            "description": (
                "Begin your career journey with essential self-discovery tools. "
                "Explore career domains, take aptitude assessments, and gain clarity on your strengths and interests."
            ),
            "status": True,
            "core_features": [
                {"feature_name": "career_assessment", "feature_status": True},
                {"feature_name": "domain_exploration", "feature_status": True},
                {"feature_name": "skill_gap_analysis", "feature_status": False},
                {"feature_name": "career_roadmap", "feature_status": False},
                {"feature_name": "counsellor_session", "feature_status": False},
                {"feature_name": "resume_builder", "feature_status": False},
                {"feature_name": "job_recommendations", "feature_status": False},
                {"feature_name": "learning_resources", "feature_status": False},
                {"feature_name": "mock_interview", "feature_status": False},
                {"feature_name": "mentorship_access", "feature_status": False},
                {"feature_name": "premium_counsellor", "feature_status": False},
            ],
            "subscription_feature": [
                {"feature_name": "Career Aptitude Assessment", "feature_status": True},
                {"feature_name": "Domain & Stream Exploration", "feature_status": True},
                {"feature_name": "Basic Career Reports", "feature_status": True},
                {"feature_name": "Career Interest Profiling", "feature_status": True},
                {"feature_name": "Progress Tracking Dashboard", "feature_status": True},
            ],
        },
        {
            "package_name": "Career Builder",
            "subscription_type": "subscription",
            "subscription_price": 6000.0,
            "subscription_discount": 0.0,
            "subscription_sell_price": 6000.0,
            "plan_price": 30000.0,
            "duration_days": 365,
            "description": (
                "Accelerate your career growth with in-depth guidance, skill gap analysis, "
                "and a personalized career roadmap crafted by expert counsellors."
            ),
            "status": True,
            "core_features": [
                {"feature_name": "career_assessment", "feature_status": True},
                {"feature_name": "domain_exploration", "feature_status": True},
                {"feature_name": "skill_gap_analysis", "feature_status": True},
                {"feature_name": "career_roadmap", "feature_status": True},
                {"feature_name": "counsellor_session", "feature_status": True},
                {"feature_name": "resume_builder", "feature_status": True},
                {"feature_name": "job_recommendations", "feature_status": False},
                {"feature_name": "learning_resources", "feature_status": False},
                {"feature_name": "mock_interview", "feature_status": False},
                {"feature_name": "mentorship_access", "feature_status": False},
                {"feature_name": "premium_counsellor", "feature_status": False},
            ],
            "subscription_feature": [
                {"feature_name": "Career Aptitude Assessment", "feature_status": True},
                {"feature_name": "Domain & Stream Exploration", "feature_status": True},
                {"feature_name": "Skill Gap Analysis", "feature_status": True},
                {"feature_name": "Personalized Career Roadmap", "feature_status": True},
                {"feature_name": "Live Counsellor Sessions", "feature_status": True},
                {"feature_name": "Resume Builder", "feature_status": True},
                {"feature_name": "Detailed Career Reports", "feature_status": True},
            ],
        },
        {
            "package_name": "Career Pro",
            "subscription_type": "subscription",
            "subscription_price": 8000.0,
            "subscription_discount": 0.0,
            "subscription_sell_price": 8000.0,
            "plan_price": 32000.0,
            "duration_days": 365,
            "description": (
                "Unlock your full career potential with premium counselling, mentorship access, "
                "AI-powered job recommendations, mock interviews, and comprehensive career intelligence."
            ),
            "status": True,
            "core_features": [
                {"feature_name": "career_assessment", "feature_status": True},
                {"feature_name": "domain_exploration", "feature_status": True},
                {"feature_name": "skill_gap_analysis", "feature_status": True},
                {"feature_name": "career_roadmap", "feature_status": True},
                {"feature_name": "counsellor_session", "feature_status": True},
                {"feature_name": "resume_builder", "feature_status": True},
                {"feature_name": "job_recommendations", "feature_status": True},
                {"feature_name": "learning_resources", "feature_status": True},
                {"feature_name": "mock_interview", "feature_status": True},
                {"feature_name": "mentorship_access", "feature_status": True},
                {"feature_name": "premium_counsellor", "feature_status": True},
            ],
            "subscription_feature": [
                {"feature_name": "Career Aptitude Assessment", "feature_status": True},
                {"feature_name": "Domain & Stream Exploration", "feature_status": True},
                {"feature_name": "Skill Gap Analysis", "feature_status": True},
                {"feature_name": "Personalized Career Roadmap", "feature_status": True},
                {"feature_name": "Live Counsellor Sessions", "feature_status": True},
                {"feature_name": "Resume Builder", "feature_status": True},
                {
                    "feature_name": "AI-Powered Job Recommendations",
                    "feature_status": True,
                },
                {"feature_name": "Curated Learning Resources", "feature_status": True},
                {"feature_name": "Mock Interview Practice", "feature_status": True},
                {"feature_name": "Mentorship Access", "feature_status": True},
                {"feature_name": "Premium Career Counselling", "feature_status": True},
            ],
        },
    ]

    def load_subscription(self, *args, **kwargs):
        self.stdout.write("Creating Subscription Plans...")

        created_by_user = User.objects.first()

        for data in self.subscription_data:
            subscription, created = Subscription.objects.get_or_create(
                package_name=data["package_name"],
                defaults={
                    "price": data["plan_price"],
                    "duration_days": data["duration_days"],
                    "description": data["description"],
                    "is_active": data["status"],
                    "created_by": created_by_user,
                    "created_at": now(),
                },
            )

            if created:
                self.stdout.write(f"Created subscription: {subscription.package_name}")

                for feature in data["core_features"]:
                    SubscriptionFeature.objects.create(
                        subscription=subscription,
                        feature_name=feature["feature_name"],
                        is_enabled=feature["feature_status"],
                        is_core=True,
                        created_by=created_by_user,
                        created_at=now(),
                    )
                    self.stdout.write(
                        f"  - Added core feature: {feature['feature_name']}"
                    )

                for feature in data["subscription_feature"]:
                    SubscriptionFeature.objects.create(
                        subscription=subscription,
                        feature_name=feature["feature_name"],
                        is_enabled=feature["feature_status"],
                        is_core=False,
                        created_by=created_by_user,
                        created_at=now(),
                    )
                    self.stdout.write(
                        f"  - Added subscription feature: {feature['feature_name']}"
                    )

        self.stdout.write("Subscription data uploaded.")
