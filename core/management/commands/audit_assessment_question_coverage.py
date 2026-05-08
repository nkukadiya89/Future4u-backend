from __future__ import annotations

import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from assessment.models import Question
from domain.models import Domain


SIGNAL_DIMENSIONS = (
    "background",
    "interest",
    "academic_strength",
    "skill_confidence",
    "exposure",
    "work_preference",
    "readiness",
)
OLD_DIMENSIONS = ("aptitude", "personality", "work_style")


class Command(BaseCommand):
    help = "Write assessment question coverage report for active child domains."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default=str(
                Path(settings.BASE_DIR)
                / "core"
                / "management"
                / "output"
                / "assessment_question_coverage_report.csv"
            ),
            help="CSV output path.",
        )

    def handle(self, *args, **options):
        output_path = Path(options["output"])
        output_path.parent.mkdir(parents=True, exist_ok=True)

        active_questions = Question.objects.filter(is_active=True).prefetch_related(
            "mapped_domains"
        )
        questions_by_domain_id = {}
        for question in active_questions:
            for domain in question.mapped_domains.all():
                questions_by_domain_id.setdefault(domain.id, []).append(question)

        child_domains = (
            Domain.objects.filter(
                parent__isnull=False,
                is_active=True,
                deleted=False,
                parent__is_active=True,
                parent__deleted=False,
            )
            .select_related("parent")
            .order_by("parent__domain_name", "domain_name")
        )

        rows = []
        status_counts = {}
        for domain in child_domains:
            parent = domain.parent
            parent_questions = questions_by_domain_id.get(parent.id, [])
            domain_questions = questions_by_domain_id.get(domain.id, [])
            combined_questions = list(
                {question.id: question for question in parent_questions + domain_questions}.values()
            )

            old_dimensions = sorted(
                {
                    question.dimension
                    for question in combined_questions
                    if question.dimension in OLD_DIMENSIONS
                }
            )
            dimension_counts = {
                dimension: sum(
                    1 for question in combined_questions if question.dimension == dimension
                )
                for dimension in SIGNAL_DIMENSIONS
            }
            combined_count = len(combined_questions)
            status = self._coverage_status(combined_count, old_dimensions)
            status_counts[status] = status_counts.get(status, 0) + 1

            rows.append(
                {
                    "parent_code": parent.domain_code,
                    "parent_name": parent.domain_name,
                    "domain_code": domain.domain_code,
                    "domain_name": domain.domain_name,
                    "parent_question_count": len(parent_questions),
                    "domain_question_count": len(domain_questions),
                    "combined_question_count": combined_count,
                    **dimension_counts,
                    "old_active_dimensions": "|".join(old_dimensions),
                    "status": status,
                }
            )

        fieldnames = [
            "parent_code",
            "parent_name",
            "domain_code",
            "domain_name",
            "parent_question_count",
            "domain_question_count",
            "combined_question_count",
            *SIGNAL_DIMENSIONS,
            "old_active_dimensions",
            "status",
        ]
        with output_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        summary = ", ".join(
            f"{status}={count}" for status, count in sorted(status_counts.items())
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Wrote {len(rows)} rows to {output_path}. {summary}"
            )
        )

    def _coverage_status(self, combined_count, old_dimensions):
        if old_dimensions:
            return "OLD_STYLE"
        if 12 <= combined_count <= 15:
            return "GOOD"
        if combined_count > 15:
            return "TOO_HIGH"
        if 6 <= combined_count <= 11:
            return "SHORT"
        return "BAD"
