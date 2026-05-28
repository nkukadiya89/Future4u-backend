from rest_framework import routers

from activity_log.routers import activity_log_router
from assessment.routers import assessment_router
from business_category.routers import bussiness_category_router
from career.routers import career_router
from city.routers import city_router
from company.routers import company_router
from country.routers import country_router
from domain_career_mapping.routers import domain_career_mapping_router
from domain_skill_mapping.routers import domain_skill_mapping_router
from education_level.routers import education_level_router
from employee.routers import employee_router
from faq.routers import faq_router
from jobs.routers import job_router
from skill.routers import skill_router
from state.routers import state_router
from stream.routers import stream_router
from stream_domain_mapping.routers import stream_domain_mapping_router
from user.routers import user_router
from user_profile.routers import user_profile_router
from user_skill.routers import user_skill_router
from assessment_career.routers import assessment_career_router
from course.routers import courses_router
# from subscription.routers import subscription_router

try:
    from domain.routers import domain_router
except ModuleNotFoundError:
    domain_router = None


from language_master.routers import language_router

future4u_router = routers.DefaultRouter()

future4u_router.registry.extend(activity_log_router.registry)
future4u_router.registry.extend(assessment_career_router.registry)
future4u_router.registry.extend(language_router.registry)
future4u_router.registry.extend(assessment_router.registry)
future4u_router.registry.extend(bussiness_category_router.registry)
future4u_router.registry.extend(career_router.registry)
future4u_router.registry.extend(city_router.registry)
future4u_router.registry.extend(company_router.registry)
future4u_router.registry.extend(country_router.registry)
if domain_router is not None:
    future4u_router.registry.extend(domain_router.registry)
future4u_router.registry.extend(education_level_router.registry)
future4u_router.registry.extend(employee_router.registry)
future4u_router.registry.extend(faq_router.registry)
future4u_router.registry.extend(skill_router.registry)
future4u_router.registry.extend(state_router.registry)
future4u_router.registry.extend(stream_router.registry)
future4u_router.registry.extend(stream_domain_mapping_router.registry)
future4u_router.registry.extend(domain_skill_mapping_router.registry)
future4u_router.registry.extend(domain_career_mapping_router.registry)
future4u_router.registry.extend(user_profile_router.registry)
future4u_router.registry.extend(user_skill_router.registry)
future4u_router.registry.extend(user_router.registry)
future4u_router.registry.extend(job_router.registry)
future4u_router.registry.extend(courses_router.registry)
# future4u_router.registry.extend(subscription_router.registry)
