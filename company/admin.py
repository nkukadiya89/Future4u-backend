from django.contrib import admin

from company.models import Attachment, Company, CompanyEmail, CompanyProfile, KeyPersons


class CompanyAdmin(admin.ModelAdmin):
    class Media:
        js = ("company/company_admin.js",)


admin.site.register(Company, CompanyAdmin)
admin.site.register(KeyPersons)
admin.site.register(Attachment)
admin.site.register(CompanyEmail)
admin.site.register(CompanyProfile)
