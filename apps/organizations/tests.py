from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User

from .models import Membership, Organization


class OrganizationModelTests(APITestCase):
    def test_duplicate_names_receive_unique_slugs(self):
        first = Organization.objects.create(name="Acme Team")
        second = Organization.objects.create(name="Acme Team")

        self.assertEqual(first.slug, "acme-team")
        self.assertEqual(second.slug, "acme-team-1")

    def test_saving_existing_organization_preserves_slug(self):
        organization = Organization.objects.create(name="Acme Team")
        original_slug = organization.slug
        organization.name = "Renamed Team"
        organization.save()

        self.assertEqual(organization.slug, original_slug)


class OrganizationApiTests(APITestCase):
    organizations_url = reverse("organization-list-create")

    def setUp(self):
        self.owner = User.objects.create_user(
            "owner@example.com", "Owner", "password123"
        )
        self.admin = User.objects.create_user(
            "admin@example.com", "Admin", "password123"
        )
        self.member = User.objects.create_user(
            "member@example.com", "Member", "password123"
        )
        self.outsider = User.objects.create_user(
            "outsider@example.com", "Outsider", "password123"
        )

    def create_organization(self, name="Acme Team", user=None):
        self.client.force_authenticate(user=user or self.owner)
        response = self.client.post(
            self.organizations_url, {"name": name}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return Organization.objects.get(pk=response.data["id"])

    def add_membership(self, organization, user, role=Membership.Role.MEMBER):
        return Membership.objects.create(
            organization=organization, user=user, role=role
        )

    def members_url(self, organization):
        return reverse(
            "organization-members", kwargs={"organization_id": organization.pk}
        )

    def member_url(self, organization, membership):
        return reverse(
            "organization-member-detail",
            kwargs={
                "organization_id": organization.pk,
                "membership_id": membership.pk,
            },
        )

    def test_unauthenticated_users_cannot_list_or_create_organizations(self):
        list_response = self.client.get(self.organizations_url)
        create_response = self.client.post(
            self.organizations_url, {"name": "Acme Team"}, format="json"
        )

        self.assertEqual(list_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(create_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_organization_assigns_creator_as_owner(self):
        organization = self.create_organization()

        membership = Membership.objects.get(organization=organization, user=self.owner)
        self.assertEqual(membership.role, Membership.Role.OWNER)

    def test_organization_list_is_limited_to_user_memberships(self):
        visible = self.create_organization("Visible Team")
        hidden = Organization.objects.create(name="Hidden Team")
        self.add_membership(hidden, self.outsider)
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.organizations_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data], [visible.pk])

    def test_member_can_list_members_but_non_member_cannot(self):
        organization = self.create_organization()
        membership = self.add_membership(organization, self.member)
        self.client.force_authenticate(user=self.member)

        member_response = self.client.get(self.members_url(organization))
        self.client.force_authenticate(user=self.outsider)
        outsider_response = self.client.get(self.members_url(organization))

        self.assertEqual(member_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(member_response.data), 2)
        self.assertEqual(outsider_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(
            any(item["id"] == membership.pk for item in member_response.data)
        )

    def test_owner_and_admin_can_add_existing_users(self):
        organization = self.create_organization()
        self.client.force_authenticate(user=self.owner)
        owner_response = self.client.post(
            self.members_url(organization),
            {"email": self.member.email, "role": Membership.Role.MEMBER},
            format="json",
        )
        admin_membership = self.add_membership(
            organization, self.admin, Membership.Role.ADMIN
        )
        self.client.force_authenticate(user=self.admin)
        admin_response = self.client.post(
            self.members_url(organization),
            {"email": self.outsider.email, "role": Membership.Role.ADMIN},
            format="json",
        )

        self.assertEqual(owner_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(admin_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(admin_membership.role, Membership.Role.ADMIN)

    def test_member_cannot_add_users_and_unknown_users_are_rejected(self):
        organization = self.create_organization()
        self.add_membership(organization, self.member)
        self.client.force_authenticate(user=self.member)

        forbidden_response = self.client.post(
            self.members_url(organization),
            {"email": self.outsider.email},
            format="json",
        )
        self.client.force_authenticate(user=self.owner)
        unknown_response = self.client.post(
            self.members_url(organization),
            {"email": "unknown@example.com"},
            format="json",
        )

        self.assertEqual(forbidden_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(unknown_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_membership_and_owner_role_are_rejected(self):
        organization = self.create_organization()
        self.add_membership(organization, self.member)

        duplicate_response = self.client.post(
            self.members_url(organization),
            {"email": self.member.email},
            format="json",
        )
        owner_response = self.client.post(
            self.members_url(organization),
            {"email": self.admin.email, "role": Membership.Role.OWNER},
            format="json",
        )

        self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(owner_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_member_cannot_access_membership_from_another_organization(self):
        first = self.create_organization("First Team")
        second = self.create_organization("Second Team")
        second_membership = self.add_membership(second, self.member)
        self.client.force_authenticate(user=self.member)

        response = self.client.get(self.member_url(first, second_membership))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_change_member_role_but_cannot_grant_ownership(self):
        organization = self.create_organization()
        self.add_membership(organization, self.admin, Membership.Role.ADMIN)
        target = self.add_membership(organization, self.member)
        self.client.force_authenticate(user=self.admin)

        update_response = self.client.patch(
            self.member_url(organization, target),
            {"role": Membership.Role.ADMIN},
            format="json",
        )
        owner_response = self.client.patch(
            self.member_url(organization, target),
            {"role": Membership.Role.OWNER},
            format="json",
        )

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(owner_response.status_code, status.HTTP_400_BAD_REQUEST)
        target.refresh_from_db()
        self.assertEqual(target.role, Membership.Role.ADMIN)

    def test_members_cannot_change_roles_or_remove_members(self):
        organization = self.create_organization()
        current = self.add_membership(organization, self.member)
        target = self.add_membership(organization, self.outsider)
        self.client.force_authenticate(user=self.member)

        update_response = self.client.patch(
            self.member_url(organization, target),
            {"role": Membership.Role.ADMIN},
            format="json",
        )
        delete_response = self.client.delete(self.member_url(organization, target))

        self.assertEqual(update_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(delete_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Membership.objects.filter(pk=current.pk).exists())
        self.assertTrue(Membership.objects.filter(pk=target.pk).exists())

    def test_owner_cannot_be_modified_or_removed(self):
        organization = self.create_organization()
        owner_membership = Membership.objects.get(
            organization=organization, user=self.owner
        )
        self.client.force_authenticate(user=self.owner)

        update_response = self.client.patch(
            self.member_url(organization, owner_membership),
            {"role": Membership.Role.ADMIN},
            format="json",
        )
        delete_response = self.client.delete(
            self.member_url(organization, owner_membership)
        )

        self.assertEqual(update_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(delete_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_put_is_not_supported_for_membership_updates(self):
        organization = self.create_organization()
        target = self.add_membership(organization, self.member)

        response = self.client.put(
            self.member_url(organization, target),
            {"role": Membership.Role.ADMIN},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_duplicate_memberships_are_rejected_at_model_level(self):
        organization = self.create_organization()
        self.add_membership(organization, self.member)

        with self.assertRaises(Exception):
            self.add_membership(organization, self.member)
