from __future__ import annotations

import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from assessment.models import Question
from domain.models import Domain


SEED_HEADERS = (
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


def _likert_frequency_options() -> tuple[str, str, str, str, str]:
    # Seed command accepts either "label" (score inferred from column)
    # or "score:label". We keep it simple and deterministic.
    return (
        "Never",
        "Rarely",
        "Sometimes",
        "Often",
        "Very often",
    )


def _behavior_questions_for_domain(*, domain_name: str) -> list[dict[str, str]]:
    """
    Produce 3 behavior-based, domain-anchored questions.
    Keep them concrete and non-generic by referencing real actions.
    """
    dn = (domain_name or "").strip()
    if not dn:
        dn = "this field"

    # Mix dimensions to give the domain enough signal coverage.
    return [
        {
            "dimension": "interest",
            "signal_strength": "2",
            "question_text": (
                f"In the last 30 days, how often did you choose to learn or read about {dn} even when it wasn't required?"
            ),
        },
        {
            "dimension": "aptitude",
            "signal_strength": "2",
            "question_text": (
                f"When working on {dn}-related tasks, how often do you break down a messy problem into clear steps and finish it?"
            ),
        },
        {
            "dimension": "work_style",
            "signal_strength": "1",
            "question_text": (
                f"In group activities related to {dn}, how often do you take ownership to coordinate people, tools, or timelines to complete the work?"
            ),
        },
    ]


class Command(BaseCommand):
    help = "Audit domains for mapped assessment question coverage and generate a seed-compatible CSV for gaps."

    def add_arguments(self, parser):
        parser.add_argument(
            "--min-questions",
            type=int,
            default=2,
            help="Minimum active mapped questions required per domain (default: 2).",
        )
        parser.add_argument(
            "--max-generate",
            type=int,
            default=3,
            help="How many questions to generate per missing domain (default: 3).",
        )
        parser.add_argument(
            "--out",
            default=str(Path(settings.BASE_DIR) / "core" / "management" / "source" / "domain_question_gaps.csv"),
            help="Where to write the CSV output.",
        )

    def handle(self, *args, **options):
        min_questions = max(0, int(options["min_questions"]))
        max_generate = max(1, int(options["max_generate"]))
        out_path = Path(options["out"])
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Count active questions mapped to each active domain.
        # Note: Question has no deleted flag; Domain does.
        domain_rows = (
            Domain.objects.filter(deleted=False, is_active=True)
            .annotate(
                active_question_count=Count(
                    "assessment_questions",
                    filter=Q(assessment_questions__is_active=True),
                    distinct=True,
                )
            )
            .only("id", "domain_code", "domain_name")
            .order_by("domain_name", "domain_code")
        )

        missing = [d for d in domain_rows if int(getattr(d, "active_question_count", 0) or 0) < min_questions]

        # CSV: include a per-domain summary row (for reporting) plus seed rows for new questions.
        with out_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)

            # Report section (human-readable) as a commented CSV-style header.
            w.writerow(["# domain_code", "domain_name", "active_mapped_questions"])
            for d in missing:
                w.writerow([d.domain_code, d.domain_name, int(d.active_question_count or 0)])

            w.writerow([])  # spacer row

            # Seed section (machine-loadable by seed_assessment_questions.py)
            w.writerow(SEED_HEADERS)
            opt1, opt2, opt3, opt4, opt5 = _likert_frequency_options()

            for d in missing:
                questions = _behavior_questions_for_domain(domain_name=d.domain_name)[:max_generate]
                for q in questions:
                    w.writerow(
                        [
                            q["dimension"],
                            q["question_text"],
                            d.domain_code,  # mapped_domains (seed command supports comma-separated codes)
                            q["signal_strength"],
                            "1",  # is_active
                            opt1,
                            opt2,
                            opt3,
                            opt4,
                            opt5,
                        ]
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Found {len(missing)} domain(s) below {min_questions} mapped active question(s). "
                f"CSV written: {out_path.resolve()}"
            )
        )

