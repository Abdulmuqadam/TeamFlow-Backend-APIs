from rest_framework.permissions import BasePermission

from apps.organizations.models import Membership

from .models import Project


class IsOrganizationMemberForProject(BasePermission):
    """
    Allows access only to members of the project's organization.
    """

    def has_permission(self, request, view):
        project_id = view.kwargs.get("project_id")

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return False

        return Membership.objects.filter(
            user=request.user,
            organization=project.organization,
        ).exists()


class IsOrganizationAdminForProject(BasePermission):
    """
    Allows OWNER or ADMIN access to project management.
    """

    def has_permission(self, request, view):
        project_id = view.kwargs.get("project_id")

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return False

        return Membership.objects.filter(
            user=request.user,
            organization=project.organization,
            role__in=[
                Membership.Role.OWNER,
                Membership.Role.ADMIN,
            ],
        ).exists()


class IsOrganizationAdminForOrganization(BasePermission):
    """
    Allows OWNER or ADMIN of the organization.
    """

    def has_permission(self, request, view):
        organization_id = view.kwargs.get("organization_id")

        return Membership.objects.filter(
            user=request.user,
            organization_id=organization_id,
            role__in=[
                Membership.Role.OWNER,
                Membership.Role.ADMIN,
            ],
        ).exists()
