from django.contrib import admin

from .models import LabOrder, LabResult, LabTestCatalog


@admin.register(LabTestCatalog)
class LabTestCatalogAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    search_fields = ("code", "name")


class LabResultInline(admin.StackedInline):
    model = LabResult
    can_delete = False
    readonly_fields = [f.name for f in LabResult._meta.fields]


@admin.register(LabOrder)
class LabOrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "hms_request_id",
        "patient_number",
        "patient_name",
        "test_code",
        "status",
        "received_at",
    )
    list_filter = ("status", "test_code")
    search_fields = ("order_number", "hms_request_id", "patient_number")
    readonly_fields = [f.name for f in LabOrder._meta.fields]
    inlines = [LabResultInline]

    def has_add_permission(self, request):
        return False


@admin.register(LabResult)
class LabResultAdmin(admin.ModelAdmin):
    list_display = (
        "result_id",
        "order",
        "result_value",
        "unit",
        "is_abnormal",
        "performed_by",
        "completed_at",
    )
    search_fields = ("order__order_number", "result_id")
