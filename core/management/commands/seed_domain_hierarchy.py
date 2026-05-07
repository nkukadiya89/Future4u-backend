from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from core.management.commands._master_import_utils import (
    load_csv_rows,
    resolve_import_user,
)
from domain.models import Domain
from domain.services import domain_service


class Command(BaseCommand):
    help = "Seed domain categories and child domains from domain_hierarchy.csv."

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
            help="Load domain hierarchy from this CSV path.",
        )
        parser.add_argument(
            "--username",
            default=None,
            help="User for created_by/updated_by on imports (default: first superuser).",
        )

    def handle(self, *args, **options):
        self._assert_schema_ready()
        user = resolve_import_user(username=options.get("username"))
        rows = load_csv_rows(options["load_path"])
        normalized = self._normalize_rows(rows)

        with transaction.atomic():
            domains_by_code = self._upsert_all_without_parents(
                rows=normalized,
                user=user,
            )
            updated = self._attach_parents(
                rows=normalized,
                domains_by_code=domains_by_code,
                user=user,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Domain hierarchy loaded: total={len(normalized)} parent_links={updated}"
            )
        )

    def _assert_schema_ready(self):
        table_name = Domain._meta.db_table
        with connection.cursor() as cursor:
            columns = {
                column.name
                for column in connection.introspection.get_table_description(
                    cursor,
                    table_name,
                )
            }
        if "domain_category" in columns:
            raise CommandError(
                "Run migrations before seeding domain_hierarchy.csv: "
                "python manage.py migrate"
            )

    def _normalize_rows(self, rows: list[dict]) -> list[dict]:
        required = {"domain_code", "domain_name", "parent_code"}
        seen: set[str] = set()
        normalized = []

        for idx, row in enumerate(rows, start=2):
            missing = required - set(row.keys())
            if missing:
                raise CommandError(f"Missing columns: {', '.join(sorted(missing))}")

            code = (row.get("domain_code") or "").strip()
            name = (row.get("domain_name") or "").strip()
            parent_code = (row.get("parent_code") or row.get("parent") or "").strip()
            if not code:
                raise CommandError(f"Row {idx}: domain_code is required.")
            if not name:
                raise CommandError(f"Row {idx}: domain_name is required.")

            key = code.lower()
            if key in seen:
                raise CommandError(f"Row {idx}: duplicate domain_code {code}.")
            seen.add(key)

            normalized.append(
                {
                    "domain_code": code,
                    "domain_name": name,
                    "parent_code": parent_code,
                    "description": (row.get("description") or "").strip(),
                    "domain_image": (row.get("domain_image") or "").strip(),
                    "is_active": self._parse_bool(row.get("is_active"), default=True),
                }
            )

        codes = {row["domain_code"].lower() for row in normalized}
        for idx, row in enumerate(normalized, start=2):
            parent_code = row["parent_code"]
            if not parent_code:
                continue
            if parent_code.lower() == row["domain_code"].lower():
                raise CommandError(f"Row {idx}: domain cannot be its own parent.")
            if parent_code.lower() not in codes:
                parent = Domain.objects.filter(
                    domain_code__iexact=parent_code,
                    deleted=False,
                ).first()
                if parent is None:
                    raise CommandError(
                        f"Row {idx}: unknown parent_code {parent_code}."
                    )

        return normalized

    def _upsert_all_without_parents(self, *, rows: list[dict], user):
        domains_by_code = {}
        for row in rows:
            code = row["domain_code"]
            domain = Domain.objects.filter(domain_code__iexact=code).first()
            if domain is None:
                domain = Domain(domain_code=code)

            domain.domain_name = row["domain_name"]
            domain.description = row["description"]
            if row["domain_image"] or domain.pk is None:
                domain.domain_image = row["domain_image"]
            domain.is_active = row["is_active"]
            domain.deleted = False
            domain.save(user=user)
            domains_by_code[code.lower()] = domain

        return domains_by_code

    def _attach_parents(self, *, rows: list[dict], domains_by_code: dict, user) -> int:
        updated = 0
        for row in rows:
            domain = domains_by_code[row["domain_code"].lower()]
            parent_code = row["parent_code"]
            parent = domains_by_code.get(parent_code.lower()) if parent_code else None
            domain_service.assert_no_circular_parent(domain=domain, parent=parent)
            if domain.parent_id != (parent.id if parent else None):
                domain.parent = parent
                domain.save(user=user)
                updated += 1
        return updated

    def _parse_bool(self, value, *, default: bool) -> bool:
        if value in (None, ""):
            return default
        return str(value).strip().lower() in ("1", "true", "yes", "y")
