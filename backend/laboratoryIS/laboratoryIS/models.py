import uuid
from django.db import models


class LaboratoryRequest(models.Model):

    STATUS_CHOICES = [
        ("RECEIVED", "Received"),
        ("PROCESSING", "Processing"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]

    request_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    patient_id = models.CharField(max_length=100)

    test_code = models.CharField(max_length=50)

    test_name = models.CharField(max_length=200)

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="RECEIVED"
    )

    requested_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"{self.request_id} - {self.test_name}"

        class LaboratoryResult(models.Model):

    request = models.OneToOneField(
        LaboratoryRequest,
        on_delete=models.CASCADE,
        related_name="result"
    )

    result_value = models.TextField()

    unit = models.CharField(
        max_length=50,
        blank=True
    )

    reference_range = models.CharField(
        max_length=100,
        blank=True
    )

    verified = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return str(self.request.request_id)