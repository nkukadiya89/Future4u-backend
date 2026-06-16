from __future__ import annotations

import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from assessment.models import Option, Question
from domain.models import Domain

DIMENSIONS = ("interest", "aptitude", "personality", "work_style")


class Command(BaseCommand):
    help = "Seed Assessment Questions + Options (idempotent) for testing flows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sample-path",
            default=str(
                Path(settings.BASE_DIR)
                / "core" / "management" / "source" / "assessment_questions_sample.csv"
            ),
            help="Where to write/read the sample CSV.",
        )
        parser.add_argument(
            "--load", dest="load_path", default=None,
            help="Load questions/options from a CSV at this path.",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Do not write anything, only print what would be created.",
        )

    def _parse_row(self, r: dict, idx: int, col_flags: dict) -> dict | None:
        dim = (r.get("dimension") or "").strip()
        qt = (r.get("question_text") or "").strip()
        if not dim or dim.startswith("#") or not qt or qt.startswith("#"):
            return None
        if dim not in DIMENSIONS:
            raise ValueError(f"Row {idx}: invalid dimension '{dim}'")
        if not qt:
            raise ValueError(f"Row {idx}: question_text is required")

        active_raw = (r.get("is_active") or "1").strip().lower()
        is_active = active_raw in ("1", "true", "yes", "y")
        signal_strength_raw = (r.get("signal_strength") or "").strip()
        try:
            signal_strength = (
                max(1, int(signal_strength_raw))
                if col_flags["has_signal_strength_column"] else 1
            )
        except ValueError as exc:
            raise ValueError(f"Row {idx}: signal_strength must be a positive integer") from exc

        # Support both | and , as separators for domain codes
        mapped_domains_raw = (r.get("mapped_domains") or "").strip()
        sep = "|" if "|" in mapped_domains_raw else ","
        domain_codes = [code.strip() for code in mapped_domains_raw.split(sep) if code.strip()]

        question_type = (
            (r.get("question_type") or "scale").strip().lower()
            if col_flags["has_question_type_column"] else "scale"
        )
        if question_type not in {Question.QuestionType.SCALE, Question.QuestionType.MCQ, Question.QuestionType.YESNO}:
            raise ValueError(f"Row {idx}: unsupported question_type '{question_type}'")

        mapped_streams_raw = (
            (r.get("mapped_streams") or "").strip()
            if col_flags["has_mapped_streams_column"] else ""
        )
        education_level_code = (
            (r.get("education_level") or "").strip()
            if col_flags["has_education_level_column"] else ""
        )
        target_stream_code = (
            (r.get("target_stream") or "").strip()
            if col_flags["has_target_stream_column"] else ""
        )
        sequence_order_raw = (
            (r.get("sequence_order") or "0").strip()
            if col_flags["has_sequence_order_column"] else "0"
        )
        try:
            sequence_order = int(sequence_order_raw) if sequence_order_raw else 0
        except ValueError:
            sequence_order = 0

        return {
            "dim": dim, "qt": qt, "is_active": is_active,
            "signal_strength": signal_strength, "domain_codes": domain_codes,
            "question_type": question_type,
            "mapped_streams_raw": mapped_streams_raw,
            "education_level_code": education_level_code,
            "target_stream_code": target_stream_code,
            "sequence_order": sequence_order,
            "option_texts": [(r.get(f"option_{i}_text") or "").strip() for i in range(1, 5)],
        }

    def _resolve_relations(self, parsed: dict, idx: int) -> dict | None:
        domain_ids = []
        if parsed["domain_codes"]:
            domains = []
            for code in parsed["domain_codes"]:
                obj = Domain.objects.filter(
                    domain_code__iexact=code, deleted=False, is_active=True
                ).first()
                if obj:
                    domains.append(obj)
            found_codes = {d.domain_code.lower() for d in domains}
            missing_codes = [c for c in parsed["domain_codes"] if c.lower() not in found_codes]
            if missing_codes:
                self.stdout.write(
                    self.style.WARNING(
                        f"Row {idx}: mapped_domains not found (skipping): {', '.join(missing_codes)}"
                    )
                )
                return None
            domain_ids = [d.id for d in domains]

        education_level_obj = None
        if parsed["education_level_code"]:
            from education_level.models import EducationLevel
            education_level_obj = EducationLevel.objects.filter(
                level_code__iexact=parsed["education_level_code"]
            ).first()

        target_stream_obj = None
        if parsed["target_stream_code"]:
            from stream.models import Stream
            target_stream_obj = Stream.objects.filter(
                stream_code__iexact=parsed["target_stream_code"], deleted=False
            ).first()

        stream_ids = []
        if parsed["mapped_streams_raw"]:
            from stream.models import Stream
            for sc in [s.strip() for s in parsed["mapped_streams_raw"].split("|") if s.strip()]:
                s_obj = Stream.objects.filter(stream_code__iexact=sc, deleted=False).first()
                if s_obj:
                    stream_ids.append(s_obj.id)

        return {
            "domain_ids": domain_ids, "stream_ids": stream_ids,
            "education_level_obj": education_level_obj,
            "target_stream_obj": target_stream_obj,
        }

    def _create_or_update_question(self, parsed: dict, relations: dict, col_flags: dict) -> tuple:
        defaults = {
            "is_active": parsed["is_active"],
            "signal_strength": parsed["signal_strength"],
            "question_type": parsed["question_type"],
            "sequence_order": parsed["sequence_order"],
            "education_level": relations["education_level_obj"],
            "target_stream": relations["target_stream_obj"],
        }

        q = None
        if col_flags["has_sequence_order_column"] and parsed["sequence_order"]:
            matches = Question.objects.filter(
                dimension=parsed["dim"], sequence_order=parsed["sequence_order"]
            )
            q = matches.filter(question_text=parsed["qt"]).first() or matches.first()
        if not q and not (col_flags["has_sequence_order_column"] and parsed["sequence_order"]):
            q = Question.objects.filter(dimension=parsed["dim"], question_text=parsed["qt"]).first()

        if q:
            changed_fields = []
            if q.question_text != parsed["qt"]:
                q.question_text = parsed["qt"]
                changed_fields.append("question_text")
            if q.is_active != parsed["is_active"]:
                q.is_active = parsed["is_active"]
                changed_fields.append("is_active")
            if col_flags["has_signal_strength_column"] and q.signal_strength != parsed["signal_strength"]:
                q.signal_strength = parsed["signal_strength"]
                changed_fields.append("signal_strength")
            if q.question_type != parsed["question_type"]:
                q.question_type = parsed["question_type"]
                changed_fields.append("question_type")
            if q.sequence_order != parsed["sequence_order"]:
                q.sequence_order = parsed["sequence_order"]
                changed_fields.append("sequence_order")
            if q.education_level_id != (relations["education_level_obj"].id if relations["education_level_obj"] else None):
                q.education_level = relations["education_level_obj"]
                changed_fields.append("education_level")
            if q.target_stream_id != (relations["target_stream_obj"].id if relations["target_stream_obj"] else None):
                q.target_stream = relations["target_stream_obj"]
                changed_fields.append("target_stream")
            if changed_fields:
                q.save(update_fields=changed_fields)
            return q, False, bool(changed_fields)

        q = Question.objects.create(dimension=parsed["dim"], question_text=parsed["qt"], **defaults)
        return q, True, True

    def _sync_m2m(self, q: Question, relations: dict, col_flags: dict):
        if col_flags["has_mapped_domains_column"]:
            if relations["domain_ids"]:
                q.mapped_domains.set(relations["domain_ids"])
            else:
                q.mapped_domains.clear()
        if col_flags["has_mapped_streams_column"]:
            if relations["stream_ids"]:
                q.mapped_streams.set(relations["stream_ids"])
            else:
                q.mapped_streams.clear()

    def _create_or_update_options(self, q: Question, parsed: dict) -> tuple[int, int]:
        created_o = updated_o = 0
        for i in range(1, 5):
            label = parsed["option_texts"][i - 1]
            if not label:
                continue
            o, o_created = Option.objects.get_or_create(
                question=q, sequence_order=i, defaults={"option_text": label},
            )
            if o_created:
                created_o += 1
            elif o.option_text != label:
                o.option_text = label
                o.save(update_fields=["option_text"])
                updated_o += 1

        stale_options = q.options.exclude(sequence_order__in=[1, 2, 3, 4])
        deleted = stale_options.count()
        if deleted:
            stale_options.delete()
            updated_o += deleted
        return created_o, updated_o

    def _load_from_csv(self, *, load_path: Path, dry_run: bool):
        if not load_path.exists():
            raise FileNotFoundError(str(load_path))

        created_q = updated_q = created_o = updated_o = 0
        dry_run_count = 0
        dry_run_dimensions = {dim: 0 for dim in DIMENSIONS}

        with load_path.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("CSV has no header row.")

            col_flags = {
                "has_mapped_domains_column": "mapped_domains" in reader.fieldnames,
                "has_signal_strength_column": "signal_strength" in reader.fieldnames,
                "has_question_type_column": "question_type" in reader.fieldnames,
                "has_mapped_streams_column": "mapped_streams" in reader.fieldnames,
                "has_education_level_column": "education_level" in reader.fieldnames,
                "has_target_stream_column": "target_stream" in reader.fieldnames,
                "has_sequence_order_column": "sequence_order" in reader.fieldnames,
            }

            if not all(h in reader.fieldnames for h in ("option_1_text", "option_2_text", "option_3_text", "option_4_text")):
                raise ValueError("Missing option headers. Expected option_1_text .. option_4_text columns.")

            missing = [h for h in ("dimension", "question_text", "is_active") if h not in reader.fieldnames]
            if missing:
                raise ValueError(f"Missing headers: {', '.join(missing)}")

            for idx, r in enumerate(reader, start=2):
                parsed = self._parse_row(r, idx, col_flags)
                if parsed is None:
                    continue

                relations = self._resolve_relations(parsed, idx)
                if relations is None:
                    continue

                if dry_run:
                    dry_run_count += 1
                    dry_run_dimensions[parsed["dim"]] = dry_run_dimensions.get(parsed["dim"], 0) + 1
                    continue

                q, was_created, did_update = self._create_or_update_question(parsed, relations, col_flags)
                if was_created:
                    created_q += 1
                elif did_update:
                    updated_q += 1

                self._sync_m2m(q, relations, col_flags)
                oc, ou = self._create_or_update_options(q, parsed)
                created_o += oc
                updated_o += ou

        if dry_run:
            return dry_run_count, dry_run_dimensions
        return created_q, updated_q, created_o, updated_o

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        sample_path = Path(options["sample_path"])
        load_path = Path(options["load_path"]) if options.get("load_path") else sample_path
        result = self._load_from_csv(load_path=load_path, dry_run=dry_run)

        if dry_run:
            count, dimensions = result
            summary = ", ".join(f"{d}={c}" for d, c in dimensions.items() if c)
            msg = f"Dry run complete. No changes written. CSV questions checked={count}"
            if summary:
                msg += f" ({summary})"
            self.stdout.write(self.style.SUCCESS(msg))
            return

        cq, uq, co, uo = result
        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete (CSV): questions(created={cq}, updated={uq}) options(created={co}, updated={uo})"
            )
        )
