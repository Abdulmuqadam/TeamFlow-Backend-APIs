from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from apps.organizations.models import Membership
from apps.projects.permissions import IsOrganizationAdminForOrganization
from .models import Project, Task
from .serializers import ProjectSerializer, TaskSerializer
from django.shortcuts import get_object_or_404
from .permissions import IsOrganizationAdminForProject, IsOrganizationMemberForProject


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
    permission_classes = [
        IsAuthenticated,
    ]

    def get_project(self):
        return get_object_or_404(
            Project,
            id=self.kwargs["project_id"],
        )

    def get_queryset(self):
        project = self.get_project()

        is_member = Membership.objects.filter(
            user=self.request.user,
            organization=project.organization,
        ).exists()

        if not is_member:
            raise PermissionDenied("You are not a member of this organization.")

        return Task.objects.filter(
            project=project,
        ).select_related(
            "project",
            "assigned_to",
            "created_by",
        )

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
