from rest_framework import serializers

from .models import LabOrder, LabResult, LabTestCatalog


class LabTestCatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabTestCatalog
        fields = ["code", "name", "description", "is_active"]


class LabOrderSerializer(serializers.ModelSerializer):
    result = serializers.SerializerMethodField()

    class Meta:
        model = LabOrder
        fields = [
            "order_number",
            "hms_request_id",
            "patient_number",
            "patient_name",
            "patient_date_of_birth",
            "test_code",
            "test_name",
            "status",
            "result",
            "received_at",
            "updated_at",
        ]

    def get_result(self, obj):
        result = getattr(obj, "result", None)
        if result is None:
            return None
        return LabResultSerializer(result).data


class LabResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabResult
        fields = [
            "result_id",
            "result_value",
            "unit",
            "reference_range",
            "is_abnormal",
            "notes",
            "performed_by",
            "verified_by",
            "completed_at",
        ]


class LabOrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=LabOrder.Status.choices)


class LabOrderIngestSerializer(serializers.Serializer):
    """Validates the payload the HMS sends when submitting a lab request."""

    request_id = serializers.UUIDField()
    patient_number = serializers.CharField(max_length=50)
    patient_first_name = serializers.CharField(max_length=100)
    patient_last_name = serializers.CharField(max_length=100)
    patient_date_of_birth = serializers.DateField()
    test_code = serializers.CharField(max_length=50)
    test_name = serializers.CharField(max_length=200)

    def validate_test_code(self, value):
        if not value.strip():
            raise serializers.ValidationError("test_code must not be blank.")
        return value.strip().upper()

    def validate_patient_number(self, value):
        if not value.strip():
            raise serializers.ValidationError("patient_number must not be blank.")
        return value.strip()

    def validate(self, attrs):
        first = attrs.get("patient_first_name", "").strip()
        last = attrs.get("patient_last_name", "").strip()
        if not first or not last:
            raise serializers.ValidationError(
                "patient_first_name and patient_last_name must not be blank."
            )
        return attrs
