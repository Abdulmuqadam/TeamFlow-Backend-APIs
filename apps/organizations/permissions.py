from rest_framework.permissions import BasePermission

from .models import Membership


class IsOrganizationAdmin(BasePermission):
    """
    Allows access only to organization OWNER or ADMIN.
    """

    def has_permission(self, request, view):
        organization_id = view.kwargs.get("organization_id")

        if not organization_id:
            return False

        return Membership.objects.filter(
            user=request.user,
            organization_id=organization_id,
            role__in=[
                Membership.Role.OWNER,
                Membership.Role.ADMIN,
            ],
        ).exists()


class IsOrganizationMember(BasePermission):
    """
    Allows access only to members of the organization.
    """

    def has_permission(self, request, view):
        organization_id = view.kwargs.get("organization_id")

        if not organization_id:
            return False

        return Membership.objects.filter(
            user=request.user,
            organization_id=organization_id,
        ).exists()
