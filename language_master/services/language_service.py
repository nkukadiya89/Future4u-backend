import csv
import io
import json
import logging
from typing import Any
from uuid import UUID

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from base import services as base_services
from language_master.models import Language, LanguageImportBatch, LanguageImportError

logger = logging.getLogger(__name__)

SAMPLE_CSV_HEADERS = ("name", "code", "description", "is_active")
REQUIRED_IMPORT_HEADERS = {"name", "code"}
HEADER_ALIASES = {
    "language_name": "name",
    "language_code": "code",
    "lang_code": "code",
    "lang_name": "name",
    "active": "is_active",
    "status": "is_active",
}


def language_base_queryset():
    return Language.objects.select_related("created_by", "updated_by")


def get_all(*, include_archived: bool = False):
    qs = language_base_queryset()
    if not include_archived:
        qs = qs.filter(deleted=False)
    return qs.order_by("name")


def get_by_code(*, code: str, include_archived: bool = False):
    qs = language_base_queryset().filter(code__iexact=code)
    if not include_archived:
        qs = qs.filter(deleted=False)
    return qs.first()


def case_insensitive_code_exists(*, code: str, exclude_pk: UUID | None = None) -> bool:
    q = Language.objects.filter(code__iexact=code)
    if exclude_pk:
        q = q.exclude(pk=exclude_pk)
    return q.exists()


def dropdown_languages():
    return (
        Language.objects.filter(is_active=True, deleted=False)
        .only("id", "code", "name")
        .order_by("name")
    )


@transaction.atomic
def create_language(*, user, validated_data: dict) -> Language:
    instance = Language(**validated_data)
    instance.save(user=user)
    return instance


@transaction.atomic
def update_language(*, language: Language, user, validated_data: dict) -> Language:
    for k, v in validated_data.items():
        setattr(language, k, v)
    language.save(user=user)
    return language


@transaction.atomic
def set_active_status(*, language: Language, user, is_active: bool) -> Language:
    language.is_active = is_active
    language.save(user=user)
    return language


@transaction.atomic
def archive_language(*, language: Language, user) -> Language:
    return base_services.soft_delete(language, user=user)


@transaction.atomic
def restore_language(*, language: Language, user) -> Language:
    return base_services.restore(language, user=user)


@transaction.atomic
def bulk_archive(*, ids: list, user) -> int:
    qs = Language.objects.filter(id__in=ids, deleted=False)
    count = 0
    for lang in qs:
        lang.soft_delete(user=user)
        count += 1
    return count


@transaction.atomic
def bulk_restore(*, ids: list, user) -> int:
    return Language.objects.filter(id__in=ids, deleted=True).update(
        deleted=False,
        deleted_at=None,
        deleted_by=None,
        updated_at=timezone.now(),
        updated_by=user,
    )


def normalize_import_row(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in row.items():
        kk = (str(k) if k is not None else "").strip()
        if not kk:
            continue
        key = HEADER_ALIASES.get(kk.lower(), kk.lower())
        out[key] = v
    for field in ("name", "code", "description"):
        if field in out and out[field] not in (None, ""):
            out[field] = str(out[field]).strip()
    if "is_active" in out and out["is_active"] not in ("", None):
        out["is_active"] = str(out["is_active"]).lower() in ("1", "true", "yes", "y")
    return out


def parse_import_file(uploaded) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    if not uploaded:
        return [], ["No file uploaded."]
    raw = uploaded.read()
    try:
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            return [], ["CSV has no header row."]
        normalized_headers = [
            HEADER_ALIASES.get(
                (str(h).strip().lower() if h else ""),
                (str(h).strip().lower() if h else ""),
            )
            for h in reader.fieldnames
        ]
        missing = sorted(REQUIRED_IMPORT_HEADERS - set(h for h in normalized_headers if h))
        if missing:
            return [], [f"Missing required headers: {', '.join(missing)}"]
        out_rows = []
        for r in reader:
            if not any((v or "").strip() for v in r.values()):
                continue
            out_rows.append(dict(r))
        return out_rows, errors
    except Exception as e:
        logger.exception("parse_import_file failed")
        return [], [str(e)]


@transaction.atomic
def bulk_import_rows(*, user, rows: list[dict], serializer_class, context: dict) -> LanguageImportBatch:
    batch = LanguageImportBatch.objects.create(created_by=user, total_rows=len(rows))
    imported = 0
    errors: list[LanguageImportError] = []
    seen_codes: set[str] = set()

    for idx, raw_row in enumerate(rows, start=1):
        row = normalize_import_row(dict(raw_row))
        row_code = (row.get("code") or "").strip().lower()
        if row_code:
            if row_code in seen_codes:
                errors.append(LanguageImportError(
                    batch=batch, row_number=idx,
                    message=f"Duplicate code in upload: {row_code}"[:500],
                    row_data=row,
                ))
                continue
            seen_codes.add(row_code)

        existing = Language.objects.filter(code__iexact=row_code).first() if row_code else None
        ser = serializer_class(instance=existing, data=row, partial=bool(existing), context=context)
        if not ser.is_valid():
            errors.append(LanguageImportError(
                batch=batch, row_number=idx,
                message=json.dumps(ser.errors)[:500],
                row_data=row,
            ))
            continue
        try:
            with transaction.atomic():
                obj = ser.save()
                if getattr(obj, "deleted", False):
                    obj.deleted = False
                    obj.deleted_at = None
                    obj.deleted_by = None
                    obj.updated_by = user
                    obj.updated_at = timezone.now()
                    obj.save(update_fields=["deleted", "deleted_at", "deleted_by", "updated_by", "updated_at"])
                imported += 1
        except Exception as e:
            errors.append(LanguageImportError(
                batch=batch, row_number=idx,
                message=str(e)[:500],
                row_data=row,
            ))

    if errors:
        LanguageImportError.objects.bulk_create(errors)
    batch.imported_count = imported
    batch.failed_count = len(errors)
    batch.completed_at = timezone.now()
    batch.save(update_fields=["imported_count", "failed_count", "completed_at"])
    return batch


def bulk_import_languages(*, user, rows: list[dict], serializer_class, context: dict) -> dict[str, Any]:
    batch = bulk_import_rows(user=user, rows=rows, serializer_class=serializer_class, context=context)
    err_qs = LanguageImportError.objects.filter(batch=batch).order_by("row_number")
    return {
        "success_count": batch.imported_count,
        "error_count": batch.failed_count,
        "error_details": [
            {"row": e.row_number, "message": e.message, "row_data": e.row_data}
            for e in err_qs.iterator(chunk_size=200)
        ],
        "batch_id": str(batch.id),
    }


def import_batches_queryset():
    return LanguageImportBatch.objects.select_related("created_by").order_by("-created_at")


def sample_csv_bytes() -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(SAMPLE_CSV_HEADERS)
    w.writerow(["English", "EN", "English language", "1"])
    w.writerow(["Hindi", "HI", "Hindi language", "1"])
    return buf.getvalue().encode("utf-8")
