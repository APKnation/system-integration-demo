import uuid

from django.db import models


class Patient(models.Model):
    GENDER_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
       
    ]

    patient_number = models.CharField(max_length=50, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["patient_number"]

    def __str__(self):
        return f"{self.patient_number} - {self.first_name} {self.last_name}"


class LabRequest(models.Model):
    """A lab test request raised by the HMS against the LIS."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent to LIS"
        REJECTED = "REJECTED", "Rejected by LIS"
        ERROR = "ERROR", "Delivery error"
        COMPLETED = "COMPLETED", "Completed"

    request_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="lab_requests"
    )
    test_code = models.CharField(max_length=50)
    test_name = models.CharField(max_length=200)
    status = models.CharField(
        max_length=30, choices=Status.choices, default=Status.PENDING
    )
    lis_order_number = models.CharField(max_length=64, blank=True, default="")
    rejection_reason = models.TextField(blank=True, default="")
    requested_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"{self.request_id} ({self.test_code} - {self.status})"
