from rest_framework import serializers

from .models import LabRequest, Patient


class PatientSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            "id",
            "patient_number",
            "first_name",
            "last_name",
            "full_name",
            "date_of_birth",
            "gender",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_full_name(self, obj) -> str:
        return f"{obj.first_name} {obj.last_name}"


class LabRequestSerializer(serializers.ModelSerializer):
    """Read serializer used when returning a lab request to the caller."""

    patient_number = serializers.CharField(source="patient.patient_number", read_only=True)
    patient_name = serializers.SerializerMethodField()

    class Meta:
        model = LabRequest
        fields = [
            "request_id",
            "patient_number",
            "patient_name",
            "test_code",
            "test_name",
            "status",
            "lis_order_number",
            "rejection_reason",
            "requested_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_patient_name(self, obj) -> str:
        return str(obj.patient)


class LabRequestCreateSerializer(serializers.ModelSerializer):
    """Write serializer with explicit validation for creating a lab request."""

    patient_number = serializers.CharField(write_only=True, max_length=50)

    class Meta:
        model = LabRequest
        fields = ["request_id", "patient_number", "test_code", "test_name"]
        read_only_fields = ["request_id"]

    def validate_patient_number(self, value):
        if not Patient.objects.filter(patient_number=value).exists():
            raise serializers.ValidationError(
                f"Patient with patient_number '{value}' does not exist."
            )
        return value

    def validate_test_code(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("test_code must not be blank.")
        return value.strip().upper()

    def validate_test_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("test_name must not be blank.")
        return value.strip()

    def validate(self, attrs):
        # request_id may be supplied by the caller (idempotency); otherwise
        # the model default (uuid4) is used when saving.
        supplied_request_id = self.initial_data.get("request_id")
        if supplied_request_id is not None:
            try:
                import uuid

                attrs["request_id"] = uuid.UUID(str(supplied_request_id))
            except (ValueError, TypeError, AttributeError):
                raise serializers.ValidationError(
                    {"request_id": "Must be a valid UUID."}
                )
        return attrs

    def create(self, validated_data):
        patient = Patient.objects.get(
            patient_number=validated_data.pop("patient_number")
        )
        return LabRequest.objects.create(patient=patient, **validated_data)
