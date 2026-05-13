import logging
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from core.management.commands._master_import_utils import (
    RequestUserProxy,
    load_csv_rows,
    resolve_import_user,
)
from stream.models import Stream
from stream.serializers import StreamSerializer
from stream.services import stream_service

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Load streams from CSV (defaults to core/management/source/stream_master_sample.csv)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            dest="load_path",
            default=str(
                Path(settings.BASE_DIR)
                / "core"
                / "management"
                / "source"
                / "stream_master_sample.csv"
            ),
            help="Load streams from CSV at this path.",
        )
        parser.add_argument(
            "--username",
            default=None,
            help="User for created_by/updated_by on imports (default: first superuser).",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Archive streams not in the CSV and free sequence numbers before import.",
        )

    def _prepare_replace(self, *, rows, user):
        incoming_codes = {
            (row.get("stream_code") or "").strip().lower()
            for row in rows
            if (row.get("stream_code") or "").strip()
        }
        existing = list(Stream.objects.order_by("sequence_order", "stream_code"))
        for index, stream in enumerate(existing, start=1):
            stream.sequence_order = 10000 + index
            stream.updated_by = user
            if stream.stream_code.lower() not in incoming_codes:
                stream.is_active = False
                stream.deleted = True
                stream.deleted_by = user
            stream.save(
                update_fields=[
                    "sequence_order",
                    "is_active",
                    "deleted",
                    "deleted_by",
                    "updated_at",
                    "updated_by",
                ]
            )
        return len(existing), len(incoming_codes)

    def handle(self, *args, **options):
        load_path = options.get("load_path")
        if not load_path:
            return

        user = resolve_import_user(username=options.get("username"))
        rows = load_csv_rows(load_path)
        if options.get("replace"):
            moved_count, incoming_count = self._prepare_replace(rows=rows, user=user)
            self.stdout.write(
                self.style.WARNING(
                    f"Prepared stream replacement: moved={moved_count} incoming={incoming_count}"
                )
            )
        logger.info("init_streams loading %s rows from %s", len(rows), load_path)
        result = stream_service.bulk_import_streams(
            user=user,
            rows=rows,
            serializer_class=StreamSerializer,
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
            self.stdout.write(
                self.style.WARNING(
                    "... additional errors omitted (see logs / import batch)."
                )
            )
