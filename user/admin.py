from django.contrib import admin

from user.models import CustomGroup, EmailPhoneVerify, RoleFamily, User

# Register your models here.

admin.site.register(User)
admin.site.register(RoleFamily)
admin.site.register(EmailPhoneVerify)


class CustomGroupAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "sequence")


admin.site.register(CustomGroup, CustomGroupAdmin)
