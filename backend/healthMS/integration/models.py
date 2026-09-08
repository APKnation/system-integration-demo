import uuid
from django.db import models


class IntegrationLog(models.Model):

    transaction_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True
    )

    request_id = models.UUIDField(
        null=True,
        blank=True
    )

    endpoint = models.CharField(
        max_length=255
    )

    method = models.CharField(
        max_length=10
    )

    status_code = models.IntegerField()

    status = models.CharField(
        max_length=30
    )

    error_message = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return str(self.transaction_id)