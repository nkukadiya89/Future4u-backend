import csv
from os import path

from decouple import config
from django.conf import settings
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand
from django.utils.timezone import now

from company.models import Company
from country.models import Country
from currency.models import Currency
from delivery_address.models import City
from pincode.models import PinCode
from subscription.models import Subcription, SubscriptionFeature
from unit_of_measurement.models import UnitOfMeasurements
from user.models import CustomGroup, RoleFamily, User
from vendor.models import VendorMatrixSteps


class Command(BaseCommand):
    help = "Load country data into country database"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--country", type=bool, help="Country data to be uploaded")
        parser.add_argument(
            "--zone_name", type=bool, help="ZoneName data to be uploaded"
        )

        parser.add_argument("--groups", type=bool, help="Create Groups")
        parser.add_argument("--user", type=bool, help="Create Super User")

    def handle(self, *args, **kwargs):
        self.stdout.write("Initialise..")
        if (
            kwargs["country"] is None
            and kwargs["zone_name"] is None
            and kwargs["groups"] is None
            and kwargs["user"] is None
        ):
            self.create_super_user()
            self.create_custom_groups()
            self.create_unit_of_measurements()
            self.create_vendor_matrix_step()
            self.create_role_family()

            self.load_country()
            self.load_currency()
            self.load_pincode_city_state_wise()
            self.load_pincode_city_state_wise_2()
            self.load_city_name()
            self.create_subscription_data()

    # Super User Create
    def create_super_user(self):
        self.stdout.write("Creating Super User.......")
        user = User.objects.create(
            is_superuser=True,
            is_staff=True,
            is_active=True,
            username="PROCEM",
            first_name="PROCEM",
            last_name="Admin",
            about_me="Admin ",
            email=config("INIT_EMAIL"),
            profile_image="null",
            whatsapp_verified=False,
            designation="Super Admin",
            phone=963963963,
            message="null",
            role=1,
            status="active",
            aadhar_card=339782180844,
            pancard="AAAAA0000A",
            emergency_contact=5764768365,
            current_address="3581 Pleasure Plaza",
            permanent_address="540 Springview Court",
            email_verified=True,
            phone_verified=True,
            company=None,
            vendor=None,
            employee=None,
        )
        new_password = config("INIT_ADMIN_PASSWORD")
        user.set_password(new_password)  # type: ignore

        user.save()
        self.stdout.write("Super User Created!.......")
        return user

    # category Create

    def create_unit_of_measurements(self):
        self.stdout.write("Creating Unit of Measurements...........")
        created_by_user = User.objects.get(pk=1)
        unit_of_measurements = UnitOfMeasurements.objects.create(
            unit_of_measurement="MT",
            created_by=created_by_user,
            updated_by=created_by_user,
        )
        return unit_of_measurements

    # Role Family Create
    role_family_data = [
        {
            "family_name": "Buyer Family",
            "created_by": 1,
            "updated_by": 1,
        },
        {
            "family_name": "CXO Family / Management Family",
            "created_by": 1,
            "updated_by": 1,
        },
        {
            "family_name": "Finance Family",
            "created_by": 1,
            "updated_by": 1,
        },
        {
            "family_name": "Project Family",
            "created_by": 1,
            "updated_by": 1,
        },
        {
            "family_name": "Eng. Family",
            "created_by": 1,
            "updated_by": 1,
        },
        {
            "family_name": "Planning family",
            "created_by": 1,
            "updated_by": 1,
        },
    ]

    def create_role_family(self):
        self.stdout.write("Creating Role Family...........")
        created_by_user = User.objects.get(pk=1)
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

    # Company Create
    def create_company(self):
        self.stdout.write("Creating Company.......")
        created_by_user = User.objects.get(pk=1)
        pincode_number = PinCode.objects.filter(pincode_number=380015).first()
        company = Company.objects.create(
            name="PROCEM",
            first_name="Admin",
            designation="Founder",
            address_line_1="902, Ganesh Glory, Jagatpur Road",
            address_line_2="Sarkhej - Gandhinagar Highway Gota",
            city="Ahmedabad",
            state="Gujarat",
            website="procem.ai",
            no_of_employees="11-50 employees",
            company_type="Buyer",
            company_pan="RVUMB5621M",
            gst_no="23MRZSI9550T2",
            about_company=(
                "A Procurement company is a business that specializes in procurement. "
                "Procurement is the process of acquiring goods and services by "
                "negotiating with suppliers"
            ),
            email=config("INIT_EMAIL"),
            phone="919727111122",
            pincode_id=pincode_number,
            status="active",
            is_active=True,
            created_by=created_by_user,
            updated_by=created_by_user,
        )
        user = User.objects.get(pk=1)
        user.company = company
        user.save()

        created_by_user = User.objects.get(pk=1)

        self.stdout.write("Company Created!.......")
        return company

    def create_custom_groups(self):
        self.stdout.write("Creating Groups.......")
        user = User.objects.get(id=1)

        super_admin_group = CustomGroup.objects.create(
            name="Super Admin", group_name="Super Admin", created_by=user
        )
        company_admin_group = CustomGroup.objects.create(
            name="Company Admin", group_name="Company Admin"
        )
        vendor_admin_group = CustomGroup.objects.create(
            name="Vendor Admin", group_name="Vendor Admin"
        )

        self.stdout.write("Custom Groups Created!.......")

        super_admin_permissions = [
            "activity_log|Can view activity log",
            "category_tree|Can add category tree",
            "category_tree|Can change category tree",
            "category_tree|Can delete category tree",
            "category_tree|Can view category tree",
            "company|Can add attachment",
            "company|Can add company",
            "company|Can add key persons",
            "company|Can change attachment",
            "company|Can change company",
            "company|Can change key persons",
            "company|Can delete attachment",
            "company|Can delete company",
            "company|Can delete key persons",
            "company|Can view attachment",
            "company|Can view company",
            "company|Can view key persons",
            "pincode|Can add pin code",
            "pincode|Can change pin code",
            "pincode|Can delete pin code",
            "pincode|Can view pin code",
            "request_demo|Can change request demo",
            "request_demo|Can delete request demo",
            "request_demo|Can view request demo",
            "subcription|Can add subcription",
            "subcription|Can change subcription",
            "subcription|Can delete subcription",
            "subcription|Can view subcription",
            "subcription|Can add stripe charge",
            "subcription|Can add subscription feature",
            "subcription|Can add subscription invoice",
            "subcription|Can change stripe charge",
            "subcription|Can change subscription feature",
            "subcription|Can change subscription invoice",
            "subcription|Can delete stripe charge",
            "subcription|Can delete subscription feature",
            "subcription|Can delete subscription invoice",
            "subcription|Can view stripe charge",
            "subcription|Can view subscription feature",
            "subcription|Can view subscription invoice",
            "unit_of_measurement|Can add unit of measurements",
            "unit_of_measurement|Can change unit of measurements",
            "unit_of_measurement|Can delete unit of measurements",
            "unit_of_measurement|Can view unit of measurements",
            "user|Can add custom group",
            "user|Can change auth group permissions model",
            "user|Can change custom group",
            "user|Can change user",
            "user|Can delete auth group permissions model",
            "user|Can delete custom group",
            "user|Can view auth group permissions model",
            "user|Can view custom group",
            "user|Can view user",
        ]

        company_admin_permissions = [
            "activity_log|Can view activity log",
            "company|Can add attachment",
            "company|Can add key persons",
            "company|Can change attachment",
            "company|Can change company",
            "company|Can change key persons",
            "company|Can delete attachment",
            "company|Can delete key persons",
            "company|Can view attachment",
            "company|Can view company",
            "company|Can view key persons",
            "delivery_address|Can add address master",
            "delivery_address|Can add wbs number",
            "delivery_address|Can change address master",
            "delivery_address|Can change wbs number",
            "delivery_address|Can delete address master",
            "delivery_address|Can delete wbs number",
            "delivery_address|Can view address master",
            "delivery_address|Can view wbs number",
            "subcription|Can view stripe charge",
            "subcription|Can view subcription",
            "subcription|Can view subscription feature",
            "user_profile|Can change business setting",
            "user_profile|Can view business setting",
            "user_profile|Can view pr release",
            "user|Can add custom group",
            "user|Can change auth group permissions model",
            "user|Can change custom group",
            "user|Can change user",
            "user|Can delete auth group permissions model",
            "user|Can delete custom group",
            "user|Can view auth group permissions model",
            "user|Can view custom group",
            "vendor|Can add vendor",
            "vendor|Can change vendor",
            "vendor|Can view vendor",
            "vendor|Can delete vendor",
            "vendor|Can add key persons",
            "vendor|Can view key persons",
            "vendor|Can change key persons",
            "vendor|Can delete key persons",
            "vendor|Can add vendor company code",
            "vendor|Can view vendor company code",
            "vendor|Can change vendor company code",
            "vendor|Can delete vendor company code",
            "vendor|Can add vendor inquiry value",
            "vendor|Can view vendor inquiry value",
            "vendor|Can change vendor inquiry value",
            "vendor|Can delete vendor inquiry value",
            "vendor|Can add assign city to vendor",
            "vendor|Can change assign city to vendor",
            "vendor|Can view assign city to vendor",
            "vendor|Can delete assign city to vendor",
            "vendor|Can add vendor suppliers billing details",
            "vendor|Can change vendor suppliers billing details",
            "vendor|Can delete vendor suppliers billing details",
            "vendor|Can view vendor suppliers billing details",
            "vendor|Can add bank details",
            "vendor|Can change bank details",
            "vendor|Can delete bank details",
            "vendor|Can view bank details",
            "vendor|Can add vendor company",
            "vendor|Can view vendor company",
            "vendor|Can change vendor company",
            "vendor|Can delete vendor company",
            "vendor|Can add vendor payment released",
            "vendor|Can view vendor payment released",
            "vendor|Can change vendor payment released",
            "vendor|Can delete vendor payment released",
            "vendor|Can add vendor communication matrix",
            "vendor|Can view vendor communication matrix",
            "vendor|Can change vendor communication matrix",
            "vendor|Can delete vendor communication matrix",
        ]
        vendor_admin_permissions = [
            "user|Can add custom group",
            "user|Can change auth group permissions model",
            "user|Can change custom group",
            "user|Can change user",
            "user|Can delete auth group permissions model",
            "user|Can delete custom group",
            "user|Can view auth group permissions model",
            "user|Can view custom group",
            "user|Can view user",
            "vendor|Can change vendor",
            "vendor|Can view vendor",
            "vendor|Can add key persons",
            "vendor|Can view key persons",
            "vendor|Can change key persons",
            "vendor|Can delete key persons",
            "vendor|Can view vendor company code",
            "vendor|Can view vendor inquiry value",
            "vendor|Can view assign city to vendor",
            "vendor|Can add vendor suppliers billing details",
            "vendor|Can change vendor suppliers billing details",
            "vendor|Can delete vendor suppliers billing details",
            "vendor|Can view vendor suppliers billing details",
            "vendor|Can add bank details",
            "vendor|Can change bank details",
            "vendor|Can delete bank details",
            "vendor|Can view bank details",
            "vendor|Can add vendor company",
            "vendor|Can view vendor company",
            "vendor|Can change vendor company",
            "vendor|Can delete vendor company",
            "vendor|Can add vendor payment released",
            "vendor|Can view vendor payment released",
            "vendor|Can change vendor payment released",
            "vendor|Can delete vendor payment released",
            "vendor|Can add vendor communication matrix",
            "vendor|Can view vendor communication matrix",
            "vendor|Can change vendor communication matrix",
            "vendor|Can delete vendor communication matrix",
        ]

        assign_group_super_admin = CustomGroup.objects.get(name="Super Admin")
        assign_group_super_admin.user_set.add(user)

        self.assign_permissions(super_admin_group, super_admin_permissions)
        self.assign_permissions(company_admin_group, company_admin_permissions)
        self.assign_permissions(vendor_admin_group, vendor_admin_permissions)

    def assign_permissions(self, group, permissions):
        for permission_name in permissions:
            try:
                app_label, codename = permission_name.split("|")
                permission_obj = Permission.objects.get(
                    content_type__app_label=app_label, name=codename
                )
                group.permissions.add(permission_obj)
                self.stdout.write(
                    f"Assigned {app_label and codename} permission to {group.name} group"
                )
            except Permission.DoesNotExist:
                self.stdout.write(
                    f"Permission {permission_name} does not exist. "
                    f"Skipping assignment to {group.name} group"
                )
            except Permission.MultipleObjectsReturned:
                self.stdout.write(
                    f"Multiple permissions with the name {permission_name} exist. "
                    f"Skipping assignment to {group.name} group"
                )

    # Currency Upload CSV
    def load_currency(self):
        self.stdout.write("Loading Currency")
        file_path = path.join(
            settings.BASE_DIR, "core", "management", "source", "currey.csv"
        )
        with open(file_path, "r", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=",")

            Currency.objects.bulk_create(
                [
                    Currency(
                        country_id=row["country_id"],
                        currency_name=row["currency_name"],
                        currency_code=row["currency_code"],
                        currency_symbol=row["currency_symbol"],
                    )
                    for row in reader
                ],
                ignore_conflicts=True,
            )
        self.stdout.write("Currency Upload")

    # Country Upload CSV
    def load_country(self):
        self.stdout.write("Loading Country...")
        file_path = path.join(
            settings.BASE_DIR, "core", "management", "source", "country.csv"
        )
        with open(file_path, "r") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=",")
            Country.objects.bulk_create(
                [
                    Country(
                        name=row["name"],
                        code=row["code"],
                        unicode=row["unicode"],
                        country_flag=row["unicode"],
                        phone_code=row["phone_code"],
                    )
                    for row in reader
                ],
                ignore_conflicts=True,
            )
        self.stdout.write("Country data uploaded.")

    # Pincode City and State Wise Upload CSV
    def load_pincode_city_state_wise(self):
        self.stdout.write("Loading Pincode File 1........")
        file_path = path.join(
            settings.BASE_DIR,
            "core",
            "management",
            "source",
            "pincode_city_state_wise.csv",
        )
        created_by_user = User.objects.get(pk=1)
        with open(file_path, "r") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=",")
            PinCode.objects.bulk_create(
                [
                    PinCode(
                        zone_id_id=row["zone_id"],
                        pincode_number=row["pincode_number"],
                        city_name=row["city_name"],
                        state_name=row["state_name"],
                        created_by=created_by_user,
                        updated_by=created_by_user,
                    )
                    for row in reader
                ],
                ignore_conflicts=True,
            )
        self.stdout.write("Pincode Data Uploaded File 1.....")

    def load_pincode_city_state_wise_2(self):
        self.stdout.write("Loading Pincode File 2........")
        file_path = path.join(
            settings.BASE_DIR,
            "core",
            "management",
            "source",
            "pincode_city_state_wise_2.csv",
        )
        created_by_user = User.objects.get(pk=1)
        with open(file_path, "r") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=",")
            PinCode.objects.bulk_create(
                [
                    PinCode(
                        zone_id_id=row["zone_id"],
                        pincode_number=row["pincode_number"],
                        city_name=row["city_name"],
                        state_name=row["state_name"],
                        created_by=created_by_user,
                        updated_by=created_by_user,
                    )
                    for row in reader
                ],
                ignore_conflicts=True,
            )
        self.stdout.write("Pincode Data Uploaded 2....")

    # vendor matrix step Create
    vendor_matrix_step_data = [
        {
            "name": "PR Raised",
            "created_by": 1,
            "updated_by": 1,
        },
        {
            "name": "RFQ Floated",
            "created_by": 1,
            "updated_by": 1,
        },
        {
            "name": "Order Placed",
            "created_by": 1,
            "updated_by": 1,
        },
        {
            "name": "Order Delivered",
            "created_by": 1,
            "updated_by": 1,
        },
        {
            "name": "Payment Received",
            "created_by": 1,
            "updated_by": 1,
        },
    ]

    def create_vendor_matrix_step(self):
        self.stdout.write("Creating Vendor Matrix Steps...........")
        created_by_user = User.objects.get(pk=1)
        vendor_matrix_steps = []

        for data in self.vendor_matrix_step_data:
            vendor_matrix_step, _ = VendorMatrixSteps.objects.update_or_create(
                name=data["name"],
                defaults={
                    "created_by": created_by_user,
                    "updated_by": created_by_user,
                },
            )
            vendor_matrix_steps.append(vendor_matrix_step)
        return vendor_matrix_steps

    # City Upload CSV
    def load_city_name(self):
        self.stdout.write("Loading City....")
        file_path = path.join(
            settings.BASE_DIR, "core", "management", "source", "india_city_name.csv"
        )
        with open(file_path, "r") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=",")
            City.objects.bulk_create(
                [
                    City(
                        city_name=row["city_name"],
                        created_by=User.objects.get(id=row["created_by"]),
                        updated_by=User.objects.get(id=row["updated_by"]),
                    )
                    for row in reader
                ],
                ignore_conflicts=True,
            )
        self.stdout.write("City data uploaded.")

    # Subscription Create
    subscription_data = [
        {
            "package_name": "Welcome Package",
            "subscription_type": "enterpirse",
            "per_user_price": 0,
            "discount": 0,
            "sell_price": 0,
            "duration": "90",
            "description": "Full access to all features",
            "status": "active",
            "features": [
                "Site Location",
                "Manage User Group",
                "Manage User",
                "Business Setting",
                "Vendor Onboarding",
                "Reports",
            ],
        }
    ]

    def create_subscription_data(self, *args, **kwargs):
        self.stdout.write("Creating Subscription Plans...")

        created_by_user = User.objects.first()

        for data in self.subscription_data:
            subscription, created = Subcription.objects.get_or_create(
                package_name=data["package_name"],
                defaults={
                    "subscription_type": data["subscription_type"],
                    "per_user_price": data["per_user_price"],
                    "discount": data["discount"],
                    "sell_price": data["sell_price"],
                    "duration": data["duration"],
                    "description": data["description"],
                    "status": data["status"],
                    "created_by": created_by_user,
                    "updated_by": created_by_user,
                    "created_at": now(),
                    "updated_at": now(),
                },
            )

            if created:
                self.stdout.write(f"Created subscription: {subscription.package_name}")

                for feature in data["features"]:
                    SubscriptionFeature.objects.create(
                        subcription=subscription,
                        feature_name=feature,
                        feature_status=True,
                        created_by=created_by_user,
                        updated_by=created_by_user,
                        created_at=now(),
                        updated_at=now(),
                    )
                    self.stdout.write(f"  - Added feature: {feature}")

        self.stdout.write("Subscription data uploaded.")
