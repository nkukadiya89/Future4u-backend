from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


HEADERS = (
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
    "option_1_text",
    "option_2_text",
    "option_3_text",
    "option_4_text",
)


DIMENSIONS = ("interest", "aptitude", "personality", "work_style")

LEGACY_DIMENSION_MAP = {
    "background": "personality",
    "academic_strength": "aptitude",
    "skill_confidence": "aptitude",
    "exposure": "aptitude",
    "work_preference": "work_style",
    "readiness": "aptitude",
}


@dataclass(frozen=True)
class QuestionTemplate:
    dimension: str
    question_text: str
    options: tuple[str, str, str, str]
    signal_strength: int = 4


def _pretty_label(code: str) -> str:
    # Turn "AI_ML" into "AI ML", "BUSINESS_ADMIN" -> "BUSINESS ADMIN"
    return (code or "").strip().replace("__", " ").replace("_", " ").strip()


def _domain_meta(code: str) -> tuple[str, list[str], list[str]]:
    """
    Best-effort domain metadata from DB.
    Returns: (domain_label, technical_keywords, domain_keywords)
    Falls back safely when DB isn't available.
    """
    label = _pretty_label(code)
    try:
        from domain.models import Domain, DomainCounsellorKnowledge

        dom = (
            Domain.objects.filter(domain_code__iexact=code, deleted=False)
            .only("domain_name")
            .first()
        )
        if dom and getattr(dom, "domain_name", None):
            label = str(dom.domain_name).strip() or label

        k = (
            DomainCounsellorKnowledge.objects.filter(domain_code__iexact=code)
            .only("technical_keywords", "domain_keywords")
            .first()
        )
        tech = (
            [str(x).strip() for x in (getattr(k, "technical_keywords", []) or []) if str(x).strip()]
            if k
            else []
        )
        domk = (
            [str(x).strip() for x in (getattr(k, "domain_keywords", []) or []) if str(x).strip()]
            if k
            else []
        )
        return label, tech, domk
    except Exception:
        return label, [], []


def _pick4(items: list[str], *, fallback: tuple[str, str, str, str]) -> tuple[str, str, str, str]:
    dedup: list[str] = []
    seen = set()
    for it in items:
        k = it.lower()
        if k in seen:
            continue
        seen.add(k)
        dedup.append(it)
        if len(dedup) >= 4:
            break
    return (dedup[0], dedup[1], dedup[2], dedup[3]) if len(dedup) >= 4 else fallback


def _templates_for(code: str) -> list[QuestionTemplate]:
    label, technical_keywords, domain_keywords = _domain_meta(code)

    # These are intentionally domain-agnostic but "feel" specific because we inject the label.
    # Each domain/category gets 3 questions per dimension (12 total), MCQ with 4 options.
    return [
        # interest (3)
        QuestionTemplate(
            "interest",
            f"What sounds most exciting to you in {label}?",
            (
                f"Exploring what {label} is really about",
                f"Building or creating something in {label}",
                f"Solving real problems using {label}",
                f"Learning step-by-step and improving in {label}",
            ),
        ),
        QuestionTemplate(
            "interest",
            f"If you had free time this week, what would you prefer to do to explore {label}?",
            (
                f"Watch a short beginner video about {label}",
                f"Try a simple hands-on task/project in {label}",
                f"Talk to someone who studies/works in {label}",
                f"Read about careers and paths inside {label}",
            ),
        ),
        QuestionTemplate(
            "interest",
            f"Which outcome would make you feel proud in {label}?",
            (
                f"Creating something useful related to {label}",
                f"Helping others using skills from {label}",
                f"Becoming highly skilled/recognized in {label}",
                f"Finding a long-term career path in {label}",
            ),
        ),
        # aptitude (3)
        QuestionTemplate(
            "aptitude",
            f"When a {label} topic feels difficult, what do you usually do?",
            (
                "Avoid it and move to something easier",
                "Try a little but stop if it stays hard",
                "Ask for help and keep trying",
                "Break it down and practice until I understand",
            ),
        ),
        QuestionTemplate(
            "aptitude",
            f"Which of these feels most like what you'd learn or use in {label}?",
            _pick4(
                technical_keywords + domain_keywords,
                fallback=(
                    "Learning basics step by step",
                    "Practicing with simple real examples",
                    "Improving through feedback and correction",
                    "Solving harder problems over time",
                ),
            ),
        ),
        QuestionTemplate(
            "aptitude",
            f"If you were learning {label}, which approach fits you best?",
            (
                "I learn best only through theory",
                "I learn best only through practice",
                "I need a mix of both, with guidance",
                "I can learn independently using resources",
            ),
        ),
        # personality (3)
        QuestionTemplate(
            "personality",
            f"In {label}, progress often takes time. Which describes you best?",
            (
                "I get bored quickly if results are slow",
                "I try, but I lose motivation sometimes",
                "I stay consistent when I have a clear plan",
                "I enjoy long-term improvement and mastery",
            ),
        ),
        QuestionTemplate(
            "personality",
            f"How do you feel about feedback and correction while learning {label}?",
            (
                "I avoid feedback; it feels discouraging",
                "I accept feedback but feel tense",
                "I like feedback when it's clear and kind",
                "I actively seek feedback to improve faster",
            ),
        ),
        QuestionTemplate(
            "personality",
            f"Which work mindset matches you in a {label}-related path?",
            (
                "I prefer safe tasks with low risk",
                "I prefer predictable routines",
                "I like learning new things regularly",
                "I like challenging goals and pushing limits",
            ),
        ),
        # work_style (3)
        QuestionTemplate(
            "work_style",
            f"Which work style would you prefer in {label}?",
            (
                "Working alone, quietly focused",
                "Working with a small team",
                "Working with many people and communicating often",
                "A mix depending on the task",
            ),
        ),
        QuestionTemplate(
            "work_style",
            f"What kind of tasks do you prefer in {label}?",
            (
                "Creative and open-ended tasks",
                "Structured tasks with clear rules",
                "Tasks that need accuracy and careful checking",
                "Tasks that involve experimenting and improving",
            ),
        ),
        QuestionTemplate(
            "work_style",
            f"Which environment would suit you for {label} work?",
            (
                "Fast-paced with frequent changes",
                "Steady pace with clear expectations",
                "High responsibility and pressure",
                "Flexible environment with learning time",
            ),
        ),
    ]


def _load_codes_from_existing_csv(path: Path) -> list[str]:
    # Backward compatible helper (kept for older usage), but this command now
    # prefers `domain_hierarchy.csv` as the source of truth.
    codes: set[str] = set()
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mapped = (row.get("mapped_domains") or "").strip()
            if not mapped:
                continue
            sep = "|" if "|" in mapped else ","
            for code in [c.strip() for c in mapped.split(sep) if c.strip()]:
                codes.add(code)
    return sorted(codes)


def _load_domain_pairs_from_hierarchy(path: Path) -> tuple[list[tuple[str | None, str]], set[str]]:
    """
    Read `domain_hierarchy.csv` and return:
    - pairs: list[(parent_code_or_None, domain_code)]
    - parents_with_children: set[parent_code]

    Only rows with `is_active` truthy are included.
    """
    if not path.exists():
        raise FileNotFoundError(str(path))

    pairs: list[tuple[str | None, str]] = []
    parents_with_children: set[str] = set()

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("domain_hierarchy.csv has no header row.")

        required = {"domain_code", "parent_code", "is_active"}
        missing = sorted(required - set(reader.fieldnames))
        if missing:
            raise ValueError(f"domain_hierarchy.csv missing headers: {', '.join(missing)}")

        for idx, row in enumerate(reader, start=2):
            code = (row.get("domain_code") or "").strip()
            parent = (row.get("parent_code") or "").strip() or None
            active_raw = (row.get("is_active") or "1").strip().lower()
            is_active = active_raw in ("1", "true", "yes", "y")
            if not is_active:
                continue
            if not code:
                raise ValueError(f"domain_hierarchy.csv row {idx}: domain_code is blank")
            pairs.append((parent, code))
            if parent:
                parents_with_children.add(parent)

    return pairs, parents_with_children


class Command(BaseCommand):
    help = (
        "Regenerate assessment_questions_sample.csv with 4 dimensions and 3 MCQ questions "
        "per dimension for every active domain in domain_hierarchy.csv. "
        "Generates 12 questions for each domain category (parent) and each child domain."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--domain-hierarchy",
            dest="domain_hierarchy_path",
            default=str(
                Path(settings.BASE_DIR)
                / "core"
                / "management"
                / "source"
                / "domain_hierarchy.csv"
            ),
            help="CSV source of domain categories + domains (domain_hierarchy.csv).",
        )
        parser.add_argument(
            "--out",
            dest="out_path",
            default=str(
                Path(settings.BASE_DIR)
                / "core"
                / "management"
                / "source"
                / "assessment_questions_sample.csv"
            ),
            help="Output CSV path.",
        )
        parser.add_argument(
            "--question-type",
            default="mcq",
            choices=("mcq",),
            help="Currently only MCQ generation is supported.",
        )
        parser.add_argument(
            "--min-per-dimension",
            type=int,
            default=3,
            help="How many questions per dimension per domain/category to generate (default 3).",
        )

    def handle(self, *args, **options):
        domain_hierarchy_path = Path(options["domain_hierarchy_path"])
        out_path = Path(options["out_path"])
        per_dim = int(options["min_per_dimension"] or 3)
        if per_dim < 1:
            raise ValueError("--min-per-dimension must be >= 1")

        pairs, _parents_with_children = _load_domain_pairs_from_hierarchy(domain_hierarchy_path)
        if not pairs:
            raise ValueError(f"No active domain rows found in {domain_hierarchy_path}")

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=HEADERS)
            w.writeheader()

            seq = 10
            created = 0
            parent_codes = sorted({code for parent, code in pairs if parent is None})
            child_codes = [(parent, code) for parent, code in pairs if parent is not None]

            # Domain categories (parent codes)
            for parent_code in parent_codes:
                templates = _templates_for(parent_code)
                # Ensure exactly N per dimension.
                by_dim: dict[str, list[QuestionTemplate]] = {d: [] for d in DIMENSIONS}
                for t in templates:
                    if t.dimension in by_dim:
                        by_dim[t.dimension].append(t)
                for dim in DIMENSIONS:
                    if len(by_dim[dim]) < per_dim:
                        raise ValueError(
                            f"Not enough templates for dimension={dim} (have {len(by_dim[dim])}, need {per_dim})"
                        )

                for dim in DIMENSIONS:
                    for t in by_dim[dim][:per_dim]:
                        row = {
                            "dimension": dim,
                            "question_text": t.question_text,
                            "question_type": "mcq",
                            "mapped_domains": parent_code,
                            "mapped_streams": "",
                            "signal_strength": str(int(t.signal_strength)),
                            "is_active": "1",
                            "education_level": "",
                            "target_stream": "",
                            "sequence_order": str(seq),
                            "option_1_text": t.options[0],
                            "option_2_text": t.options[1],
                            "option_3_text": t.options[2],
                            "option_4_text": t.options[3],
                        }
                        w.writerow(row)
                        created += 1
                        seq += 1

            # Child domains
            for _parent, child_code in child_codes:
                templates = _templates_for(child_code)
                by_dim: dict[str, list[QuestionTemplate]] = {d: [] for d in DIMENSIONS}
                for t in templates:
                    if t.dimension in by_dim:
                        by_dim[t.dimension].append(t)
                for dim in DIMENSIONS:
                    if len(by_dim[dim]) < per_dim:
                        raise ValueError(
                            f"Not enough templates for dimension={dim} (have {len(by_dim[dim])}, need {per_dim})"
                        )
                for dim in DIMENSIONS:
                    for t in by_dim[dim][:per_dim]:
                        row = {
                            "dimension": dim,
                            "question_text": t.question_text,
                            "question_type": "mcq",
                            "mapped_domains": child_code,
                            "mapped_streams": "",
                            "signal_strength": str(int(t.signal_strength)),
                            "is_active": "1",
                            "education_level": "",
                            "target_stream": "",
                            "sequence_order": str(seq),
                            "option_1_text": t.options[0],
                            "option_2_text": t.options[1],
                            "option_3_text": t.options[2],
                            "option_4_text": t.options[3],
                        }
                        w.writerow(row)
                        created += 1
                        seq += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Regenerated CSV with {created} questions at {out_path}"
            )
        )

