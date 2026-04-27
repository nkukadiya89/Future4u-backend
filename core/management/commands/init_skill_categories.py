import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from core.management.commands._master_import_utils import resolve_import_user
from skill_category.models import SkillCategory


class Command(BaseCommand):
    help = "Load skill categories from CSV (defaults to core/management/source/skill_category_master_sample.csv)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            dest="load_path",
            default=str(
                Path(settings.BASE_DIR)
                / "core"
                / "management"
                / "source"
                / "skill_category_master_sample.csv"
            ),
            help="Load skill categories from CSV at this path.",
        )
        parser.add_argument(
            "--username",
            default=None,
            help="User for created_by/updated_by on imports (default: first superuser).",
        )

    def handle(self, *args, **options):
        load_path = options.get("load_path")
        if not load_path:
            return

        user = resolve_import_user(username=options.get("username"))
        
        # Load CSV rows
        path = Path(load_path)
        if not path.is_file():
            self.stdout.write(self.style.ERROR(f"File not found: {path}"))
            return

        rows = []
        with path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                self.stdout.write(self.style.ERROR("CSV has no header row."))
                return
            for row in reader:
                if not any((v or "").strip() for v in row.values()):
                    continue
                rows.append(dict(row))

        if not rows:
            self.stdout.write(self.style.ERROR("No data rows in CSV."))
            return

        # Bulk create skill categories
        created = SkillCategory.objects.bulk_create(
            [
                SkillCategory(
                    category_name=row.get("category_name", "").strip(),
                    category_image_url="",  # Empty initially, upload via API later
                    created_by=user,
                    updated_by=user,
                )
                for row in rows
            ],
            ignore_conflicts=True,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Load complete: {len(created)} skill categories imported successfully."
            )
        )
