"""
Assessment recommendation engine: career, skill, and domain scoring from responses.
"""

from django.db import transaction
from django.db.models import Prefetch

from assessment.models import (
    AssessmentCareerRecommendation,
    AssessmentDomainScore,
    AssessmentSkillScore,
    OptionCareerMapping,
    OptionSkillMapping,
    UserResponse,
)
from career.models import Career
from domain.models import Domain


def calculate_career_scores(assessment):
    """
    Weighted career scores from the student's selected options via OptionCareerMapping.
    Returns dict mapping career_id -> aggregated float score.
    """
    responses = (
        UserResponse.objects.filter(assessment=assessment)
        .select_related("selected_option")
        .only("id", "selected_option_id")
    )
    option_ids = [r.selected_option_id for r in responses if r.selected_option_id]
    if not option_ids:
        return {}

    mappings = OptionCareerMapping.objects.filter(option_id__in=option_ids).only(
        "career_id", "weight", "option_id"
    )
    career_scores = {}
    for mapping in mappings:
        cid = mapping.career_id
        career_scores[cid] = career_scores.get(cid, 0.0) + float(mapping.weight)
    return career_scores


def calculate_skill_scores(assessment):
    """
    Aggregate OptionSkillMapping weights per skill for this assessment's responses.
    Deletes prior rows and bulk_creates AssessmentSkillScore.
    """
    responses = (
        UserResponse.objects.filter(assessment=assessment)
        .select_related("selected_option")
        .only("id", "selected_option_id")
    )
    option_ids = [r.selected_option_id for r in responses if r.selected_option_id]
    skill_scores = {}
    if option_ids:
        mappings = OptionSkillMapping.objects.filter(option_id__in=option_ids).only(
            "skill_id", "weight", "option_id"
        )
        for mapping in mappings:
            sid = mapping.skill_id
            skill_scores[sid] = skill_scores.get(sid, 0.0) + float(mapping.weight)

    AssessmentSkillScore.objects.filter(assessment=assessment).delete()
    to_create = [
        AssessmentSkillScore(assessment=assessment, skill_id=sid, score=score)
        for sid, score in skill_scores.items()
    ]
    if to_create:
        AssessmentSkillScore.objects.bulk_create(to_create)
    return skill_scores


def calculate_domain_scores(assessment):
    """
    Domain affinity from each answered question's mapped_domains and signal_strength.
    Deletes prior rows and bulk_creates AssessmentDomainScore.
    """
    domain_prefetch = Prefetch(
        "question__mapped_domains",
        queryset=Domain.objects.only("id"),
    )
    responses = (
        UserResponse.objects.filter(assessment=assessment)
        .select_related("question")
        .prefetch_related(domain_prefetch)
        .only("id", "question_id", "question__signal_strength")
    )

    domain_scores = {}
    for resp in responses:
        question = resp.question
        strength = float(question.signal_strength)
        for domain in question.mapped_domains.all():
            did = domain.id
            domain_scores[did] = domain_scores.get(did, 0.0) + strength

    AssessmentDomainScore.objects.filter(assessment=assessment).delete()
    to_create = [
        AssessmentDomainScore(assessment=assessment, domain_id=did, score=score)
        for did, score in domain_scores.items()
    ]
    if to_create:
        AssessmentDomainScore.objects.bulk_create(to_create)
    return domain_scores


def generate_reasoning(career, score):
    """
    Build a short human-readable explanation list for a recommended career.
    """
    reasons = []
    if score > 10:
        reasons.append("Strong analytical aptitude")
    if score > 5:
        reasons.append("High interest in technology")
    if score > 0:
        reasons.append("Logical problem-solving patterns detected")
    if not reasons:
        reasons.append("Logical problem-solving patterns detected")
    return reasons


def save_career_recommendations(assessment):
    """
    Replace existing career recommendations with a freshly ranked set from responses.
    """
    AssessmentCareerRecommendation.objects.filter(assessment=assessment).delete()
    career_scores = calculate_career_scores(assessment)
    if not career_scores:
        return []

    max_score = max(career_scores.values()) or 1.0
    ranked = sorted(career_scores.items(), key=lambda x: x[1], reverse=True)
    career_ids = [cid for cid, _ in ranked]
    careers_by_id = Career.objects.in_bulk(career_ids)

    objs = []
    for idx, (career_id, score) in enumerate(ranked, start=1):
        career = careers_by_id.get(career_id)
        match_pct = (float(score) / float(max_score)) * 100.0 if max_score else 0.0
        reasoning = generate_reasoning(career, float(score)) if career else []
        objs.append(
            AssessmentCareerRecommendation(
                assessment=assessment,
                career_id=career_id,
                score=float(score),
                rank=idx,
                match_percentage=match_pct,
                reasoning=reasoning,
                is_recommended=True,
            )
        )
    AssessmentCareerRecommendation.objects.bulk_create(objs)
    return objs


def generate_full_assessment_result(assessment):
    """
    Orchestrate skill scores, domain scores, and persisted career recommendations.
    """
    with transaction.atomic():
        calculate_skill_scores(assessment)
        calculate_domain_scores(assessment)
        save_career_recommendations(assessment)
