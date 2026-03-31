import logging
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from core.management.commands._master_import_utils import RequestUserProxy, load_csv_rows, resolve_import_user
from career.serializers import CareerSerializer
from career.services import career_service

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Write sample career CSV and/or load careers from CSV."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sample-path",
            default=str(Path(settings.BASE_DIR) / "core" / "management" / "source" / "career_master_sample.csv"),
            help="Path to write sample CSV.",
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
            help="Load careers from CSV at this path.",
        )
        parser.add_argument(
            "--username",
            default=None,
            help="User for created_by/updated_by on imports (default: first superuser).",
        )

    def handle(self, *args, **options):
        if not options.get("no_sample"):
            sample_path = Path(options["sample_path"])
            sample_path.parent.mkdir(parents=True, exist_ok=True)
            sample_path.write_bytes(career_service.sample_csv_bytes())
            self.stdout.write(self.style.SUCCESS(f"Sample CSV written: {sample_path.resolve()}"))

        load_path = options.get("load_path")
        if not load_path:
            return

        user = resolve_import_user(username=options.get("username"))
        rows = load_csv_rows(load_path)
        logger.info("init_careers loading %s rows from %s", len(rows), load_path)
        result = career_service.bulk_import_careers(
            user=user,
            rows=rows,
            serializer_class=CareerSerializer,
            context={"request": RequestUserProxy(user)},
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

