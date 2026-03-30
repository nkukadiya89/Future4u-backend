from __future__ import annotations

import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from assessment.models import Option, Question


DEFAULT_OPTIONS = [
    (1, "Strongly Disagree"),
    (2, "Disagree"),
    (3, "Neutral"),
    (4, "Agree"),
    (5, "Strongly Agree"),
]

DIMENSIONS = ("interest", "aptitude", "personality", "work_style")

SAMPLE_HEADERS = (
    "dimension",
    "question_text",
    "is_active",
    "option_1",
    "option_2",
    "option_3",
    "option_4",
    "option_5",
)


def _question_text(*, dimension: str, idx: int) -> str:
    if dimension == "interest":
        return f"I enjoy activities related to this field. (Q{idx})"
    if dimension == "aptitude":
        return f"I learn skills in this area quickly. (Q{idx})"
    if dimension == "personality":
        return f"My personality fits well with work in this area. (Q{idx})"
    if dimension == "work_style":
        return f"My preferred work style matches roles in this area. (Q{idx})"
    return f"{dimension.title()} question (Q{idx})"


class Command(BaseCommand):
    help = "Seed Assessment Questions + Options (idempotent) for testing flows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--write-sample",
            action="store_true",
            help="Write a sample CSV file (does not touch DB).",
        )
        parser.add_argument(
            "--sample-path",
            default=str(Path(settings.BASE_DIR) / "core" / "management" / "source" / "assessment_questions_sample.csv"),
            help="Where to write/read the sample CSV.",
        )
        parser.add_argument(
            "--load",
            dest="load_path",
            default=None,
            help="Load questions/options from a CSV at this path.",
        )
        parser.add_argument(
            "--per-dimension",
            type=int,
            default=6,
            help="How many questions to create per dimension (default: 6).",
        )
        parser.add_argument(
            "--inactive",
            action="store_true",
            help="Create seeded questions as inactive (default: active).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Do not write anything, only print what would be created.",
        )

    def _write_sample_csv(self, *, sample_path: Path, per_dimension: int, is_active: bool):
        sample_path.parent.mkdir(parents=True, exist_ok=True)
        with sample_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(SAMPLE_HEADERS)
            for dim in DIMENSIONS:
                for i in range(1, per_dimension + 1):
                    qt = _question_text(dimension=dim, idx=i)
                    row = [dim, qt, "1" if is_active else "0"]
                    for score_value, option_text in DEFAULT_OPTIONS:
                        row.append(f"{score_value}:{option_text}")
                    w.writerow(row)

    def _load_from_csv(self, *, load_path: Path, dry_run: bool):
        if not load_path.exists():
            raise FileNotFoundError(str(load_path))

        created_q = created_o = updated_q = updated_o = 0
        with load_path.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("CSV has no header row.")
            missing = [h for h in SAMPLE_HEADERS if h not in reader.fieldnames]
            if missing:
                raise ValueError(f"Missing headers: {', '.join(missing)}")

            for idx, r in enumerate(reader, start=2):
                dim = (r.get("dimension") or "").strip()
                qt = (r.get("question_text") or "").strip()
                active_raw = (r.get("is_active") or "1").strip().lower()
                is_active = active_raw in ("1", "true", "yes", "y")

                if dim not in DIMENSIONS:
                    raise ValueError(f"Row {idx}: invalid dimension '{dim}'")
                if not qt:
                    raise ValueError(f"Row {idx}: question_text is required")

                if dry_run:
                    self.stdout.write(f"[DRY RUN] CSV Question: ({dim}) {qt}")
                    continue

                q, q_created = Question.objects.get_or_create(
                    dimension=dim,
                    question_text=qt,
                    defaults={"is_active": is_active},
                )
                if q_created:
                    created_q += 1
                else:
                    if q.is_active != is_active:
                        q.is_active = is_active
                        q.save(update_fields=["is_active"])
                        updated_q += 1

                for i in range(1, 6):
                    cell = (r.get(f"option_{i}") or "").strip()
                    if not cell:
                        continue
                    if ":" not in cell:
                        raise ValueError(f"Row {idx}: option_{i} must be formatted 'score:label'")
                    score_str, label = cell.split(":", 1)
                    score_value = int(score_str.strip())
                    label = label.strip()
                    if score_value < 1 or score_value > 5:
                        raise ValueError(f"Row {idx}: option score must be 1..5")
                    if not label:
                        raise ValueError(f"Row {idx}: option label cannot be blank")

                    o, o_created = Option.objects.get_or_create(
                        question=q,
                        score_value=score_value,
                        defaults={"option_text": label},
                    )
                    if o_created:
                        created_o += 1
                    else:
                        if o.option_text != label:
                            o.option_text = label
                            o.save(update_fields=["option_text"])
                            updated_o += 1

        if dry_run:
            return None
        return created_q, updated_q, created_o, updated_o

    @transaction.atomic
    def handle(self, *args, **options):
        per_dimension = int(options["per_dimension"])
        is_active = not bool(options.get("inactive"))
        dry_run = bool(options.get("dry_run"))

        sample_path = Path(options["sample_path"])
        if options.get("write_sample"):
            if per_dimension <= 0:
                self.stdout.write(self.style.WARNING("Nothing to do: --per-dimension must be > 0"))
                return
            self._write_sample_csv(sample_path=sample_path, per_dimension=per_dimension, is_active=is_active)
            self.stdout.write(self.style.SUCCESS(f"Sample CSV written: {sample_path.resolve()}"))
            return

        load_path_raw = options.get("load_path")
        if load_path_raw:
            result = self._load_from_csv(load_path=Path(load_path_raw), dry_run=dry_run)
            if dry_run:
                self.stdout.write(self.style.SUCCESS("Dry run complete. No changes written."))
                return
            created_q, updated_q, created_o, updated_o = result
            self.stdout.write(
                self.style.SUCCESS(
                    "Seed complete (CSV): "
                    f"questions(created={created_q}, updated={updated_q}) "
                    f"options(created={created_o}, updated={updated_o})"
                )
            )
            return

        if per_dimension <= 0:
            self.stdout.write(self.style.WARNING("Nothing to do: --per-dimension must be > 0"))
            return

        created_q = 0
        created_o = 0
        updated_q = 0
        updated_o = 0

        for dim in DIMENSIONS:
            for i in range(1, per_dimension + 1):
                qt = _question_text(dimension=dim, idx=i)

                if dry_run:
                    self.stdout.write(f"[DRY RUN] Question: ({dim}) {qt}")
                    continue

                q, was_created = Question.objects.get_or_create(
                    dimension=dim,
                    question_text=qt,
                    defaults={"is_active": is_active},
                )
                if was_created:
                    created_q += 1
                else:
                    if q.is_active != is_active:
                        q.is_active = is_active
                        q.save(update_fields=["is_active"])
                        updated_q += 1

                for score_value, option_text in DEFAULT_OPTIONS:
                    o, o_created = Option.objects.get_or_create(
                        question=q,
                        score_value=score_value,
                        defaults={"option_text": option_text},
                    )
                    if o_created:
                        created_o += 1
                    else:
                        if o.option_text != option_text:
                            o.option_text = option_text
                            o.save(update_fields=["option_text"])
                            updated_o += 1

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry run complete. No changes written."))
            return

        self.stdout.write(
            self.style.SUCCESS(
                "Seed complete: "
                f"questions(created={created_q}, updated={updated_q}) "
                f"options(created={created_o}, updated={updated_o})"
            )
        )

