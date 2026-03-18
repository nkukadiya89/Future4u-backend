from django.contrib import admin

from activity_log.models import ActivityLog, WhatsAppMessageLog

# Register your models here.

admin.site.register(ActivityLog)
admin.site.register(WhatsAppMessageLog)
