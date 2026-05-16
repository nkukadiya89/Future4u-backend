from __future__ import annotations

from typing import Any

from django.db.models import Avg, Count, Max, Min, Q

from assessment.models import StudentAssessment
from assessment.services.domain_config import get_domain_config
from career.models import Career
from courses.models import Course
from domain.models import Domain, DomainCounsellorKnowledge, DomainReportMeta
from domain_career_mapping.models import DomainCareerMapping
from domain_skill_mapping.models import DomainSkillMapping
from jobs.models import Job


class CareerKnowledgeRetriever:
    """PostgreSQL-only career knowledge (seeded via CSV imports). No in-code domain dictionaries."""

    MAX_CAREERS = 8

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
            domain_ids=knowledge_domain_ids,
            career_ids=[career.id for career, _ in career_entries],
        )
        skill_match_score = cls._aggregate_skill_match_score(knowledge_domain_ids)
        jobs_meta = cls._jobs_meta(domain_ids=knowledge_domain_ids)
        report_meta = cls._domain_report_meta_for_assessment(assessment, domain_ids)
        counsellor = cls._counsellor_for_assessment(assessment, domain_ids)
        roadmap_steps = cls._roadmap_steps_for_assessment(assessment)
        certifications = cls._certifications(domain_ids=knowledge_domain_ids)

        results: list[dict[str, Any]] = []
        for career, mapping_weight in career_entries:
            career_key = str(career.id)
            min_edu = career.min_education_level
            max_edu = career.max_education_level

            results.append(
                {
                    "career_id": career_key,
                    "career_code": career.career_code,
                    "career_name": career.career_name,
                    "description": (career.description or "")[:800],
                    "mapping_weight": mapping_weight,
                    "skill_match_score": skill_match_score,
                    "domain_name": domain.domain_name,
                    "required_skills": skills_by_career.get(career_key, [])[:12],
                    "required_education": {
                        "min_level": getattr(min_edu, "display_name", None),
                        "max_level": getattr(max_edu, "display_name", None),
                        "min_level_code": getattr(min_edu, "level_code", None),
                        "max_level_code": getattr(max_edu, "level_code", None),
                    },
                    "career_roadmap": {
                        "steps": roadmap_steps,
                        "degrees": report_meta.get("degrees", []) if report_meta else [],
                    },
                    "direction_why": report_meta.get("direction_why", "") if report_meta else "",
                    "salary": jobs_meta.get("salary_range"),
                    "active_listings": jobs_meta.get("active_listings") or 0,
                    "work_environment": jobs_meta.get("work_modes", []),
                    "industry_trends": counsellor.get("insight") if counsellor else "",
                    "future_scope": report_meta.get("note", "") if report_meta else "",
                    "certifications": certifications[:6],
                    "career_factors": {
                        "domain_fit_weight": mapping_weight,
                        "tradeoff": counsellor.get("tradeoff") if counsellor else None,
                        "tension": counsellor.get("tension") if counsellor else None,
                    },
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
    def _counsellor_for_assessment(
        cls, assessment: StudentAssessment, domain_ids: list
    ) -> dict[str, str] | None:
        for code in cls._domain_codes_for_lookup(assessment):
            row = cls._counsellor_knowledge(code)
            if row:
                return row
        return None

    @classmethod
    def _roadmap_steps_for_assessment(cls, assessment: StudentAssessment) -> list[str]:
        """Merge next_step_* and counsellor actions from assessment domain and siblings (CSV-backed)."""
        steps: list[str] = []
        seen: set[str] = set()
        for code in cls._domain_codes_for_lookup(assessment):
            meta = cls._domain_report_meta(code)
            if meta:
                for raw in meta.get("next_steps", []):
                    step = str(raw).strip()
                    if step and step not in seen:
                        seen.add(step)
                        steps.append(step)
            counsellor = cls._counsellor_knowledge(code)
            if counsellor:
                action = (counsellor.get("action") or "").strip()
                if action and action not in seen:
                    seen.add(action)
                    steps.append(action)
            if len(steps) >= 6:
                break
        return steps[:6]

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
        seen: set = set()
        entries: list[tuple[Career, int]] = []
        for mapping in mappings:
            if mapping.career_id in seen:
                continue
            seen.add(mapping.career_id)
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

    @classmethod
    def _skills_for_careers(
        cls, *, domain_ids: list, career_ids: list
    ) -> dict[str, list[str]]:
        rows = (
            DomainSkillMapping.objects.filter(
                domain_id__in=domain_ids,
                is_active=True,
                deleted=False,
                skill__is_active=True,
                skill__deleted=False,
            )
            .select_related("skill")
            .order_by("-weight_score", "skill__skill_name")
        )
        shared: list[str] = []
        seen: set[str] = set()
        for row in rows:
            name = row.skill.skill_name
            if name not in seen:
                seen.add(name)
                shared.append(name)

        return {str(cid): shared for cid in career_ids}

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
    def _jobs_meta(cls, *, domain_ids: list) -> dict[str, Any]:
        """Optional enrichment from corporate Job posts (no CSV seed in this repo)."""
        qs = Job.objects.filter(
            Q(domain_id__in=domain_ids) | Q(domain__parent_id__in=domain_ids),
            is_active=True,
            deleted=False,
        )
        agg = qs.aggregate(
            salary_min=Min("salary_min"),
            salary_max=Max("salary_max"),
            job_count=Count("id"),
        )
        work_modes = list(
            qs.exclude(work_mode__isnull=True)
            .exclude(work_mode="")
            .values_list("work_mode", flat=True)
            .distinct()[:5]
        )
        salary_range = None
        if agg.get("salary_min") is not None or agg.get("salary_max") is not None:
            salary_range = {
                "min": agg.get("salary_min"),
                "max": agg.get("salary_max"),
            }
        return {
            "salary_range": salary_range,
            "work_modes": work_modes,
            "active_listings": agg.get("job_count") or 0,
        }

    @classmethod
    def _certifications(cls, *, domain_ids: list) -> list[str]:
        names = (
            Course.objects.filter(
                domains__id__in=domain_ids,
                deleted=False,
                is_certified=True,
            )
            .exclude(certification_name__isnull=True)
            .exclude(certification_name="")
            .values_list("certification_name", flat=True)
            .distinct()[:8]
        )
        return list(names)

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

    @classmethod
    def _counsellor_knowledge(cls, domain_code: str) -> dict[str, str] | None:
        row = (
            DomainCounsellorKnowledge.objects.filter(domain_code__iexact=domain_code)
            .only("insight", "tradeoff", "action", "tension")
            .first()
        )
        if not row:
            return None
        return {
            "insight": row.insight,
            "tradeoff": row.tradeoff,
            "action": row.action,
            "tension": row.tension,
        }
