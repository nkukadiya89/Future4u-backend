from __future__ import annotations

from typing import Any

from education_level.models import EducationLevel
from job_generation.exceptions import JobGenerationAccessDeniedError
from job_generation.schemas.job_output import JobGenerationPayload
from job_generation.selectors.job_generation_access import can_user_generate_jobs
from job_generation.services.job_generator import JobGenerator
from job_generation.utils import resolve_education_tag_meta
from user_profile.models import CorporateProfile


class JobGenerationService:
    """Orchestrates AI job posting generation for institute and corporate users."""

    def generate(self, *, user, validated_input: dict[str, Any]) -> tuple[dict[str, Any], int]:
        if not can_user_generate_jobs(user):
            raise JobGenerationAccessDeniedError(
                "Job generation is only available for corporate accounts"
            )

        corporate_id = validated_input.get("corporate")
        if isinstance(corporate_id, CorporateProfile):
            company = corporate_id
        else:
            company = CorporateProfile.objects.filter(id=corporate_id, deleted=False).first()
        if not company:
            from job_generation.exceptions import JobGenerationValidationError
            raise JobGenerationValidationError(
                "CorporateProfile not found",
                error="Invalid corporate ID",
                details="The selected company does not exist.",
            )

        generation_input = {
            **validated_input,
            "company_name": company.company_name or "",
            "company_website": company.website or "",
            "company_about_us": company.about_us or "",
        }

        payload, token_usage = JobGenerator.generate(generation_input=generation_input)
        return _build_response(payload, validated_input, company), token_usage



def _build_response(
    payload: JobGenerationPayload,
    validated_input: dict[str, Any],
    company: CorporateProfile | None = None,
) -> dict[str, Any]:
    data = payload.model_dump()

    # Enrich education_tags: list[str] → list[{name, type, level_key}]
    enriched_tags = [
        resolve_education_tag_meta(tag) for tag in data.get("education_tags", [])
    ]

    # Resolve education tag metadata to actual EducationLevel DB records.
    # Multiple AI tags can share the same level_key (e.g. "BCA" and "B.Tech"
    # both map to "graduation") — keep all of them in education_tags_meta for
    # display, but deduplicate the resolved PKs so the DB M2M gets only one ID
    # per level_key.
    level_codes = [t["level_key"] for t in enriched_tags if t.get("level_key")]
    if level_codes:
        levels = EducationLevel.objects.filter(level_code__in=set(level_codes))
        level_map: dict[str, int] = {l.level_code: l.pk for l in levels}
        seen_pks: set[int] = set()
        resolved_pks = []
        for t in enriched_tags:
            pk = level_map.get(t.get("level_key", ""))
            if pk is not None and pk not in seen_pks:
                seen_pks.add(pk)
                resolved_pks.append(pk)
    else:
        resolved_pks = []

    # education_tags      → unique PKs only (used when saving to DB via POST /job/)
    # education_tags_meta → all AI-generated names/types/keys (used for display)
    data["education_tags"] = resolved_pks
    data["education_tags_meta"] = enriched_tags

    if company:
        data["corporate"] = company.pk
        data["corporate_name"] = company.company_name or ""
    else:
        corporate = validated_input.get("corporate")
        data["corporate"] = corporate.pk if hasattr(corporate, "pk") else corporate
        data["corporate_name"] = ""
    data["job_overview"] = validated_input.get("job_overview", "")
    country = validated_input.get("country")
    data["country"] = country.pk if country else None
    data["country_name"] = country.name if country else ""
    state = validated_input.get("state")
    data["state"] = state.pk if state else None
    data["state_name"] = state.name if state else ""
    city = validated_input.get("city")
    data["city"] = city.pk if city else None
    data["city_name"] = city.name if city else ""
    data["salary_min"] = float(validated_input["salary_min"]) if validated_input.get("salary_min") is not None else None
    data["salary_max"] = float(validated_input["salary_max"]) if validated_input.get("salary_max") is not None else None
    data["job_type"] = validated_input.get("job_type", "")
    data["experience_level"] = validated_input.get("experience_level", "")
    data["mode"] = validated_input.get("mode", "")
    deadline = validated_input.get("application_deadline")
    data["application_deadline"] = deadline.isoformat() if deadline else None
    return data


