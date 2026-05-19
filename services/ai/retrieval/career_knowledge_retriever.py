from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from django.db.models import Avg, Count, Max, Min, Q

from assessment.models import StudentAssessment
from assessment.services.domain_config import get_domain_config
from career.models import Career
from domain.models import Domain, DomainReportMeta
from domain_career_mapping.models import DomainCareerMapping
from domain_skill_mapping.models import DomainSkillMapping


from services.ai.config import TOP_SUGGESTION_COUNT


class CareerKnowledgeRetriever:
    """PostgreSQL-only career knowledge (seeded via CSV imports). No in-code domain dictionaries."""

    MAX_CAREERS = TOP_SUGGESTION_COUNT

    @classmethod
    def retrieve(cls, assessment: StudentAssessment) -> list[dict[str, Any]]:
        domain = assessment.domain
        if not domain:
            return []

        domain_ids = cls._domain_ids_for_assessment(assessment)
        knowledge_domain_ids = cls._knowledge_domain_ids(assessment, domain_ids)
        career_entries = cls._resolve_career_entries(assessment, domain_ids)
        if not career_entries:
            return []

        skills_by_career = cls._skills_for_careers(
            assessment_domain_ids=knowledge_domain_ids,
            career_entries=career_entries,
        )
        report_meta = cls._domain_report_meta_for_assessment(assessment, domain_ids)
        reference_degrees = (report_meta.get("degrees") or []) if report_meta else []
        direction_why = (report_meta.get("direction_why") or "") if report_meta else ""
        future_scope = (report_meta.get("note") or "") if report_meta else ""
        domain_salary = cls._domain_salary_range(domain_ids=knowledge_domain_ids)

        category = assessment.domain_category
        domain_category_name = getattr(category, "domain_name", None) if category else None

        results: list[dict[str, Any]] = []
        for career, mapping_weight in career_entries:
            career_key = str(career.id)
            min_edu = career.min_education_level
            max_edu = career.max_education_level
            career_skills = skills_by_career.get(career_key, [])[:12]
            skill_match_score = cls._skill_match_for_career(
                career=career,
                skill_names=career_skills,
                domain_ids=knowledge_domain_ids,
            )

            results.append(
                {
                    "career_id": career_key,
                    "career_code": career.career_code,
                    "career_name": career.career_name,
                    "description": (career.description or "")[:800],
                    "mapping_weight": mapping_weight,
                    "skill_match_score": skill_match_score,
                    "domain_name": domain.domain_name,
                    "domain_code": domain.domain_code,
                    "domain_category_name": domain_category_name,
                    "domain_category_code": (
                        getattr(category, "domain_code", None) if category else None
                    ),
                    "required_skills": career_skills,
                    "required_education": {
                        "min_level": getattr(min_edu, "display_name", None),
                        "max_level": getattr(max_edu, "display_name", None),
                        "min_level_code": getattr(min_edu, "level_code", None),
                        "max_level_code": getattr(max_edu, "level_code", None),
                    },
                    "reference_degrees": reference_degrees[:6],
                    "direction_why": direction_why[:800],
                    "future_scope": future_scope[:800],
                    "salary": domain_salary,
                }
            )

        return results

    @classmethod
    def _domain_ids_for_assessment(cls, assessment: StudentAssessment) -> list:
        domain_ids = [assessment.domain_id]
        if assessment.domain_category_id:
            domain_ids.append(assessment.domain_category_id)
        return domain_ids

    @classmethod
    def _knowledge_domain_ids(cls, assessment: StudentAssessment, domain_ids: list) -> list:
        """Sibling domains under the same parent (e.g. ADVERTISING → DIGITAL_MARKETING mappings)."""
        expanded = list(dict.fromkeys(domain_ids))
        domain = assessment.domain
        if not domain or not domain.parent_id:
            return expanded

        sibling_ids = Domain.objects.filter(
            parent_id=domain.parent_id,
            is_active=True,
            deleted=False,
        ).values_list("id", flat=True)
        for sid in sibling_ids:
            if sid not in expanded:
                expanded.append(sid)
        return expanded

    @classmethod
    def _domain_codes_for_lookup(cls, assessment: StudentAssessment) -> list[str]:
        """Domain codes to try for report meta / counsellor (assessment domain + siblings from DB)."""
        codes: list[str] = []
        seen: set[str] = set()
        domain = assessment.domain

        def add_code(raw: str | None) -> None:
            code = (raw or "").strip()
            if not code:
                return
            key = code.lower()
            if key in seen:
                return
            seen.add(key)
            codes.append(code)

        if domain:
            add_code(domain.domain_code)
        if assessment.domain_category:
            add_code(assessment.domain_category.domain_code)

        if domain and domain.parent_id:
            for code in Domain.objects.filter(
                parent_id=domain.parent_id,
                is_active=True,
                deleted=False,
            ).values_list("domain_code", flat=True):
                add_code(code)

        return codes

    @classmethod
    def _domain_report_meta_for_assessment(
        cls, assessment: StudentAssessment, domain_ids: list
    ) -> dict[str, Any] | None:
        for code in cls._domain_codes_for_lookup(assessment):
            meta = cls._domain_report_meta(code)
            if meta:
                return meta
        return None

    @classmethod
    def _lookup_mapping_weight(cls, domain_ids: list, career_id) -> int | None:
        weight = (
            DomainCareerMapping.objects.filter(
                domain_id__in=domain_ids,
                career_id=career_id,
                is_active=True,
                deleted=False,
            )
            .order_by("-weight_score")
            .values_list("weight_score", flat=True)
            .first()
        )
        if weight is None:
            return None
        return int(weight)

    @classmethod
    def _resolve_career_entries(
        cls, assessment: StudentAssessment, domain_ids: list
    ) -> list[tuple[Career, int]]:
        knowledge_domain_ids = cls._knowledge_domain_ids(assessment, domain_ids)

        mapping_qs = DomainCareerMapping.objects.filter(
            domain_id__in=knowledge_domain_ids,
            is_active=True,
            deleted=False,
            career__is_active=True,
            career__deleted=False,
        )
        entries = cls._entries_from_mappings(mapping_qs)
        if entries:
            return entries

        domain = assessment.domain
        category = assessment.domain_category
        for domain_code in (
            getattr(domain, "domain_code", None),
            getattr(category, "domain_code", None),
        ):
            entries = cls._careers_from_scoring_config(domain_code, knowledge_domain_ids)
            if entries:
                return entries

        for domain_code in cls._domain_codes_for_lookup(assessment):
            entries = cls._careers_from_report_meta(domain_code, knowledge_domain_ids)
            if entries:
                return entries

        return []

    @classmethod
    def _entries_from_mappings(cls, queryset) -> list[tuple[Career, int]]:
        mappings = queryset.select_related(
            "career",
            "career__min_education_level",
            "career__max_education_level",
        ).order_by("-weight_score", "career__career_name")
        seen_ids: set = set()
        seen_names: set[str] = set()
        entries: list[tuple[Career, int]] = []
        for mapping in mappings:
            name_key = (mapping.career.career_name or "").strip().casefold()
            if mapping.career_id in seen_ids or (name_key and name_key in seen_names):
                continue
            seen_ids.add(mapping.career_id)
            if name_key:
                seen_names.add(name_key)
            entries.append((mapping.career, int(mapping.weight_score)))
            if len(entries) >= cls.MAX_CAREERS:
                break
        return entries

    @classmethod
    def _careers_from_scoring_config(
        cls, domain_code: str | None, domain_ids: list
    ) -> list[tuple[Career, int]]:
        cfg = get_domain_config(domain_code or "")
        if not cfg:
            return []

        career_codes = list((cfg.get("careers") or {}).keys())
        if not career_codes:
            return []

        rows = Career.objects.filter(
            career_code__in=career_codes,
            is_active=True,
            deleted=False,
        ).select_related("min_education_level", "max_education_level")
        by_code = {c.career_code.lower(): c for c in rows}

        entries: list[tuple[Career, int]] = []
        for code in career_codes:
            career = by_code.get(str(code).strip().lower())
            if not career:
                continue
            weight = cls._lookup_mapping_weight(domain_ids, career.id)
            if weight is None:
                continue
            entries.append((career, weight))
        return entries[: cls.MAX_CAREERS]

    @classmethod
    def _careers_from_report_meta(
        cls, domain_code: str, domain_ids: list
    ) -> list[tuple[Career, int]]:
        report_meta = cls._domain_report_meta(domain_code)
        if not report_meta:
            return []

        careers = cls._careers_by_names(report_meta.get("careers", []))
        entries: list[tuple[Career, int]] = []
        for career in careers:
            weight = cls._lookup_mapping_weight(domain_ids, career.id)
            if weight is None:
                continue
            entries.append((career, weight))
        return entries[: cls.MAX_CAREERS]

    @classmethod
    def _careers_by_names(cls, names: list[str]) -> list[Career]:
        careers: list[Career] = []
        seen: set = set()
        for raw_name in names:
            name = str(raw_name).strip()
            if not name:
                continue
            career = (
                Career.objects.filter(
                    career_name__iexact=name,
                    is_active=True,
                    deleted=False,
                )
                .select_related("min_education_level", "max_education_level")
                .first()
            )
            if not career:
                career = (
                    Career.objects.filter(
                        career_name__icontains=name,
                        is_active=True,
                        deleted=False,
                    )
                    .select_related("min_education_level", "max_education_level")
                    .first()
                )
            if career and career.id not in seen:
                seen.add(career.id)
                careers.append(career)
            if len(careers) >= cls.MAX_CAREERS:
                break
        return careers

    @staticmethod
    def _skill_tokens(*parts: str) -> set[str]:
        tokens: set[str] = set()
        for part in parts:
            for match in re.findall(r"[a-z0-9]+", (part or "").lower()):
                if len(match) >= 3:
                    tokens.add(match)
        return tokens

    @classmethod
    def _career_skill_relevance(
        cls,
        *,
        career: Career,
        skill_name: str,
        skill_code: str,
        skill_description: str,
        weight_score: int,
    ) -> int:
        career_tokens = cls._skill_tokens(
            career.career_code,
            career.career_name,
            career.description or "",
        )
        skill_tokens = cls._skill_tokens(
            skill_code,
            skill_name,
            skill_description or "",
        )

        score = int(weight_score)
        score += len(career_tokens & skill_tokens) * 18

        career_blob = " ".join(career_tokens)
        for token in skill_tokens:
            if len(token) >= 4 and token in career_blob:
                score += 10

        for stem in career.career_code.lower().split("_"):
            if len(stem) >= 4 and stem in skill_code.lower():
                score += 28

        return score

    @classmethod
    def _domain_ids_for_career_skills(
        cls, *, career_id, assessment_domain_ids: list
    ) -> list:
        """Prefer domains in the current assessment cluster; widen only if needed."""
        in_assessment = list(
            DomainCareerMapping.objects.filter(
                career_id=career_id,
                domain_id__in=assessment_domain_ids,
                is_active=True,
                deleted=False,
            )
            .order_by("-weight_score")
            .values_list("domain_id", flat=True)
        )
        if in_assessment:
            return list(dict.fromkeys(in_assessment))

        mappings = list(
            DomainCareerMapping.objects.filter(
                career_id=career_id,
                is_active=True,
                deleted=False,
            )
            .order_by("-weight_score")
            .values_list("domain_id", flat=True)[:6]
        )
        return mappings or list(assessment_domain_ids)

    @classmethod
    def _skills_for_careers(
        cls,
        *,
        assessment_domain_ids: list,
        career_entries: list[tuple[Career, int]],
    ) -> dict[str, list[str]]:
        if not career_entries:
            return {}

        career_ids = [career.id for career, _ in career_entries]
        all_domain_ids: set = set(assessment_domain_ids)
        domains_by_career: dict[Any, list] = {}

        for career_id in career_ids:
            domain_ids = cls._domain_ids_for_career_skills(
                career_id=career_id,
                assessment_domain_ids=assessment_domain_ids,
            )
            domains_by_career[career_id] = domain_ids
            all_domain_ids.update(domain_ids)

        skill_rows = (
            DomainSkillMapping.objects.filter(
                domain_id__in=all_domain_ids,
                is_active=True,
                deleted=False,
                skill__is_active=True,
                skill__deleted=False,
            )
            .select_related("skill")
            .order_by("-weight_score", "skill__skill_name")
        )

        rows_by_domain: dict[Any, list] = defaultdict(list)
        for row in skill_rows:
            rows_by_domain[row.domain_id].append(row)

        fallback_rows: list = []
        seen_fallback: set[str] = set()
        for row in skill_rows:
            name = row.skill.skill_name
            if name not in seen_fallback:
                seen_fallback.add(name)
                fallback_rows.append(row)

        skills_by_career: dict[str, list[str]] = {}
        for career, _ in career_entries:
            scored: list[tuple[int, str]] = []
            seen_names: set[str] = set()

            for domain_id in domains_by_career.get(career.id, assessment_domain_ids):
                for row in rows_by_domain.get(domain_id, []):
                    name = row.skill.skill_name
                    if name in seen_names:
                        continue
                    seen_names.add(name)
                    relevance = cls._career_skill_relevance(
                        career=career,
                        skill_name=name,
                        skill_code=row.skill.skill_code,
                        skill_description=row.skill.description or "",
                        weight_score=int(row.weight_score or 0),
                    )
                    scored.append((relevance, name))

            if not scored:
                for row in fallback_rows:
                    name = row.skill.skill_name
                    relevance = cls._career_skill_relevance(
                        career=career,
                        skill_name=name,
                        skill_code=row.skill.skill_code,
                        skill_description=row.skill.description or "",
                        weight_score=int(row.weight_score or 0),
                    )
                    scored.append((relevance, name))

            scored.sort(key=lambda item: (-item[0], item[1]))
            skills_by_career[str(career.id)] = [name for _, name in scored[:8]]

        return skills_by_career

    @classmethod
    def _aggregate_skill_match_score(cls, domain_ids: list) -> int | None:
        agg = DomainSkillMapping.objects.filter(
            domain_id__in=domain_ids,
            is_active=True,
            deleted=False,
        ).aggregate(avg=Avg("weight_score"))
        avg = agg.get("avg")
        if avg is None:
            return None
        return int(round(float(avg)))

    @classmethod
    def _skill_match_for_career(
        cls,
        *,
        career: Career,
        skill_names: list[str],
        domain_ids: list,
    ) -> int | None:
        """Per-career skill fit (0–100) from domain_skill_mapping relevance, not one domain average."""
        fallback = cls._aggregate_skill_match_score(domain_ids)
        if not skill_names:
            return fallback

        career_domain_ids = cls._domain_ids_for_career_skills(
            career_id=career.id,
            assessment_domain_ids=domain_ids,
        )
        rows = (
            DomainSkillMapping.objects.filter(
                domain_id__in=career_domain_ids,
                is_active=True,
                deleted=False,
                skill__is_active=True,
                skill__deleted=False,
                skill__skill_name__in=skill_names[:8],
            )
            .select_related("skill")
            .order_by("-weight_score")
        )
        if not rows.exists():
            return fallback

        relevance_scores: list[int] = []
        seen_skills: set[str] = set()
        for row in rows:
            name = row.skill.skill_name
            if name in seen_skills:
                continue
            seen_skills.add(name)
            relevance_scores.append(
                cls._career_skill_relevance(
                    career=career,
                    skill_name=name,
                    skill_code=row.skill.skill_code,
                    skill_description=row.skill.description or "",
                    weight_score=int(row.weight_score or 0),
                )
            )

        if not relevance_scores:
            return fallback

        raw = int(round(sum(relevance_scores) / len(relevance_scores)))
        return max(0, min(100, raw))

    @classmethod
    def _domain_salary_range(cls, *, domain_ids: list) -> dict[str, int] | None:
        from jobs.models import Job

        agg = Job.objects.filter(
            Q(domain_id__in=domain_ids) | Q(domain__parent_id__in=domain_ids),
            is_active=True,
            deleted=False,
        ).aggregate(
            salary_min=Min("salary_min"),
            salary_max=Max("salary_max"),
            job_count=Count("id"),
        )
        if not agg.get("job_count"):
            return None
        if agg.get("salary_min") is None and agg.get("salary_max") is None:
            return None
        return {
            "min": agg.get("salary_min"),
            "max": agg.get("salary_max"),
        }

    @classmethod
    def _domain_report_meta(cls, domain_code: str) -> dict[str, Any] | None:
        if not domain_code:
            return None
        row = (
            DomainReportMeta.objects.filter(domain_code__iexact=domain_code)
            .only(
                "degrees",
                "careers",
                "note",
                "direction_why",
                "next_step_1",
                "next_step_2",
                "next_step_3",
            )
            .first()
        )
        if not row:
            return None
        return {
            "degrees": row.degrees_list(),
            "careers": row.careers_list(),
            "note": row.note,
            "direction_why": row.direction_why,
            "next_steps": row.next_steps(),
        }
