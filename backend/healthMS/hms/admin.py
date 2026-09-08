from django.contrib import admin

from .models import LabRequest, Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        "patient_number",
        "first_name",
        "last_name",
        "date_of_birth",
        "gender",
        "created_at",
    )
    search_fields = ("patient_number", "first_name", "last_name")


@admin.register(LabRequest)
class LabRequestAdmin(admin.ModelAdmin):
    list_display = (
        "request_id",
        "patient",
        "test_code",
        "test_name",
        "status",
        "lis_order_number",
        "requested_at",
    )
    list_filter = ("status", "test_code")
    search_fields = ("request_id", "patient__patient_number", "test_code")
    readonly_fields = (
        "request_id",
        "patient",
        "test_code",
        "test_name",
        "status",
        "lis_order_number",
        "rejection_reason",
        "requested_at",
        "updated_at",
    )
