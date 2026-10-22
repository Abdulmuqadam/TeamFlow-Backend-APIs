from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Project, Task

User = get_user_model()


class ProjectSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(
        source="created_by.email",
        read_only=True,
    )

    class Meta:
        model = Project
        fields = (
            "id",
            "organization",
            "name",
            "description",
            "status",
            "created_by",
            "created_by_email",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "organization",
            "created_by",
            "created_by_email",
            "created_at",
            "updated_at",
        )


class TaskSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(
        source="created_by.email",
        read_only=True,
    )

    assigned_to_email = serializers.EmailField(
        source="assigned_to.email",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Task

        fields = (
            "id",
            "project",
            "title",
            "description",
            "status",
            "priority",
            "assigned_to",
            "assigned_to_email",
            "created_by",
            "created_by_email",
            "due_date",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "project",
            "created_by",
            "created_by_email",
            "assigned_to_email",
            "created_at",
            "updated_at",
        )

    def validate_title(self, value):
        cleaned_value = value.strip() if isinstance(value, str) else value

        if not cleaned_value:
            raise serializers.ValidationError("Task title cannot be empty.")

        return cleaned_value

    def validate(self, attrs):
        assigned_to = attrs.get("assigned_to")

        if not assigned_to:
            return attrs

        project = self.context.get("project")

        if not project and self.instance:
            project = self.instance.project

        if not project:
            return attrs

        is_member = project.organization.members.filter(id=assigned_to.id).exists()

        if not is_member:
            raise serializers.ValidationError(
                {"assigned_to": "User must belong to the project organization."}
            )

        return attrs


class ProjectStatsSerializer(serializers.Serializer):
    project_id = serializers.IntegerField()
    project_name = serializers.CharField()
    total_tasks = serializers.IntegerField()
    todo = serializers.IntegerField()
    in_progress = serializers.IntegerField()
    done = serializers.IntegerField()
