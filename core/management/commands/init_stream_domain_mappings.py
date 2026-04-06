import logging
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from core.management.commands._master_import_utils import (
    RequestUserProxy,
    load_csv_rows,
    resolve_import_user,
)
from stream_domain_mapping.serializers import StreamDomainMappingSerializer
from stream_domain_mapping.services import stream_domain_mapping_service

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Load stream-domain mappings from CSV (defaults to core/management/source/stream_domain_mapping_sample.csv)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            dest="load_path",
            default=str(
                Path(settings.BASE_DIR)
                / "core"
                / "management"
                / "source"
                / "stream_domain_mapping_sample.csv"
            ),
            help="Load stream-domain mappings from CSV at this path.",
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
        rows = load_csv_rows(load_path)
        logger.info(
            "init_stream_domain_mappings loading %s rows from %s", len(rows), load_path
        )
        result = stream_domain_mapping_service.bulk_import_mappings(
            user=user,
            rows=rows,
            serializer_class=StreamDomainMappingSerializer,
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
