from __future__ import annotations

import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from assessment.models import Option, Question
from domain.models import Domain


DIMENSIONS = ("interest", "aptitude", "personality", "work_style")

SAMPLE_HEADERS = (
    "dimension",
    "question_text",
    "mapped_domains",
    "signal_strength",
    "is_active",
    "option_1",
    "option_2",
    "option_3",
    "option_4",
    "option_5",
)


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
            default=str(
                Path(settings.BASE_DIR)
                / "core"
                / "management"
                / "source"
                / "assessment_questions_sample.csv"
            ),
            help="Where to write/read the sample CSV.",
        )
        parser.add_argument(
            "--load",
            dest="load_path",
            default=None,
            help="Load questions/options from a CSV at this path.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Do not write anything, only print what would be created.",
        )

    def _write_sample_csv(self, *, sample_path: Path):
        sample_path.parent.mkdir(parents=True, exist_ok=True)
        with sample_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(SAMPLE_HEADERS)

    def _load_from_csv(self, *, load_path: Path, dry_run: bool):
        if not load_path.exists():
            raise FileNotFoundError(str(load_path))

        created_q = created_o = updated_q = updated_o = 0
        with load_path.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("CSV has no header row.")
            has_mapped_domains_column = "mapped_domains" in reader.fieldnames
            has_signal_strength_column = "signal_strength" in reader.fieldnames
            required_headers = (
                "dimension",
                "question_text",
                "is_active",
                "option_1",
                "option_2",
                "option_3",
                "option_4",
                "option_5",
            )
            missing = [h for h in required_headers if h not in reader.fieldnames]
            if missing:
                raise ValueError(f"Missing headers: {', '.join(missing)}")

            for idx, r in enumerate(reader, start=2):
                dim = (r.get("dimension") or "").strip()
                qt = (r.get("question_text") or "").strip()
                mapped_domains_raw = (r.get("mapped_domains") or "").strip()
                signal_strength_raw = (r.get("signal_strength") or "").strip()
                active_raw = (r.get("is_active") or "1").strip().lower()
                is_active = active_raw in ("1", "true", "yes", "y")

                if dim not in DIMENSIONS:
                    raise ValueError(f"Row {idx}: invalid dimension '{dim}'")
                if not qt:
                    raise ValueError(f"Row {idx}: question_text is required")
                try:
                    signal_strength = (
                        max(1, int(signal_strength_raw))
                        if has_signal_strength_column
                        else 1
                    )
                except ValueError as exc:
                    raise ValueError(
                        f"Row {idx}: signal_strength must be a positive integer"
                    ) from exc

                domain_codes = [
                    code.strip()
                    for code in mapped_domains_raw.split(",")
                    if code.strip()
                ]
                domain_ids = []
                if domain_codes:
                    domains = []
                    for code in domain_codes:
                        obj = Domain.objects.filter(
                            domain_code__iexact=code, deleted=False, is_active=True
                        ).first()
                        if obj:
                            domains.append(obj)
                    found_codes = {d.domain_code.lower() for d in domains}
                    missing_codes = [
                        c for c in domain_codes if c.lower() not in found_codes
                    ]
                    if missing_codes:
                        # Keep seeding usable even if domain master isn't loaded yet.
                        self.stdout.write(
                            self.style.WARNING(
                                f"Row {idx}: mapped_domains not found (skipping): {', '.join(missing_codes)}"
                            )
                        )
                    domain_ids = [d.id for d in domains]

                if dry_run:
                    self.stdout.write(
                        f"[DRY RUN] CSV Question: ({dim}) {qt} "
                        f"[signal_strength={signal_strength}, mapped_domains={domain_codes}]"
                    )
                    continue

                q, q_created = Question.objects.get_or_create(
                    dimension=dim,
                    question_text=qt,
                    defaults={
                        "is_active": is_active,
                        "signal_strength": (
                            signal_strength if has_signal_strength_column else 1
                        ),
                    },
                )
                if q_created:
                    created_q += 1
                else:
                    changed_fields = []
                    if q.is_active != is_active:
                        q.is_active = is_active
                        changed_fields.append("is_active")
                    if (
                        has_signal_strength_column
                        and q.signal_strength != signal_strength
                    ):
                        q.signal_strength = signal_strength
                        changed_fields.append("signal_strength")
                    if changed_fields:
                        q.save(update_fields=changed_fields)
                        updated_q += 1

                if has_mapped_domains_column:
                    if domain_ids:
                        q.mapped_domains.set(domain_ids)
                    else:
                        q.mapped_domains.clear()

                for i in range(1, 6):
                    cell = (r.get(f"option_{i}") or "").strip()
                    if not cell:
                        continue
                    if ":" not in cell:
                        score_value = i
                        label = cell.strip()
                    else:
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
        dry_run = bool(options.get("dry_run"))

        sample_path = Path(options["sample_path"])
        if options.get("write_sample"):
            self._write_sample_csv(sample_path=sample_path)
            self.stdout.write(
                self.style.SUCCESS(f"Sample CSV written: {sample_path.resolve()}")
            )
            return

        load_path_raw = options.get("load_path")
        load_path = Path(load_path_raw) if load_path_raw else sample_path
        result = self._load_from_csv(load_path=load_path, dry_run=dry_run)
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS("Dry run complete. No changes written.")
            )
            return
        created_q, updated_q, created_o, updated_o = result
        self.stdout.write(
            self.style.SUCCESS(
                "Seed complete (CSV): "
                f"questions(created={created_q}, updated={updated_q}) "
                f"options(created={created_o}, updated={updated_o})"
            )
        )
