from rest_framework import routers
from activity_log.routers import activity_log_router
from business_category.routers import bussiness_category_router
from city.routers import city_router
from company.routers import company_router
from country.routers import country_router
from education_level.routers import education_level_router
from employee.routers import employee_router
from faq.routers import faq_router
from state.routers import state_router
from stream.routers import stream_router
from stream_domain_mapping.routers import stream_domain_mapping_router
from user_profile.routers import user_profile_router
from user.routers import user_router

try:
    from domain.routers import domain_router
except ModuleNotFoundError:
    domain_router = None


future4u_router = routers.DefaultRouter()

future4u_router.registry.extend(activity_log_router.registry)
future4u_router.registry.extend(bussiness_category_router.registry)
future4u_router.registry.extend(city_router.registry)
future4u_router.registry.extend(company_router.registry)
future4u_router.registry.extend(country_router.registry)
if domain_router is not None:
    future4u_router.registry.extend(domain_router.registry)
future4u_router.registry.extend(education_level_router.registry)
future4u_router.registry.extend(employee_router.registry)
future4u_router.registry.extend(faq_router.registry)
future4u_router.registry.extend(state_router.registry)
future4u_router.registry.extend(stream_router.registry)
future4u_router.registry.extend(stream_domain_mapping_router.registry)
future4u_router.registry.extend(user_profile_router.registry)
future4u_router.registry.extend(user_router.registry)