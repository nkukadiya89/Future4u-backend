from __future__ import annotations

import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from assessment.models import Question
from domain.models import Domain

DIMENSIONS = ("interest", "aptitude", "personality", "work_style")


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

        active_questions = Question.objects.filter(
            is_active=True, dimension__in=DIMENSIONS
        ).prefetch_related("mapped_domains")
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
            # The runtime question pool uses the specific domain once selected,
            # so coverage for child domains should be evaluated against the child domain alone.
            combined_questions = list(
                {question.id: question for question in domain_questions}.values()
            )

            dimension_counts = {
                dimension: sum(
                    1
                    for question in combined_questions
                    if question.dimension == dimension
                )
                for dimension in DIMENSIONS
            }
            combined_count = len(combined_questions)
            status = self._coverage_status(combined_count, dimension_counts)
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
            *DIMENSIONS,
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
            self.style.SUCCESS(f"Wrote {len(rows)} rows to {output_path}. {summary}")
        )

    def _coverage_status(self, combined_count, dimension_counts):
        per_dim = 3
        expected_total = per_dim * len(DIMENSIONS)
        if combined_count == expected_total and all(
            dimension_counts.get(d, 0) == per_dim for d in DIMENSIONS
        ):
            return "GOOD"
        if combined_count > expected_total:
            return "TOO_HIGH"
        if combined_count >= (expected_total // 2):
            return "SHORT"
        return "BAD"
