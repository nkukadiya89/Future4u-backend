from django.contrib import admin

from company.models import Company, CompanyService

admin.site.register(Company)
admin.site.register(CompanyService)
