import csv
import logging
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from education_level.serializers import EducationLevelSerializer
from education_level.services import education_level_service

logger = logging.getLogger(__name__)
User = get_user_model()


class _Req:
    __slots__ = ("user",)

    def __init__(self, user):
        self.user = user


class Command(BaseCommand):
    help = "Write sample education-level CSV and/or load levels from CSV."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sample-path",
            default="education_level_master_sample.csv",
            help="Path to write sample CSV (default: education_level_master_sample.csv).",
        )
        parser.add_argument(
            "--no-sample",
            action="store_true",
            help="Do not write the sample CSV file.",
        )
        parser.add_argument(
            "--load",
            dest="load_path",
            default=None,
            help="Load education levels from CSV at this path.",
        )
        parser.add_argument(
            "--username",
            default=None,
            help="User for created_by/updated_by on imports (default: first superuser).",
        )

    def handle(self, *args, **options):
        if not options.get("no_sample"):
            sample_path = Path(options["sample_path"])
            sample_path.write_bytes(education_level_service.sample_csv_bytes())
            self.stdout.write(self.style.SUCCESS(f"Sample CSV written: {sample_path.resolve()}"))
        load_path = options.get("load_path")
        if not load_path:
            return
        path = Path(load_path)
        if not path.is_file():
            raise CommandError(f"File not found: {path}")
        user = None
        if options.get("username"):
            user = User.objects.filter(username=options["username"]).first()
            if not user:
                raise CommandError(f"User not found: {options['username']}")
        if user is None:
            user = User.objects.filter(is_superuser=True).first() or User.objects.order_by("pk").first()
        if user is None:
            raise CommandError("No user available for audit fields; create a user or pass --username.")
        rows = []
        with path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise CommandError("CSV has no header row.")
            for r in reader:
                if not any((v or "").strip() for v in r.values()):
                    continue
                rows.append(dict(r))
        if not rows:
            raise CommandError("No data rows in CSV.")
        logger.info("init_education_levels loading %s rows from %s", len(rows), path)
        result = education_level_service.bulk_import_levels(
            user=user,
            rows=rows,
            serializer_class=EducationLevelSerializer,
            context={"request": _Req(user)},
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Load complete: success={result['success_count']} errors={result['error_count']} batch={result['batch_id']}"
            )
        )
        for d in result["error_details"][:20]:
            logger.warning("row %s: %s", d["row"], d["message"])
            self.stdout.write(self.style.WARNING(f"Row {d['row']}: {d['message']}"))
        if len(result["error_details"]) > 20:
            self.stdout.write(self.style.WARNING("... additional errors omitted (see logs / import batch)."))
