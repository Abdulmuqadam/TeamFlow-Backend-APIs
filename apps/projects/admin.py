from django.contrib import admin

from .models import Project, Task


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "organization",
        "status",
        "created_by",
        "created_at",
    )

    list_filter = (
        "status",
        "organization",
    )

    search_fields = (
        "name",
        "description",
    )


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "project",
        "status",
        "priority",
        "assigned_to",
        "due_date",
    )

    list_filter = (
        "status",
        "priority",
    )

    search_fields = (
        "title",
        "description",
    )
