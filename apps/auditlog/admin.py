from django.contrib import admin

from apps.auditlog.models import AuditLogEntry


@admin.register(AuditLogEntry)
class AuditLogEntryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "account", "actor", "action", "event", "target_type", "target_id")
    list_filter = ("action", "created_at")
    search_fields = ("account__name", "actor__email", "action", "target_type", "target_id", "message")
    ordering = ("-created_at", "-id")
