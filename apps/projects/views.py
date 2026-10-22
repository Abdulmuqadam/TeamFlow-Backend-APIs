from typing import cast

from django.db import models
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.activity.models import Activity
from apps.activity.notification_services import (
    notify_task_assigned,
    notify_task_status_changed,
)
from apps.activity.services import record_task_activity
from apps.organizations.models import Membership
from apps.projects.permissions import IsOrganizationAdminForOrganization
from apps.projects.services import update_task_with_events

from .models import Project, Task
from .pagination import TaskPagination
from .permissions import IsOrganizationAdminForProject, IsOrganizationMemberForProject
from .serializers import ProjectSerializer, ProjectStatsSerializer, TaskSerializer


class OrganizationProjectListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [
                IsAuthenticated(),
                IsOrganizationAdminForOrganization(),
            ]

        return [
            IsAuthenticated(),
        ]

    def get_queryset(self):
        organization_id = self.kwargs["organization_id"]

        is_member = Membership.objects.filter(
            user=self.request.user,
            organization_id=organization_id,
        ).exists()

        if not is_member:
            raise PermissionDenied("You are not a member of this organization.")

        return Project.objects.filter(
            organization_id=organization_id,
        ).select_related(
            "created_by",
            "organization",
        )

    def perform_create(self, serializer):
        organization_id = self.kwargs["organization_id"]

        serializer.save(
            organization_id=organization_id,
            created_by=self.request.user,
        )


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectSerializer
    lookup_url_kwarg = "project_id"

    def get_queryset(self):
        return Project.objects.all().select_related(
            "organization",
            "created_by",
        )

    def get_permissions(self):
        if self.request.method in [
            "PATCH",
            "PUT",
            "DELETE",
        ]:
            return [
                IsAuthenticated(),
                IsOrganizationAdminForProject(),
            ]

        return [
            IsAuthenticated(),
            IsOrganizationMemberForProject(),
        ]


class ProjectTaskListCreateView(generics.ListCreateAPIView):
    serializer_class = TaskSerializer
    pagination_class = TaskPagination
    permission_classes = [
        IsAuthenticated,
    ]

    def get_project(self):
        project = get_object_or_404(
            Project.objects.select_related("organization"),
            id=self.kwargs["project_id"],
        )

        is_member = Membership.objects.filter(
            user=self.request.user,
            organization=project.organization,
        ).exists()

        if not is_member:
            raise PermissionDenied("You are not a member of this organization.")

        return project

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["project"] = self.get_project()
        return context

    def get_queryset(self):
        project = self.get_project()
        request = cast(Request, self.request)

        queryset = Task.objects.filter(
            project=project,
        ).select_related(
            "project",
            "assigned_to",
            "created_by",
        )

        status = request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status)

        priority = request.query_params.get("priority")
        if priority:
            queryset = queryset.filter(priority=priority)

        assigned_to = request.query_params.get("assigned_to")
        if assigned_to:
            queryset = queryset.filter(assigned_to_id=assigned_to)

        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(title__icontains=search)
                | models.Q(description__icontains=search)
            )

        ordering = request.query_params.get("ordering", "-created_at")
        allowed_orderings = {
            "created_at",
            "-created_at",
            "due_date",
            "-due_date",
            "priority",
            "-priority",
        }

        if ordering in allowed_orderings:
            queryset = queryset.order_by(ordering)

        return queryset

    def perform_create(self, serializer):
        project = self.get_project()

        is_admin = Membership.objects.filter(
            user=self.request.user,
            organization=project.organization,
            role__in=[
                Membership.Role.OWNER,
                Membership.Role.ADMIN,
            ],
        ).exists()

        if not is_admin:
            raise PermissionDenied("Only organization admins can create tasks.")

        task = serializer.save(
            project=project,
            created_by=self.request.user,
        )

        record_task_activity(
            task=task,
            actor=self.request.user,
            action=Activity.Action.TASK_CREATED,
            message=f'Created task "{task.title}"',
        )


class ProjectStatsView(generics.GenericAPIView):
    serializer_class = ProjectStatsSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        project = get_object_or_404(
            Project.objects.select_related("organization"),
            id=kwargs["project_id"],
        )

        is_member = Membership.objects.filter(
            user=request.user,
            organization=project.organization,
        ).exists()

        if not is_member:
            raise PermissionDenied("You are not a member of this organization.")

        stats = Task.objects.filter(project=project).aggregate(
            total_tasks=Count("id"),
            todo=Count("id", filter=Q(status=Task.Status.TODO)),
            in_progress=Count("id", filter=Q(status=Task.Status.IN_PROGRESS)),
            done=Count("id", filter=Q(status=Task.Status.DONE)),
        )

        return Response(
            self.get_serializer(
                {
                    "project_id": project.pk,
                    "project_name": project.name,
                    **stats,
                }
            ).data
        )


class TaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskSerializer
    lookup_url_kwarg = "task_id"

    def get_queryset(self):
        return Task.objects.all().select_related(
            "project",
            "project__organization",
            "assigned_to",
            "created_by",
        )

    def get_object(self):
        task = get_object_or_404(
            self.get_queryset(),
            id=self.kwargs["task_id"],
        )

        is_member = Membership.objects.filter(
            user=self.request.user,
            organization=task.project.organization,
        ).exists()

        if not is_member:
            raise PermissionDenied("You are not a member of this organization.")

        return task

    def perform_update(self, serializer):
        update_task_with_events(
            serializer=serializer,
            actor=self.request.user,
        )

    def perform_destroy(self, instance):
        membership = get_object_or_404(
            Membership,
            user=self.request.user,
            organization=instance.project.organization,
        )

        if membership.role not in [
            Membership.Role.OWNER,
            Membership.Role.ADMIN,
        ]:
            raise PermissionDenied("Only organization admins can delete tasks.")

        instance.delete()
