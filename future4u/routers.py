from rest_framework import routers
from activity_log.routers import activity_log_router
from business_category.routers import bussiness_category_router
from city.routers import city_router
from city_areas.routers import city_area_router
from company.routers import company_router
from country.routers import country_router
from employee.routers import employee_router
from end_client.routers import end_client_router
from faq.routers import faq_router
from partner_company.routers import partner_company_router
from state.routers import state_router
from user_profile.routers import user_profile_router
from user.routers import user_router


future4u_router = routers.DefaultRouter()

future4u_router.registry.extend(activity_log_router.registry)
future4u_router.registry.extend(bussiness_category_router.registry)
future4u_router.registry.extend(city_router.registry)
future4u_router.registry.extend(city_area_router.registry)
future4u_router.registry.extend(company_router.registry)
future4u_router.registry.extend(country_router.registry)
future4u_router.registry.extend(employee_router.registry)
future4u_router.registry.extend(end_client_router.registry)
future4u_router.registry.extend(faq_router.registry)
future4u_router.registry.extend(partner_company_router.registry)
future4u_router.registry.extend(state_router.registry)
future4u_router.registry.extend(user_profile_router.registry)
future4u_router.registry.extend(user_router.registry)