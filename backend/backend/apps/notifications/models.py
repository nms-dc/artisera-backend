import uuid

from django.conf import settings
from django.db import models


class Notification(models.Model):

    class Type(models.TextChoices):
        FOLLOWUP_DUE = "FOLLOWUP_DUE", "FOLLOWUP_DUE"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    type = models.CharField(
        max_length=50,
        choices=Type.choices,
    )

    title = models.CharField(
        max_length=255,
    )

    body = models.TextField()

    inquiry = models.ForeignKey(
        "inquiries.Inquiry",
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )

    customer = models.ForeignKey(
        "inquiries.Customer",
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )

    tab = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    is_read = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title