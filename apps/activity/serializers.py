from rest_framework import serializers

from .models import Activity
from .notification_models import Notification


class ActivitySerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(
        source="actor.email",
        read_only=True,
    )

    class Meta:
        model = Activity
        fields = (
            "id",
            "task",
            "actor",
            "actor_email",
            "action",
            "message",
            "metadata",
            "created_at",
        )
        read_only_fields = fields


class NotificationSerializer(serializers.ModelSerializer):
    task_title = serializers.CharField(
        source="task.title",
        read_only=True,
    )

    class Meta:
        model = Notification
        fields = (
            "id",
            "task",
            "task_title",
            "notification_type",
            "message",
            "is_read",
            "created_at",
        )
        read_only_fields = fields
