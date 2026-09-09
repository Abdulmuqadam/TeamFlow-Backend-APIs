from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied

from .models import Organization, Membership
from .permissions import IsOrganizationAdmin, IsOrganizationMember
from .serializers import (
    OrganizationSerializer,
    MembershipSerializer,
    AddMemberSerializer,
    UpdateMembershipSerializer,
)


class OrganizationListCreateView(generics.ListCreateAPIView):
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Organization.objects.filter(members=self.request.user)

    def perform_create(self, serializer):
        organization = serializer.save()

        organization.members.add(
            self.request.user,
            through_defaults={"role": "OWNER"},
        )


class OrganizationMemberListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get_queryset(self):
        organization_id = self.kwargs["organization_id"]

        return Membership.objects.filter(
            organization_id=organization_id
        ).select_related("user")

    def get_permissions(self):
        if self.request.method == "POST":
            return [
                IsAuthenticated(),
                IsOrganizationAdmin(),
            ]

        return [
            IsAuthenticated(),
            IsOrganizationMember(),
        ]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        organization_id = self.kwargs["organization_id"]

        organization = Organization.objects.get(id=organization_id)

        user = serializer.validated_data["user"]
        role = serializer.validated_data["role"]

        membership, created = Membership.objects.get_or_create(
            organization=organization,
            user=user,
            defaults={"role": role},
        )

        if not created:
            return Response(
                {"detail": "User is already a member of this organization."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            MembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AddMemberSerializer

        return MembershipSerializer


class OrganizationMemberDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [
        IsAuthenticated,
        IsOrganizationMember,
    ]

    lookup_url_kwarg = "membership_id"

    def get_queryset(self):
        return Membership.objects.filter(
            organization_id=self.kwargs["organization_id"]
        ).select_related("user")

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return UpdateMembershipSerializer

        return MembershipSerializer

    def get_current_membership(self):
        return get_object_or_404(
            Membership,
            organization_id=self.kwargs["organization_id"],
            user=self.request.user,
        )

    def perform_update(self, serializer):
        current_membership = self.get_current_membership()
        target_membership = self.get_object()

        if current_membership.role == Membership.Role.MEMBER:
            raise PermissionDenied("Members cannot change roles.")

        if target_membership.role == Membership.Role.OWNER:
            raise PermissionDenied("The organization owner cannot be modified.")

        serializer.save()

    def perform_destroy(self, instance):
        current_membership = self.get_current_membership()

        if current_membership.role == Membership.Role.MEMBER:
            raise PermissionDenied("Members cannot remove organization members.")

        if instance.role == Membership.Role.OWNER:
            raise PermissionDenied("The organization owner cannot be removed.")

        if instance.user == self.request.user:
            raise PermissionDenied("You cannot remove yourself from the organization.")

        instance.delete()
