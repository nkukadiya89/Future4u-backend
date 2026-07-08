from .utils import is_match
from django.core.exceptions import ObjectDoesNotExist


def match_internships(ai_skills, ai_education, user, internships_qs):
    ai_levels = [
        item.get("level_key")
        for item in ai_education.get("levels", [])
        if item.get("level_key")
    ]
    
    results = []

    for internship in internships_qs:
        internship_levels = list(internship.education_tags.values_list("level_code", flat=True))

        education_match = any(level in internship_levels for level in ai_levels)
        if not education_match:
            continue

        skill_match = [
            skill for skill in ai_skills if is_match(skill, internship.skills)
        ]
        if not skill_match:
            continue
        
        score = 0

        score += len(skill_match)*10

        if education_match:
            score += 10
        
        if internship.stipend_amount and internship.stipend_amount > 0:
            score += 5

        if internship.certificate_provided:
            score += 3
        
        if internship.mode == "offline":
            score += 10
        
        if internship.mode == "online":
            score += 5
            
        elif user.city and internship.city:
            if user.city_id == internship.city_id:
                score += 10
                
            elif user.city.state_id == internship.city.state_id:
                score += 6
        
        results.append(
            {
                "internship":internship,
                "score": score,
                "skill_matches": skill_match,
            }
        )
    results.sort(key=lambda x:x["score"], reverse=True)
    return results



def match_jobs(ai_skills, ai_education, user, jobs_qs):
    ai_levels = [
        item.get("level_key")
        for item in ai_education.get("levels", [])
        if item.get("level_key")
    ]

    results = []

    for job in jobs_qs:
        job_levels = list(job.education_tags.values_list("level_code", flat=True))
        education_match = any(level in job_levels for level in ai_levels)

        if not education_match:
            continue

        skill_match = [
            skill for skill in ai_skills if is_match(skill, job.skills)
        ]
        if not skill_match:
            continue

        score = 0

        score += len(skill_match)*10
        
        if education_match:
            score += 10

        if job.salary_max:
            score += 5
        
        if job.mode == "onsite":
            score += 10
        
        if job.mode == "remote":
            score += 5
        elif job.mode == "hybrid":
            score += 7

        if user.city and job.city:
            if user.city_id == job.city_id:
                score += 10

            elif user.city.state_id == job.city.state_id:
                score += 6  

        results.append(
            {
                "job": job,
                "score": score,
                "skill_matches": skill_match,
            }
        )
    results.sort(key=lambda x:x["score"], reverse=True)
    return results
