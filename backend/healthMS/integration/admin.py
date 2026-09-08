from django.contrib import admin

from .models import IntegrationLog


@admin.register(IntegrationLog)
class IntegrationLogAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_id",
        "endpoint",
        "method",
        "status_code",
        "status",
        "request_id",
        "created_at",
    )
    list_filter = ("status", "method", "status_code")
    search_fields = ("endpoint", "error_message", "request_id")
    readonly_fields = (
        "transaction_id",
        "request_id",
        "endpoint",
        "method",
        "status_code",
        "status",
        "error_message",
        "created_at",
    )
