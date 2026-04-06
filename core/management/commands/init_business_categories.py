import csv
import logging
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from business_category.models import BusinessCategory

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Load business categories from CSV (simple model, no bulk-import service)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--load",
            dest="load_path",
            default=str(
                Path(settings.BASE_DIR)
                / "core"
                / "management"
                / "source"
                / "business_categorys.csv"
            ),
            help="Load business categories from CSV at this path.",
        )

    def handle(self, *args, **options):
        load_path = Path(options["load_path"])
        if not load_path.is_file():
            raise CommandError(f"File not found: {load_path}")

        rows = []
        with load_path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = (row.get("business_category") or "").strip()
                if not name:
                    continue
                rows.append(name)

        if not rows:
            raise CommandError("No rows found in CSV.")

        created = 0
        for name in rows:
            _, was_created = BusinessCategory.objects.get_or_create(
                business_category=name
            )
            if was_created:
                created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded business categories: total={len(rows)} created={created}"
            )
        )
