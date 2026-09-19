from django.db import models
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.organizations.models import Membership
from apps.projects.permissions import IsOrganizationAdminForOrganization

from .models import Project, Task
from .pagination import TaskPagination
from .permissions import IsOrganizationAdminForProject, IsOrganizationMemberForProject
from .serializers import ProjectSerializer, TaskSerializer


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

        queryset = Task.objects.filter(
            project=project,
        ).select_related(
            "project",
            "assigned_to",
            "created_by",
        )

        status = self.request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status)

        priority = self.request.query_params.get("priority")
        if priority:
            queryset = queryset.filter(priority=priority)

        assigned_to = self.request.query_params.get("assigned_to")
        if assigned_to:
            queryset = queryset.filter(assigned_to_id=assigned_to)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                models.Q(title__icontains=search)
                | models.Q(description__icontains=search)
            )

        ordering = self.request.query_params.get("ordering", "-created_at")
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

        serializer.save(
            project=project,
            created_by=self.request.user,
        )


class ProjectStatsView(generics.RetrieveAPIView):
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

        stats = project.tasks.aggregate(
            total_tasks=Count("id"),
            todo=Count("id", filter=Q(status=Task.Status.TODO)),
            in_progress=Count("id", filter=Q(status=Task.Status.IN_PROGRESS)),
            done=Count("id", filter=Q(status=Task.Status.DONE)),
        )

        return Response(
            {
                "project_id": project.id,
                "project_name": project.name,
                **stats,
            }
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
        task = self.get_object()

        membership = get_object_or_404(
            Membership,
            user=self.request.user,
            organization=task.project.organization,
        )

        # Admins and owners can update any task
        if membership.role in [
            Membership.Role.OWNER,
            Membership.Role.ADMIN,
        ]:
            serializer.save()
            return

        # Regular members can update tasks assigned to them
        if task.assigned_to == self.request.user:
            serializer.save()
            return

        raise PermissionDenied("You can only update tasks assigned to you.")

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
