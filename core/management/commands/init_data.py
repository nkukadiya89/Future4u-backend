import csv
from os import path

from decouple import config
from django.conf import settings
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils.timezone import now

from assessment.models import (
    CareerDirection,
    CareerValue,
    Concern,
    GuidanceReason,
    ParentCareerExpectation,
    ParentConstraint,
    UserGoal,
    WorkConstraint,
)
from business_category.models import BusinessCategory
from city.models import City
from country.models import Country
from education_level.serializers import EducationLevelSerializer
from education_level.services import education_level_service
from language_master.serializers import LanguageSerializer
from language_master.services import language_service
from state.models import State
from stream.serializers import StreamSerializer
from stream.services import stream_service
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
            "--assessment", type=bool, help="Assessment questions/options to be seeded"
        )

        parser.add_argument("--groups", type=bool, help="Create Groups")
        parser.add_argument("--user", type=bool, help="Create Super User")

    def handle(self, *args, **kwargs):
        self.stdout.write("Initialise..")
        # Handle specific flags
        if kwargs["groups"]:
            admin_user = (
                User.objects.filter(is_superuser=True).first() or User.objects.first()
            )
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

        if kwargs["assessment"]:
            self.load_assessment_questions()
            self.load_assessment_masters()
            return

        # If no specific flags, run all initialization
        if (
            kwargs["country"] is None
            and kwargs["zone_name"] is None
            and kwargs["domain"] is None
            and kwargs["education_level"] is None
            and kwargs["assessment"] is None
            and kwargs["groups"] is None
            and kwargs["user"] is None
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
            self.load_streams()
            self.load_assessment_questions()
            self.load_assessment_masters()
            self.load_language_master()

    # Super User Create
    def create_super_user(self):
        self.stdout.write("Creating Super User.......")
        exist_superuser = User.objects.filter(is_superuser=True).first()
        if exist_superuser:
            self.stdout.write(
                self.style.WARNING("Super User already exists, skipping creation.")
            )
            return exist_superuser
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
        all_permissions = Permission.objects.all()
        super_admin_group.permissions.set(all_permissions)

        self.stdout.write(
            self.style.SUCCESS(
                f"Super Admin Group Assigned Full Access({all_permissions.count()} Permissions)"
            )
        )

        # Student Permissions - View own data, assessments, recommendations
        student_permissions = [
            "assessment|Can view student assessment",
            "assessment|Can view concern",
            "assessment|Can view career direction",
            "assessment|Can view career value",
            "assessment|Can view user goal",
            "domain|Can view domain",
            "education_level|Can view education level",
            "stream|Can view stream",
            "user|Can view user",
            "course|Can view courses",
            "course|Can add course inquiry",
            "course|Can view course inquiry",
            "assessment_career|Can view career recommendation",
            "assessment_career|Can view career suggestion",
            "internship_job|Can view internship",
            "internship_job|Can view internship application",
            "internship_job|Can add internship application",
            "internship_job|Can change internship application",
            "internship_job|Can view job",
            "internship_job|Can view job application",
            "internship_job|Can add job application",
            "internship_job|Can change job application",
        ]

        # Parent Permissions - View linked child's data
        parent_permissions = [
            "assessment|Can view student assessment",
            "assessment|Can view parent assessment",
            "domain|Can view domain",
            "education_level|Can view education level",
            "stream|Can view stream",
            "user|Can view user",
            "course|Can view courses",
            "course|Can add course inquiry",
            "course|Can view course inquiry",
            "internship_job|Can view internship",
            "internship_job|Can view internship application",
            "internship_job|Can add internship application",
            "internship_job|Can change internship application",
            "assessment_career|Can view career recommendation",
            "assessment_career|Can view career suggestion",
            "internship_job|Can view job",
            "internship_job|Can view job application",
            "internship_job|Can add job application",
            "internship_job|Can change job application",
        ]

        # Professional Permissions - View career resources, update own profile
        professional_permissions = [
            "assessment|Can view student assessment",
            "domain|Can view domain",
            "education_level|Can view education level",
            "stream|Can view stream",
            "user|Can view user",
            "course|Can view courses",
            "course|Can add course inquiry",
            "course|Can view course inquiry",
            "internship_job|Can view internship",
            "internship_job|Can view internship application",
            "internship_job|Can add internship application",
            "internship_job|Can change internship application",
            "assessment_career|Can view career recommendation",
            "assessment_career|Can view career suggestion",
            "internship_job|Can view job",
            "internship_job|Can view job application",
            "internship_job|Can add job application",
            "internship_job|Can change job application",
        ]

        # School/College Permissions - Manage their students
        school_college_permissions = [
            "assessment|Can view student assessment",
            "domain|Can view domain",
            "education_level|Can view education level",
            "stream|Can view stream",
            "user|Can view user",
            "course|Can view courses",
            "course|Can add courses",
            "course|Can change courses",
            "course|Can delete courses",
            "course|Can view course inquiry",
            "course|Can change course inquiry",
            "course|Can view course inquiry note",
            "course|Can add course inquiry note",
            "course|Can change course inquiry note",
            "course|Can delete course inquiry note",
        ]

        # Institute Permissions - Manage courses, grade students
        institute_permissions = [
            "assessment|Can add student assessment",
            "assessment|Can change student assessment",
            "assessment|Can view student assessment",
            "domain|Can view domain",
            "education_level|Can view education level",
            "stream|Can view stream",
            "user|Can view user",
            "course|Can view courses",
            "course|Can add courses",
            "course|Can change courses",
            "course|Can delete courses",
            "course|Can view course inquiry",
            "course|Can change course inquiry",
            "internship_job|Can view internship",
            "internship_job|Can add internship",
            "internship_job|Can change internship",
            "internship_job|Can delete internship",
            "internship_job|Can view internship application",
            "internship_job|Can change internship application",
            "internship_job|Can view internship application note",
            "internship_job|Can add internship application note",
            "internship_job|Can change internship application note",
            "internship_job|Can delete internship application note",
            "course|Can view course inquiry note",
            "course|Can add course inquiry note",
            "course|Can change course inquiry note",
            "course|Can delete course inquiry note",
        ]

        # Corporate Permissions - view candidates
        corporate_permissions = [
            "assessment|Can view student assessment",
            "domain|Can view domain",
            "education_level|Can view education level",
            "stream|Can view stream",
            "user|Can view user",
            "internship_job|Can view job",
            "internship_job|Can add job",
            "internship_job|Can change job",
            "internship_job|Can delete job",
            "internship_job|Can view internship",
            "internship_job|Can add internship",
            "internship_job|Can change internship",
            "internship_job|Can delete internship",
            "internship_job|Can view internship application",
            "internship_job|Can change internship application",
            "internship_job|Can view internship application note",
            "internship_job|Can add internship application note",
            "internship_job|Can change internship application note",
            "internship_job|Can delete internship application note",
            "internship_job|Can view job application",
            "internship_job|Can change job application",
            "internship_job|Can view job application note",
            "internship_job|Can add job application note",
            "internship_job|Can change job application note",
            "internship_job|Can delete job application note",
        ]

        # Assign superuser to Super Admin group
        if user.is_superuser:
            assign_group_super_admin = CustomGroup.objects.get(name="Super Admin")
            assign_group_super_admin.user_set.add(user)

        # Assign permissions to groups
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
                    f"Assigned {app_label}.{codename} permission to {group.name} group"
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
        existing_categories = {
            value.strip().lower()
            for value in BusinessCategory.objects.values_list(
                "business_category", flat=True
            )
        }
        with open(file_path, "r", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=",")
            categories_to_create = []
            for row in reader:
                category = row["business_category"].strip()
                key = category.lower()
                if not category or key in existing_categories:
                    continue
                existing_categories.add(key)
                categories_to_create.append(
                    BusinessCategory(business_category=category)
                )
            BusinessCategory.objects.bulk_create(categories_to_create)
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

    def load_assessment_masters(self):
        self.stdout.write("Loading Assessment Masters.")

        masters = (
            (
                Concern,
                [
                    "Job Security",
                    "Financial stability / Future demand",
                    "Wrong career choice",
                    "High education cost",
                    "Lack of guidance",
                    "Competitive pressure",
                ],
            ),
            (
                CareerDirection,
                [
                    "Study further",
                    "Find a Job",
                    "Internship",
                    "Skill Development",
                    "Study Abroad",
                    "Not Sure Yet",
                ],
            ),
            (
                CareerValue,
                [
                    "High salary potential",
                    "Job security and stability",
                    "Creativity and innovation",
                    "Work life balance",
                    "Making an impact on society",
                    "Opportunities to grow and learn",
                ],
            ),
            (
                UserGoal,
                [
                    "Career clarity",
                    "Course recommendation",
                    "Job/internship Opportunities",
                    "Parent confidence",
                ],
            ),
            (
                ParentCareerExpectation,
                [
                    "High salary potential",
                    "Job security and stability",
                    "Career growth and advancement",
                    "Work-life balance",
                    "Making a positive impact",
                    "Opportunities to learn new skills",
                ],
            ),
            (
                ParentConstraint,
                [
                    "Budget constraints",
                    "Prefer local education",
                    "Safety concerns",
                    "Family business preference",
                    "No relocation",
                    "No restriction",
                ],
            ),
            (
                WorkConstraint,
                [
                    "Cannot relocate",
                    "Physical or health limitations",
                    "Need flexible schedule",
                    "Prefer remote work only",
                    "Limited time due to other commitments",
                ],
            ),
            (
                GuidanceReason,
                [
                    "Feeling stuck or unsure about career path",
                    "Want to explore new career options",
                    "Need help with skill development",
                    "Planning for a promotion or growth",
                    "Considering starting my own business",
                    "Recently graduated or lost my job",
                ],
            ),
        )
        for model, names in masters:
            for name in names:
                model.objects.get_or_create(name__iexact=name, defaults={"name": name})

    # State Upload CSV
    def load_state(self, admin_user=None):
        self.stdout.write("Loading State...")
        created_by_user = admin_user or User.objects.filter(is_superuser=True).first()
        existing_states = {
            (state.name.strip().lower(), state.country_id)
            for state in State.objects.all()
        }
        file_path = path.join(
            settings.BASE_DIR, "core", "management", "source", "state.csv"
        )
        with open(file_path, "r", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=",")
            states_to_create = []
            for row in reader:
                try:
                    country = Country.objects.get(name=row["country_name"])
                    state_name = row["name"].strip()
                    key = (state_name.lower(), country.id)
                    if not state_name or key in existing_states:
                        continue
                    existing_states.add(key)
                    states_to_create.append(
                        State(
                            name=state_name,
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
            states.setdefault(key, state)
        existing_cities = {
            (city.name.strip().lower(), city.state_id, city.country_id)
            for city in City.objects.all()
        }

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

                    city_name = row["name"].strip()
                    key = (city_name.lower(), state.id, state.country_id)
                    if not city_name or key in existing_cities:
                        continue
                    existing_cities.add(key)
                    cities_to_create.append(
                        City(
                            name=city_name,
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
            cities.setdefault(key, city)
        existing_areas = {
            (area.city_id, (area.city_area_name or "").strip().lower(), area.zipcode)
            for area in CityArea.objects.all()
        }

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

                    area_name = row["city_area"].strip()
                    zipcode = row["zipcode"].strip()
                    key = (city.id, area_name.lower(), zipcode)
                    if not area_name or key in existing_areas:
                        continue
                    existing_areas.add(key)
                    city_areas_to_create.append(
                        CityArea(
                            country_id=city.state.country.id,
                            state_id=city.state.id,
                            city_id=city.id,
                            city_area_name=area_name,
                            zipcode=zipcode,
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
        self.stdout.write("Loading Domain Hierarchy...")
        file_path = path.join(
            settings.BASE_DIR,
            "core",
            "management",
            "source",
            "domain_hierarchy.csv",
        )

        # Prepare command arguments
        command_args = {"path": file_path}

        call_command("init_domain_master", **command_args)

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

    def load_assessment_questions(self):
        self.stdout.write("Seeding Assessment Questions...")
        call_command("seed_assessment_questions")

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
