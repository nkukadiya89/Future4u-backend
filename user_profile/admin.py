from django.contrib import admin

from user_profile.models import BusinessSetting, UserProfile

admin.site.register(BusinessSetting)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "education_level", "stream")
    search_fields = ("user__email", "user__first_name", "user__last_name")
