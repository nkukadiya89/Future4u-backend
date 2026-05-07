import logging
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Load domains from CSV (defaults to core/management/source/domain_hierarchy.csv)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            dest="load_path",
            default=str(
                Path(settings.BASE_DIR)
                / "core"
                / "management"
                / "source"
                / "domain_hierarchy.csv"
            ),
            help="Load domains from CSV at this path.",
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

        logger.info("init_domain_master loading hierarchy from %s", load_path)
        call_command(
            "seed_domain_hierarchy",
            load_path=load_path,
            username=options.get("username"),
        )
