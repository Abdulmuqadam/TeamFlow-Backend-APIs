from django.urls import path

from .views import (
    OrganizationProjectListCreateView,
    ProjectDetailView,
    ProjectStatsView,
    ProjectTaskListCreateView,
    TaskDetailView,
)

urlpatterns = [
    path(
        "organizations/<int:organization_id>/projects/",
        OrganizationProjectListCreateView.as_view(),
        name="organization-projects",
    ),
    path(
        "projects/<int:project_id>/",
        ProjectDetailView.as_view(),
        name="project-detail",
    ),
    path(
        "projects/<int:project_id>/stats/",
        ProjectStatsView.as_view(),
        name="project-stats",
    ),
    path(
        "projects/<int:project_id>/tasks/",
        ProjectTaskListCreateView.as_view(),
        name="project-tasks",
    ),
    path(
        "tasks/<int:task_id>/",
        TaskDetailView.as_view(),
        name="task-detail",
    ),
]
