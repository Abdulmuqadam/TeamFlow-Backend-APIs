from rest_framework import serializers

from .models import Activity


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
