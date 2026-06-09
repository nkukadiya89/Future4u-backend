from __future__ import annotations

import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from assessment.models import Option, Question, UserResponse
from domain.models import Domain


# Only keep the 4 UI dimensions (3 questions per dimension).
DIMENSIONS = ("interest", "aptitude", "personality", "work_style")
RETIRED_DOMAIN_PERSONALITY_OPTION_TEXTS = {
    "I may stop if it feels too hard",
    "I would continue with guidance",
    "I would break it down and keep trying",
    "I enjoy working through difficult learning",
}

SAMPLE_HEADERS = (
    "dimension",
    "question_text",
    "question_type",
    "mapped_domains",
    "mapped_streams",
    "signal_strength",
    "is_active",
    "education_level",
    "target_stream",
    "sequence_order",
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
        parser.add_argument(
            "--prune-existing",
            action="store_true",
            help=(
                "Before loading, deactivate existing questions in the 4 supported dimensions "
                "for any domains mentioned in the CSV. Use this when refreshing CSV-backed "
                "MCQ questions for a domain/category."
            ),
        )

    def _write_sample_csv(self, *, sample_path: Path):
        sample_path.parent.mkdir(parents=True, exist_ok=True)
        with sample_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(SAMPLE_HEADERS)

    def _load_from_csv(self, *, load_path: Path, dry_run: bool, prune_existing: bool):
        if not load_path.exists():
            raise FileNotFoundError(str(load_path))

        created_q = created_o = updated_q = updated_o = 0
        dry_run_count = 0
        dry_run_dimensions = {dimension: 0 for dimension in DIMENSIONS}
        current_question_keys = set()
        with load_path.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("CSV has no header row.")
            has_mapped_domains_column = "mapped_domains" in reader.fieldnames
            has_signal_strength_column = "signal_strength" in reader.fieldnames
            has_question_type_column = "question_type" in reader.fieldnames
            has_mapped_streams_column = "mapped_streams" in reader.fieldnames
            has_education_level_column = "education_level" in reader.fieldnames
            has_target_stream_column = "target_stream" in reader.fieldnames
            has_sequence_order_column = "sequence_order" in reader.fieldnames
            # Support 2 CSV option formats:
            # 1) Legacy: option_1..option_5 where each cell is either "label" or "score: label"
            # 2) Split: option_1_text, option_1_score, ..., option_4_text, option_4_score
            required_base_headers = ("dimension", "question_text", "is_active")
            missing_base = [
                h for h in required_base_headers if h not in reader.fieldnames
            ]
            if missing_base:
                raise ValueError(f"Missing headers: {', '.join(missing_base)}")

            has_legacy_options = all(
                h in reader.fieldnames
                for h in ("option_1", "option_2", "option_3", "option_4")
            )
            has_split_options = all(
                h in reader.fieldnames
                for h in (
                    "option_1_text",
                    "option_2_text",
                    "option_3_text",
                    "option_4_text",
                )
            )
            if not (has_legacy_options or has_split_options):
                raise ValueError(
                    "Missing option headers. Provide either option_1..option_5 columns "
                    "or option_1_text .. option_4_text columns."
                )

            # Optionally prune existing questions for the domains in this CSV
            if prune_existing and not dry_run and has_mapped_domains_column:
                codes: set[str] = set()
                for row in reader:
                    mapped = (row.get("mapped_domains") or "").strip()
                    if not mapped:
                        continue
                    sep = "|" if "|" in mapped else ","
                    for code in [c.strip() for c in mapped.split(sep) if c.strip()]:
                        codes.add(code)

                if codes:
                    domain_ids_to_prune = list(
                        Domain.objects.filter(
                            domain_code__in=list(codes),
                            deleted=False,
                            is_active=True,
                        ).values_list("id", flat=True)
                    )
                    if domain_ids_to_prune:
                        # Deactivate questions mapped to these domains in our supported dimensions.
                        Question.objects.filter(
                            mapped_domains__id__in=domain_ids_to_prune,
                            dimension__in=DIMENSIONS,
                        ).update(is_active=False)

                # Rewind to the start for actual load
                f.seek(0)
                reader = csv.DictReader(f)

            for idx, r in enumerate(reader, start=2):
                dim = (r.get("dimension") or "").strip()
                qt = (r.get("question_text") or "").strip()
                mapped_domains_raw = (r.get("mapped_domains") or "").strip()
                signal_strength_raw = (r.get("signal_strength") or "").strip()
                active_raw = (r.get("is_active") or "1").strip().lower()
                is_active = active_raw in ("1", "true", "yes", "y")

                # Skip blank rows and comment lines
                if not dim or dim.startswith("#"):
                    continue
                if not qt or qt.startswith("#"):
                    continue

                if dim not in DIMENSIONS:
                    raise ValueError(f"Row {idx}: invalid dimension '{dim}'")
                if not qt:
                    raise ValueError(f"Row {idx}: question_text is required")
                current_question_keys.add((dim, qt))
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

                # Support both | and , as separators
                sep = "|" if "|" in mapped_domains_raw else ","
                domain_codes = [
                    code.strip()
                    for code in mapped_domains_raw.split(sep)
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
                        self.stdout.write(
                            self.style.WARNING(
                                f"Row {idx}: mapped_domains not found (skipping): {', '.join(missing_codes)}"
                            )
                        )
                        continue
                    domain_ids = [d.id for d in domains]

                # Parse extra columns
                question_type = (
                    (r.get("question_type") or "scale").strip().lower()
                    if has_question_type_column
                    else "scale"
                )
                allowed_question_types = {
                    Question.QuestionType.SCALE,
                    Question.QuestionType.MCQ,
                    Question.QuestionType.YESNO,
                }
                if question_type not in allowed_question_types:
                    raise ValueError(
                        f"Row {idx}: unsupported question_type '{question_type}'"
                    )
                mapped_streams_raw = (
                    (r.get("mapped_streams") or "").strip()
                    if has_mapped_streams_column
                    else ""
                )
                education_level_code = (
                    (r.get("education_level") or "").strip()
                    if has_education_level_column
                    else ""
                )
                target_stream_code = (
                    (r.get("target_stream") or "").strip()
                    if has_target_stream_column
                    else ""
                )
                sequence_order_raw = (
                    (r.get("sequence_order") or "0").strip()
                    if has_sequence_order_column
                    else "0"
                )
                try:
                    sequence_order = (
                        int(sequence_order_raw) if sequence_order_raw else 0
                    )
                except ValueError:
                    sequence_order = 0

                # Resolve education_level FK
                education_level_obj = None
                if education_level_code:
                    from education_level.models import EducationLevel

                    education_level_obj = EducationLevel.objects.filter(
                        level_code__iexact=education_level_code
                    ).first()

                # Resolve target_stream FK
                target_stream_obj = None
                if target_stream_code:
                    from stream.models import Stream

                    target_stream_obj = Stream.objects.filter(
                        stream_code__iexact=target_stream_code, deleted=False
                    ).first()

                # Resolve mapped_streams M2M
                stream_codes = [
                    s.strip() for s in mapped_streams_raw.split("|") if s.strip()
                ]
                stream_ids = []
                if stream_codes:
                    from stream.models import Stream

                    for sc in stream_codes:
                        s_obj = Stream.objects.filter(
                            stream_code__iexact=sc, deleted=False
                        ).first()
                        if s_obj:
                            stream_ids.append(s_obj.id)

                if dry_run:
                    dry_run_count += 1
                    dry_run_dimensions[dim] = dry_run_dimensions.get(dim, 0) + 1
                    continue

                defaults = {
                    "is_active": is_active,
                    "signal_strength": (
                        signal_strength if has_signal_strength_column else 1
                    ),
                    "question_type": question_type,
                    "sequence_order": sequence_order,
                    "education_level": education_level_obj,
                    "target_stream": target_stream_obj,
                }
                q = None
                if has_sequence_order_column and sequence_order:
                    sequence_matches = Question.objects.filter(
                        dimension=dim,
                        sequence_order=sequence_order,
                    )
                    q = (
                        sequence_matches.filter(question_text=qt).first()
                        or sequence_matches.first()
                    )
                if not q and not (has_sequence_order_column and sequence_order):
                    q = Question.objects.filter(
                        dimension=dim,
                        question_text=qt,
                    ).first()
                if q:
                    q_created = False
                else:
                    q = Question.objects.create(
                        dimension=dim,
                        question_text=qt,
                        **defaults,
                    )
                    q_created = True
                if q_created:
                    created_q += 1
                else:
                    changed_fields = []
                    if q.question_text != qt:
                        q.question_text = qt
                        changed_fields.append("question_text")
                    if q.is_active != is_active:
                        q.is_active = is_active
                        changed_fields.append("is_active")
                    if (
                        has_signal_strength_column
                        and q.signal_strength != signal_strength
                    ):
                        q.signal_strength = signal_strength
                        changed_fields.append("signal_strength")
                    if q.question_type != question_type:
                        q.question_type = question_type
                        changed_fields.append("question_type")
                    if q.sequence_order != sequence_order:
                        q.sequence_order = sequence_order
                        changed_fields.append("sequence_order")
                    if q.education_level_id != (
                        education_level_obj.id if education_level_obj else None
                    ):
                        q.education_level = education_level_obj
                        changed_fields.append("education_level")
                    if q.target_stream_id != (
                        target_stream_obj.id if target_stream_obj else None
                    ):
                        q.target_stream = target_stream_obj
                        changed_fields.append("target_stream")
                    if changed_fields:
                        q.save(update_fields=changed_fields)
                        updated_q += 1

                if has_mapped_domains_column:
                    if domain_ids:
                        q.mapped_domains.set(domain_ids)
                    else:
                        q.mapped_domains.clear()

                if has_mapped_streams_column:
                    if stream_ids:
                        q.mapped_streams.set(stream_ids)
                    else:
                        q.mapped_streams.clear()

                if has_split_options:
                    # 4-option MCQ format (text only).
                    for i in range(1, 5):
                        label = (r.get(f"option_{i}_text") or "").strip()
                        if not label:
                            continue

                        o, o_created = Option.objects.get_or_create(
                            question=q,
                            sequence_order=i,
                            defaults={"option_text": label},
                        )
                        if o_created:
                            created_o += 1
                        else:
                            if o.option_text != label:
                                o.option_text = label
                                o.save(update_fields=["option_text"])
                                updated_o += 1
                    stale_options = q.options.exclude(sequence_order__in=[1, 2, 3, 4])
                    deleted_options = stale_options.count()
                    if deleted_options:
                        stale_options.delete()
                        updated_o += deleted_options
                else:
                    # Legacy option_1..option_5 format (text only, ignore score prefix).
                    for i in range(1, 6):
                        cell = (r.get(f"option_{i}") or "").strip()
                        if not cell:
                            continue
                        # Strip optional "score: " prefix if present
                        label = (
                            cell.split(":", 1)[1].strip()
                            if ":" in cell
                            else cell.strip()
                        )
                        if not label:
                            raise ValueError(f"Row {idx}: option label cannot be blank")

                        o, o_created = Option.objects.get_or_create(
                            question=q,
                            sequence_order=i,
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
            return dry_run_count, dry_run_dimensions
        stale_q, stale_responses = self._delete_stale_questions(
            current_question_keys
        )
        return created_q, updated_q, created_o, updated_o, stale_q, stale_responses

    def _delete_stale_questions(self, current_question_keys: set[tuple[str, str]]):
        stale_ids = [
            question.id
            for question in Question.objects.filter(dimension__in=DIMENSIONS).only(
                "id",
                "dimension",
                "question_text",
            )
            if (question.dimension, question.question_text) not in current_question_keys
        ]
        if not stale_ids:
            return 0, 0

        response_count = UserResponse.objects.filter(
            question_id__in=stale_ids
        ).count()
        Question.objects.filter(id__in=stale_ids).delete()
        return len(stale_ids), response_count

    def _deactivate_retired_domain_personality_questions(self) -> int:
        questions = Question.objects.filter(
            dimension="personality",
            question_type="mcq",
            sequence_order=3,
            signal_strength=5,
            is_active=True,
        ).prefetch_related("options")

        retired_ids = [
            question.id
            for question in questions
            if {option.option_text for option in question.options.all()}
            == RETIRED_DOMAIN_PERSONALITY_OPTION_TEXTS
        ]
        retired_questions = Question.objects.filter(id__in=retired_ids)
        for question in retired_questions:
            question.mapped_domains.clear()
        retired_questions.update(is_active=False)
        return len(retired_ids)

    def _repair_zero_order_options(self) -> int:
        repaired = 0
        questions = (
            Question.objects.filter(options__sequence_order=0)
            .distinct()
            .prefetch_related("options")
        )

        for question in questions:
            options = list(question.options.all().order_by("id"))
            if not options:
                continue
            if any(option.sequence_order for option in options):
                continue

            for index, option in enumerate(options, start=1):
                option.sequence_order = index
                option.save(update_fields=["sequence_order"])
                repaired += 1

        return repaired

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        prune_existing = bool(options.get("prune_existing"))

        sample_path = Path(options["sample_path"])
        if options.get("write_sample"):
            self._write_sample_csv(sample_path=sample_path)
            self.stdout.write(
                self.style.SUCCESS(f"Sample CSV written: {sample_path.resolve()}")
            )
            return

        load_path_raw = options.get("load_path")
        load_path = Path(load_path_raw) if load_path_raw else sample_path
        result = self._load_from_csv(
            load_path=load_path, dry_run=dry_run, prune_existing=prune_existing
        )
        if dry_run:
            dry_run_count, dry_run_dimensions = result
            dimension_summary = ", ".join(
                f"{dimension}={count}"
                for dimension, count in dry_run_dimensions.items()
                if count
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "Dry run complete. No changes written. "
                    f"CSV questions checked={dry_run_count}"
                    + (f" ({dimension_summary})" if dimension_summary else "")
                )
            )
            return
        created_q, updated_q, created_o, updated_o, stale_q, stale_responses = result
        retired_personality = self._deactivate_retired_domain_personality_questions()
        updated_o += self._repair_zero_order_options()
        self.stdout.write(
            self.style.SUCCESS(
                "Seed complete (CSV): "
                f"questions(created={created_q}, updated={updated_q}) "
                f"options(created={created_o}, updated={updated_o}) "
                f"stale_questions(deleted={stale_q}, responses_deleted={stale_responses})"
                f" retired(personality={retired_personality})"
            )
        )
