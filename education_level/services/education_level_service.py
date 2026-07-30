import csv
import io
import json
import logging
from typing import Any
from uuid import UUID

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from education_level.models import (
    EducationLevel,
    EducationLevelImportBatch,
    EducationLevelImportError,
)

logger = logging.getLogger(__name__)

SAMPLE_CSV_HEADERS = (
    "level_code",
    "display_name",
    "sequence_order",
    "is_active",
)
REQUIRED_IMPORT_HEADERS = {
    "level_code",
    "display_name",
    "sequence_order",
}
HEADER_ALIASES = {
    "code": "level_code",
    "education_level_code": "level_code",
    "education_code": "level_code",
    "name": "display_name",
    "education_level_name": "display_name",
    "order": "sequence_order",
    "sequence": "sequence_order",
    "active": "is_active",
    "status": "is_active",
}

from common.services.import_file_parser import build_import_parser

parse_import_file = build_import_parser(HEADER_ALIASES, REQUIRED_IMPORT_HEADERS)


def education_level_base_queryset():
    return EducationLevel.objects.select_related("created_by", "updated_by")


def list_levels(*, include_archived: bool = False):
    qs = education_level_base_queryset()
    if not include_archived:
        qs = qs.filter(deleted=False)
    return qs.order_by("sequence_order", "display_name")


def get_level(*, pk: UUID, include_archived: bool = False):
    qs = education_level_base_queryset().filter(pk=pk)
    if not include_archived:
        qs = qs.filter(deleted=False)
    return qs.first()


def case_insensitive_code_exists(*, code: str, exclude_pk: UUID | None = None) -> bool:
    q = EducationLevel.objects.filter(level_code__iexact=code)
    if exclude_pk:
        q = q.exclude(pk=exclude_pk)
    return q.exists()


def sequence_exists(*, sequence_order: int, exclude_pk: UUID | None = None) -> bool:
    q = EducationLevel.objects.filter(sequence_order=sequence_order)
    if exclude_pk:
        q = q.exclude(pk=exclude_pk)
    return q.exists()


def blocking_foreign_key_usage(level: EducationLevel) -> str | None:
    for rel in level._meta.related_objects:
        accessor = rel.get_accessor_name()
        try:
            related = getattr(level, accessor)
        except Exception:
            continue
        if hasattr(related, "exists"):
            if related.exists():
                return rel.related_model.__name__
        elif related is not None:
            return rel.related_model.__name__
    return None


def validate_level_data(
    *, data: dict[str, Any], instance: EducationLevel | None = None
) -> dict[str, Any]:
    code = (data.get("level_code") or "").strip().lower()
    if not code:
        raise ValidationError({"level_code": "This field may not be blank."})
    name = (data.get("display_name") or "").strip()
    if not name:
        raise ValidationError({"display_name": "This field may not be blank."})
    sequence_order = data.get("sequence_order")
    if sequence_order is None:
        raise ValidationError({"sequence_order": "This field is required."})

    try:
        sequence_order = int(sequence_order)
    except (TypeError, ValueError):
        raise ValidationError({"sequence_order": "A valid integer is required."})

    exclude_pk = instance.pk if instance and instance.pk else None
    if case_insensitive_code_exists(code=code, exclude_pk=exclude_pk):
        raise ValidationError(
            {"level_code": "Level code must be unique (case-insensitive)."}
        )
    if sequence_exists(sequence_order=sequence_order, exclude_pk=exclude_pk):
        raise ValidationError({"sequence_order": "Sequence order must be unique."})

    return {
        "level_code": code,
        "display_name": name,
        "sequence_order": sequence_order,
        "is_active": bool(data.get("is_active", True)),
    }


@transaction.atomic
def create_level(*, user, validated_data: dict) -> EducationLevel:
    instance = EducationLevel(**validated_data)
    instance.save(user=user)
    return instance


@transaction.atomic
def update_level(
    *, level: EducationLevel, user, validated_data: dict
) -> EducationLevel:
    for k, v in validated_data.items():
        setattr(level, k, v)
    level.save(user=user)
    return level


def assert_can_archive(level: EducationLevel):
    blocker = blocking_foreign_key_usage(level)
    if blocker:
        raise ValidationError(f"Cannot archive: referenced by {blocker}.")


@transaction.atomic
def archive_level(*, level: EducationLevel, user) -> EducationLevel:
    assert_can_archive(level)
    level.soft_delete(user=user)
    return level


@transaction.atomic
def restore_level(*, level: EducationLevel, user) -> EducationLevel:
    level.deleted = False
    level.deleted_at = None
    level.deleted_by = None
    level.updated_at = timezone.now()
    level.updated_by = user
    level.save(
        update_fields=[
            "deleted",
            "deleted_at",
            "deleted_by",
            "updated_at",
            "updated_by",
        ]
    )
    return level


@transaction.atomic
def bulk_archive(*, ids: list, user) -> int:
    if not ids:
        raise ValidationError({"ids": "This field is required."})
    qs = EducationLevel.objects.filter(id__in=ids, deleted=False)
    count = 0
    for level in qs:
        assert_can_archive(level)
        level.soft_delete(user=user)
        count += 1
    return count


@transaction.atomic
def bulk_restore(*, ids: list, user) -> int:
    if not ids:
        raise ValidationError({"ids": "This field is required."})
    return EducationLevel.objects.filter(id__in=ids, deleted=True).update(
        deleted=False,
        deleted_at=None,
        deleted_by=None,
        updated_at=timezone.now(),
        updated_by=user,
    )


@transaction.atomic
def set_active_status(
    *, level: EducationLevel, user, is_active: bool
) -> EducationLevel:
    level.is_active = is_active
    level.save(user=user)
    return level


@transaction.atomic
def bulk_set_active(*, ids: list, user, is_active: bool) -> int:
    if not ids:
        return 0
    return EducationLevel.objects.filter(id__in=ids).update(
        is_active=is_active,
        updated_at=timezone.now(),
        updated_by=user,
    )


def dropdown_levels():
    return (
        EducationLevel.objects.filter(is_active=True, deleted=False)
        .only("id", "level_code", "display_name", "sequence_order")
        .order_by("sequence_order", "display_name")
    )


@transaction.atomic
def reorder_levels(*, orders: list[dict], user) -> int:
    if not orders:
        raise ValidationError({"orders": "This field is required."})

    id_list = [row.get("id") for row in orders]
    if any(v in (None, "") for v in id_list):
        raise ValidationError({"orders": "Each row must include id."})
    seq_list = [row.get("sequence_order") for row in orders]
    try:
        seq_list = [int(v) for v in seq_list]
    except (TypeError, ValueError):
        raise ValidationError({"orders": "Each sequence_order must be an integer."})
    if len(set(seq_list)) != len(seq_list):
        raise ValidationError({"orders": "Duplicate sequence_order values provided."})

    existing = EducationLevel.objects.filter(id__in=id_list, deleted=False).only(
        "id", "sequence_order"
    )
    if existing.count() != len(id_list):
        raise ValidationError({"orders": "Some ids are invalid or archived."})

    unaffected = (
        EducationLevel.objects.filter(deleted=False)
        .exclude(id__in=id_list)
        .values_list("sequence_order", flat=True)
    )
    unaffected_set = set(unaffected)
    conflict = [v for v in seq_list if v in unaffected_set]
    if conflict:
        raise ValidationError(
            {"orders": f"Sequence order already exists: {sorted(set(conflict))}"}
        )

    by_id = {str(obj.id): obj for obj in existing}
    updated = 0
    for row in orders:
        obj = by_id.get(str(row["id"]))
        if obj is None:
            continue
        new_seq = int(row["sequence_order"])
        if obj.sequence_order != new_seq:
            obj.sequence_order = new_seq
            obj.save(user=user)
            updated += 1
    return updated


def normalize_import_row(row: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in row.items():
        kk = (str(k) if k is not None else "").strip()
        if not kk:
            continue
        key = HEADER_ALIASES.get(kk.lower(), kk.lower())
        out[key] = v
    for k in ("sequence_order",):
        if k in out and out[k] not in ("", None):
            if isinstance(out[k], int):
                continue
            try:
                out[k] = int(float(str(out[k]).strip()))
            except (TypeError, ValueError):
                raise ValueError(f"Invalid {k}")
    if "is_active" in out and out["is_active"] not in ("", None):
        v = str(out["is_active"]).lower()
        out["is_active"] = v in ("1", "true", "yes", "y")
    return out


def bulk_import_rows(
    *, user, rows: list[dict], serializer_class, context: dict
) -> EducationLevelImportBatch:
    batch = EducationLevelImportBatch.objects.create(
        created_by=user,
        total_rows=len(rows),
    )
    imported = 0
    errors: list[EducationLevelImportError] = []
    seen_codes: set[str] = set()
    for idx, raw_row in enumerate(rows, start=1):
        row = dict(raw_row)
        try:
            row = normalize_import_row(row)
        except ValueError as e:
            errors.append(
                EducationLevelImportError(
                    batch=batch,
                    row_number=idx,
                    message=str(e)[:500],
                    row_data=dict(raw_row) if isinstance(raw_row, dict) else {},
                )
            )
            continue
        existing = None
        level_code = (row.get("level_code") or "").strip().lower()
        if level_code:
            if level_code in seen_codes:
                errors.append(
                    EducationLevelImportError(
                        batch=batch,
                        row_number=idx,
                        message="Duplicate level_code in import file",
                        row_data=row if isinstance(row, dict) else {},
                    )
                )
                continue
            seen_codes.add(level_code)
        if level_code:
            existing = EducationLevel.objects.filter(
                level_code__iexact=level_code
            ).first()
        ser = serializer_class(
            instance=existing, data=row, partial=bool(existing), context=context
        )
        if not ser.is_valid():
            msg = json.dumps(ser.errors)[:500]
            errors.append(
                EducationLevelImportError(
                    batch=batch,
                    row_number=idx,
                    message=msg[:500],
                    row_data=row if isinstance(row, dict) else {},
                )
            )
            continue
        try:
            with transaction.atomic():
                obj = ser.save()
                # If an existing archived record is re-imported, restore it.
                if getattr(obj, "deleted", False):
                    obj.deleted = False
                    obj.deleted_at = None
                    obj.deleted_by = None
                    obj.updated_by = user
                    obj.updated_at = timezone.now()
                    obj.save(
                        update_fields=[
                            "deleted",
                            "deleted_at",
                            "deleted_by",
                            "updated_by",
                            "updated_at",
                        ]
                    )
                imported += 1
        except ValidationError as e:
            detail = e.detail
            if isinstance(detail, (dict, list)):
                msg = json.dumps(detail)[:500]
            else:
                msg = str(detail)[:500]
            errors.append(
                EducationLevelImportError(
                    batch=batch,
                    row_number=idx,
                    message=msg,
                    row_data=row if isinstance(row, dict) else {},
                )
            )
        except Exception as e:
            logger.exception("bulk row %s", idx)
            errors.append(
                EducationLevelImportError(
                    batch=batch,
                    row_number=idx,
                    message=str(e)[:500],
                    row_data=row if isinstance(row, dict) else {},
                )
            )
    if errors:
        EducationLevelImportError.objects.bulk_create(errors)
    batch.imported_count = imported
    batch.failed_count = len(errors)
    batch.completed_at = timezone.now()
    batch.save(update_fields=["imported_count", "failed_count", "completed_at"])
    return batch


def bulk_import_levels(
    *, user, rows: list[dict], serializer_class, context: dict
) -> dict[str, Any]:
    batch = bulk_import_rows(
        user=user,
        rows=rows,
        serializer_class=serializer_class,
        context=context,
    )
    err_qs = EducationLevelImportError.objects.filter(batch=batch).order_by(
        "row_number"
    )
    error_details = [
        {"row": e.row_number, "message": e.message, "row_data": e.row_data}
        for e in err_qs.iterator(chunk_size=200)
    ]
    return {
        "success_count": batch.imported_count,
        "error_count": batch.failed_count,
        "error_details": error_details,
        "batch_id": str(batch.id),
    }


def import_batches_queryset():
    return EducationLevelImportBatch.objects.select_related("created_by").order_by(
        "-created_at"
    )


def import_errors_queryset(*, batch_id: UUID | None = None):
    qs = EducationLevelImportError.objects.select_related("batch").order_by(
        "-batch__created_at", "row_number"
    )
    if batch_id:
        qs = qs.filter(batch_id=batch_id)
    return qs


def error_report_csv_bytes(*, batch_id: UUID | None = None) -> tuple[str, bytes]:
    qs = import_errors_queryset(batch_id=batch_id)
    if batch_id is None:
        first = qs.first()
        if not first:
            return "education_level_import_errors_empty.csv", b"row_number,message\n"
        qs = import_errors_queryset(batch_id=first.batch_id)
        filename = f"education_level_import_errors_{first.batch_id}.csv"
    else:
        filename = f"education_level_import_errors_{batch_id}.csv"
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["row_number", "message", "row_data"])
    for er in qs.iterator(chunk_size=200):
        w.writerow([er.row_number, er.message, er.row_data])
    return filename, buf.getvalue().encode("utf-8")


def sample_csv_bytes() -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(SAMPLE_CSV_HEADERS)
    w.writerow(["primary", "Primary School", "1", "1"])
    w.writerow(["secondary", "Secondary School (10th)", "2", "1"])
    w.writerow(["higher_secondary_11", "Higher Secondary (11th)", "3", "1"])
    w.writerow(["higher_secondary", "Higher Secondary (12th)", "4", "1"])
    return buf.getvalue().encode("utf-8")
