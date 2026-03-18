import csv
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from city.models import City
from city_areas.models import CityArea
from country.models import Country
from state.models import State

User = get_user_model()


class Command(BaseCommand):
    help = "Flush and reload city area data from CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            default="core/management/source/city_area.csv",
            help="Path to the CSV file containing city area data",
        )
        parser.add_argument("--force", action="store_true", help="Force flush without confirmation")

    def handle(self, *args, **options):
        csv_file_path = options["csv_file"]
        force = options["force"]

        # Check if CSV file exists
        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f"CSV file not found: {csv_file_path}"))
            return

        # Get confirmation unless force flag is used
        if not force:
            confirm = input(
                "This will delete all existing city area data and reload from CSV. "
                "Are you sure you want to continue? (yes/no): "
            )
            if confirm.lower() != "yes":
                self.stdout.write("Operation cancelled.")
                return

        try:
            with transaction.atomic():
                # Flush existing data
                deleted_count = CityArea.objects.all().delete()[0]
                self.stdout.write(self.style.WARNING(f"Deleted {deleted_count} existing city area records"))

                # Load data from CSV
                self.load_city_areas_from_csv(csv_file_path)

                self.stdout.write(self.style.SUCCESS("City area data successfully reloaded"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during reload: {str(e)}"))
            raise

    def load_city_areas_from_csv(self, csv_file_path):
        """Load city areas from CSV file"""
        created_count = 0
        skipped_count = 0

        with open(csv_file_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                try:
                    # Get or create foreign key objects
                    country = self.get_or_none(Country, name=row["country_name"])
                    state = self.get_or_none(State, name=row["state_name"])
                    city = self.get_or_none(City, name=row["city_name"])

                    if not all([country, state, city]):
                        self.stdout.write(
                            self.style.WARNING(
                                f"Skipping row {reader.line_num}: Missing related data - "
                                f"Country: {row['country_name']}, "
                                f"State: {row['state_name']}, "
                                f"City: {row['city_name']}"
                            )
                        )
                        skipped_count += 1
                        continue

                    # Get created_by user
                    created_by_id = row.get("created_by", "1")
                    created_by = self.get_or_none(User, id=created_by_id)

                    # Create CityArea
                    CityArea.objects.create(
                        country=country,
                        state=state,
                        city=city,
                        city_area_name=row["city_area"],
                        zipcode=row["zipcode"],
                        created_by=created_by,
                    )
                    created_count += 1

                    if created_count % 100 == 0:
                        self.stdout.write(f"Created {created_count} records...")

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error processing row {reader.line_num}: {str(e)}"))
                    skipped_count += 1
                    continue

        self.stdout.write(
            self.style.SUCCESS(f"Created {created_count} city area records, " f"skipped {skipped_count} records")
        )

    def get_or_none(self, model, **kwargs):
        """Get model instance or return None"""
        try:
            return model.objects.get(**kwargs)
        except model.DoesNotExist:
            return None
