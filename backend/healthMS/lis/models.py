import uuid

from django.db import models


class LabTestCatalog(models.Model):
    """Catalog of lab tests the LIS is able to perform."""

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} - {self.name}"


class LabOrder(models.Model):
    """Mirror record of a lab test request received from the HMS."""

    class Status(models.TextChoices):
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        COMPLETED = "COMPLETED", "Completed"

    order_number = models.CharField(max_length=64, unique=True, editable=False)
    hms_request_id = models.UUIDField(unique=True, editable=False)
    patient_number = models.CharField(max_length=50)
    patient_name = models.CharField(max_length=200)
    patient_date_of_birth = models.DateField()
    test_code = models.CharField(max_length=50)
    test_name = models.CharField(max_length=200)
    status = models.CharField(
        max_length=30, choices=Status.choices, default=Status.ACCEPTED
    )
    received_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self):
        return f"{self.order_number} ({self.test_code} - {self.status})"


class LabResult(models.Model):
    """Result produced by the lab for a lab order."""

    result_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    order = models.OneToOneField(
        LabOrder, on_delete=models.CASCADE, related_name="result"
    )
    result_value = models.CharField(max_length=100)
    unit = models.CharField(max_length=50, blank=True, default="")
    reference_range = models.CharField(max_length=100, blank=True, default="")
    is_abnormal = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default="")
    performed_by = models.CharField(max_length=200)
    verified_by = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Name of the lab supervisor who verified the result.",
    )
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order.order_number} -> {self.result_value} {self.unit}"
