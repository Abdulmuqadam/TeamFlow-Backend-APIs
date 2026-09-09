from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Organization, Membership
from .permissions import IsOrganizationAdmin, IsOrganizationMember
from .serializers import (
    OrganizationSerializer,
    MembershipSerializer,
    AddMemberSerializer,
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
