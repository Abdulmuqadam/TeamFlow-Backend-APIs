from django.conf import settings
from django.db import models


class Activity(models.Model):
    class Action(models.TextChoices):
        TASK_CREATED = "TASK_CREATED", "Task created"
        TASK_UPDATED = "TASK_UPDATED", "Task updated"
        TASK_ASSIGNED = "TASK_ASSIGNED", "Task assigned"
        STATUS_CHANGED = "STATUS_CHANGED", "Status changed"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="activities",
    )

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="activities",
    )

    task = models.ForeignKey(
        "projects.Task",
        on_delete=models.CASCADE,
        related_name="activities",
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="activities",
    )

    action = models.CharField(
        max_length=30,
        choices=Action.choices,
    )

    message = models.CharField(max_length=255)

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.actor} - {self.action}"
