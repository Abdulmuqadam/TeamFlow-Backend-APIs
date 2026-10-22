from datetime import date

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.activity.models import Activity
from apps.activity.notification_models import Notification
from apps.organizations.models import Membership, Organization
from apps.users.models import User

from .models import Project, Task


class ProjectApiTests(APITestCase):
    def setUp(self):
        self.owner = self.create_user("owner@example.com", "Owner")
        self.admin = self.create_user("admin@example.com", "Admin")
        self.member = self.create_user("member@example.com", "Member")
        self.outsider = self.create_user("outsider@example.com", "Outsider")

        self.organization = Organization.objects.create(name="Acme Team")
        self.other_organization = Organization.objects.create(name="Other Team")
        self.add_membership(self.organization, self.owner, Membership.Role.OWNER)
        self.add_membership(self.organization, self.admin, Membership.Role.ADMIN)
        self.add_membership(self.organization, self.member)
        self.add_membership(
            self.other_organization, self.outsider, Membership.Role.OWNER
        )

        self.project = Project.objects.create(
            organization=self.organization,
            name="Website refresh",
            description="Refresh the public website",
            created_by=self.owner,
        )
        self.other_project = Project.objects.create(
            organization=self.other_organization,
            name="Private project",
            created_by=self.outsider,
        )

    def create_user(self, email, full_name):
        return User.objects.create_user(  # pyright: ignore[reportAttributeAccessIssue]
            email, full_name, "password123"
        )

    def add_membership(self, organization, user, role=Membership.Role.MEMBER):
        return Membership.objects.create(
            organization=organization,
            user=user,
            role=role,
        )

    def project_list_url(self, organization=None):
        organization = organization or self.organization
        return reverse(
            "organization-projects",
            kwargs={"organization_id": organization.pk},
        )

    def project_url(self, project=None):
        project = project or self.project
        return reverse("project-detail", kwargs={"project_id": project.pk})

    def task_list_url(self, project=None):
        project = project or self.project
        return reverse("project-tasks", kwargs={"project_id": project.pk})

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_unauthenticated_users_cannot_access_project_or_task_endpoints(self):
        endpoints = (
            ("get", self.project_list_url()),
            ("post", self.project_list_url()),
            ("get", self.project_url()),
            ("patch", self.project_url()),
            ("delete", self.project_url()),
            ("get", self.task_list_url()),
            ("post", self.task_list_url()),
        )

        for method, url in endpoints:
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url, {}, format="json")
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_project_list_is_scoped_to_the_requested_organization(self):
        self.authenticate(self.member)

        response = self.client.get(self.project_list_url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in response.data], [self.project.pk])

    def test_non_member_cannot_list_an_organizations_projects(self):
        self.authenticate(self.outsider)

        response = self.client.get(self.project_list_url())

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_and_admin_can_create_projects_with_server_owned_fields(self):
        for user in (self.owner, self.admin):
            with self.subTest(user=user):
                self.authenticate(user)
                response = self.client.post(
                    self.project_list_url(),
                    {
                        "organization": self.other_organization.pk,
                        "name": "New project",
                        "description": "Project description",
                        "status": Project.Status.ARCHIVED,
                        "created_by": self.outsider.pk,
                    },
                    format="json",
                )

                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                created = Project.objects.get(pk=response.data["id"])
                self.assertEqual(created.organization, self.organization)
                self.assertEqual(created.created_by, user)

    def test_member_cannot_create_a_project(self):
        self.authenticate(self.member)

        response = self.client.post(
            self.project_list_url(), {"name": "Forbidden project"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_project_detail_allows_members_to_retrieve_but_not_manage(self):
        self.authenticate(self.member)

        retrieve_response = self.client.get(self.project_url())
        update_response = self.client.patch(
            self.project_url(), {"name": "Updated name"}, format="json"
        )
        delete_response = self.client.delete(self.project_url())

        self.assertEqual(retrieve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(delete_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_project_admin_can_update_and_delete_a_project(self):
        self.authenticate(self.admin)

        update_response = self.client.patch(
            self.project_url(), {"name": "Updated name"}, format="json"
        )
        delete_response = self.client.delete(self.project_url())

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Project.objects.filter(pk=self.project.pk).exists())

    def test_member_cannot_access_a_project_in_another_organization(self):
        self.authenticate(self.member)

        response = self.client.get(self.project_url(self.other_project))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_project_serializer_returns_created_by_email_and_defaults(self):
        self.authenticate(self.owner)
        response = self.client.post(
            self.project_list_url(), {"name": "Defaults project"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Project.Status.ACTIVE)
        self.assertEqual(response.data["created_by_email"], self.owner.email)
        self.assertEqual(response.data["organization"], self.organization.pk)
        self.assertEqual(response.data["created_by"], self.owner.pk)

    def test_project_name_is_required(self):
        self.authenticate(self.admin)

        response = self.client.post(self.project_list_url(), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)


class TaskApiTests(APITestCase):
    def setUp(self):
        self.owner = self.create_user("owner@example.com", "Owner")
        self.admin = self.create_user("admin@example.com", "Admin")
        self.assignee = self.create_user("assignee@example.com", "Assignee")
        self.member = self.create_user("member@example.com", "Member")
        self.outsider = self.create_user("outsider@example.com", "Outsider")

        self.organization = Organization.objects.create(name="Acme Team")
        self.other_organization = Organization.objects.create(name="Other Team")
        self.add_membership(self.organization, self.owner, Membership.Role.OWNER)
        self.add_membership(self.organization, self.admin, Membership.Role.ADMIN)
        self.add_membership(self.organization, self.assignee)
        self.add_membership(self.organization, self.member)
        self.add_membership(
            self.other_organization, self.outsider, Membership.Role.OWNER
        )

        self.project = Project.objects.create(
            organization=self.organization,
            name="Website refresh",
            created_by=self.owner,
        )
        self.other_project = Project.objects.create(
            organization=self.other_organization,
            name="Private project",
            created_by=self.outsider,
        )
        self.task = Task.objects.create(
            project=self.project,
            title="Review copy",
            description="Review the landing page copy",
            assigned_to=self.assignee,
            created_by=self.owner,
            due_date=date(2026, 10, 1),
        )
        self.other_task = Task.objects.create(
            project=self.other_project,
            title="Private task",
            created_by=self.outsider,
        )

    def create_user(self, email, full_name):
        return User.objects.create_user(email, full_name, "password123")

    def add_membership(self, organization, user, role=Membership.Role.MEMBER):
        return Membership.objects.create(
            organization=organization,
            user=user,
            role=role,
        )

    def task_list_url(self, project=None):
        project = project or self.project
        return reverse("project-tasks", kwargs={"project_id": project.pk})

    def task_url(self, task=None):
        task = task or self.task
        return reverse("task-detail", kwargs={"task_id": task.pk})

    def activity_url(self, task=None):
        task = task or self.task
        return reverse("task-activity", kwargs={"task_id": task.pk})

    def stats_url(self, project=None):
        project = project or self.project
        return reverse("project-stats", kwargs={"project_id": project.pk})

    def notification_list_url(self):
        return reverse("notification-list")

    def notification_read_url(self, notification):
        return reverse("notification-mark-read", kwargs={"pk": notification.pk})

    def notification_read_all_url(self):
        return reverse("notification-mark-all-read")

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_member_can_list_only_tasks_from_a_project_in_their_organization(self):
        self.authenticate(self.member)

        response = self.client.get(self.task_list_url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(
            [item["id"] for item in response.data["results"]], [self.task.pk]
        )

    def test_non_member_cannot_list_tasks_from_another_organization(self):
        self.authenticate(self.member)

        response = self.client.get(self.task_list_url(self.other_project))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_only_organization_admins_can_create_tasks(self):
        self.authenticate(self.member)
        member_response = self.client.post(
            self.task_list_url(), {"title": "Member task"}, format="json"
        )

        self.authenticate(self.admin)
        admin_response = self.client.post(
            self.task_list_url(),
            {
                "project": self.other_project.pk,
                "title": "Admin task",
                "assigned_to": self.assignee.pk,
                "priority": Task.Priority.HIGH,
            },
            format="json",
        )

        self.assertEqual(member_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(admin_response.status_code, status.HTTP_201_CREATED)
        created = Task.objects.get(pk=admin_response.data["id"])
        self.assertEqual(created.project, self.project)
        self.assertEqual(created.created_by, self.admin)

    def test_task_creation_uses_defaults_and_returns_assignment_metadata(self):
        self.authenticate(self.admin)

        response = self.client.post(
            self.task_list_url(),
            {"title": "Plan release", "assigned_to": self.assignee.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Task.Status.TODO)
        self.assertEqual(response.data["priority"], Task.Priority.MEDIUM)
        self.assertEqual(response.data["assigned_to_email"], self.assignee.email)
        self.assertEqual(response.data["created_by_email"], self.admin.email)

    def test_task_creation_records_activity(self):
        self.authenticate(self.admin)

        response = self.client.post(
            self.task_list_url(),
            {"title": "Document release"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        activity = Activity.objects.get(task_id=response.data["id"])
        self.assertEqual(activity.action, Activity.Action.TASK_CREATED)
        self.assertEqual(activity.actor, self.admin)
        self.assertEqual(activity.message, 'Created task "Document release"')

    def test_task_list_supports_filters_search_and_ordering(self):
        second_task = Task.objects.create(
            project=self.project,
            title="Publish launch notes",
            description="Prepare release notes",
            status=Task.Status.DONE,
            priority=Task.Priority.HIGH,
            created_by=self.owner,
        )
        Task.objects.create(
            project=self.project,
            title="Unrelated work",
            status=Task.Status.IN_PROGRESS,
            priority=Task.Priority.LOW,
            created_by=self.owner,
        )
        self.authenticate(self.member)

        response = self.client.get(
            self.task_list_url(),
            {
                "status": Task.Status.DONE,
                "priority": Task.Priority.HIGH,
                "search": "launch",
                "ordering": "due_date",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in response.data["results"]], [second_task.pk]
        )

    def test_task_cannot_be_assigned_to_user_outside_organization(self):
        self.authenticate(self.admin)

        response = self.client.post(
            self.task_list_url(),
            {
                "title": "Cross tenant assignment",
                "assigned_to": self.outsider.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("assigned_to", response.data)

    def test_project_stats_are_scoped_and_count_each_task_status(self):
        Task.objects.create(
            project=self.project,
            title="In progress task",
            status=Task.Status.IN_PROGRESS,
            created_by=self.owner,
        )
        Task.objects.create(
            project=self.project,
            title="Done task",
            status=Task.Status.DONE,
            created_by=self.owner,
        )
        self.authenticate(self.member)

        response = self.client.get(self.stats_url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "project_id": self.project.pk,
                "project_name": self.project.name,
                "total_tasks": 3,
                "todo": 1,
                "in_progress": 1,
                "done": 1,
            },
        )

    def test_non_member_cannot_view_project_stats(self):
        self.authenticate(self.outsider)

        response = self.client.get(self.stats_url())

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_task_activity_is_visible_to_organization_members_only(self):
        activity = Activity.objects.create(
            organization=self.organization,
            project=self.project,
            task=self.task,
            actor=self.owner,
            action=Activity.Action.TASK_CREATED,
            message="Created task",
        )
        self.authenticate(self.member)

        member_response = self.client.get(self.activity_url())

        self.authenticate(self.outsider)
        outsider_response = self.client.get(self.activity_url())

        self.assertEqual(member_response.status_code, status.HTTP_200_OK)
        self.assertEqual(member_response.data[0]["id"], activity.pk)
        self.assertEqual(member_response.data[0]["actor_email"], self.owner.email)
        self.assertEqual(outsider_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_task_status_update_records_activity_and_notifies_assignee(self):
        self.authenticate(self.admin)

        response = self.client.patch(
            self.task_url(),
            {"status": Task.Status.IN_PROGRESS},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        activity = Activity.objects.get(
            task=self.task,
            action=Activity.Action.STATUS_CHANGED,
        )
        self.assertEqual(
            activity.metadata,
            {
                "old_status": Task.Status.TODO,
                "new_status": Task.Status.IN_PROGRESS,
            },
        )
        notification = Notification.objects.get(recipient=self.assignee)
        self.assertEqual(
            notification.notification_type,
            Notification.NotificationType.TASK_STATUS_CHANGED,
        )
        self.assertFalse(notification.is_read)

    def test_task_assignment_creates_assignment_notification_and_activity(self):
        self.authenticate(self.admin)

        response = self.client.patch(
            self.task_url(),
            {"assigned_to": self.member.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification = Notification.objects.get(recipient=self.member)
        self.assertEqual(
            notification.notification_type,
            Notification.NotificationType.TASK_ASSIGNED,
        )
        activity = Activity.objects.get(
            task=self.task,
            action=Activity.Action.TASK_ASSIGNED,
        )
        self.assertEqual(
            activity.metadata["new_assignee_id"],
            self.member.pk,
        )

    def test_editing_task_without_status_change_does_not_send_status_notification(self):
        self.authenticate(self.admin)

        response = self.client.patch(
            self.task_url(),
            {"title": "Updated title"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            Notification.objects.filter(
                recipient=self.assignee,
                notification_type=Notification.NotificationType.TASK_STATUS_CHANGED,
            ).exists()
        )

    def test_notifications_are_private_and_can_be_marked_read(self):
        own_notification = Notification.objects.create(
            recipient=self.assignee,
            task=self.task,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
            message="Assigned to task",
        )
        Notification.objects.create(
            recipient=self.member,
            task=self.task,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
            message="Different recipient",
        )
        self.authenticate(self.assignee)

        list_response = self.client.get(self.notification_list_url())
        read_response = self.client.patch(
            self.notification_read_url(own_notification),
            {},
            format="json",
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(list_response.data[0]["task_title"], self.task.title)
        self.assertEqual(read_response.status_code, status.HTTP_200_OK)
        own_notification.refresh_from_db()
        self.assertTrue(own_notification.is_read)

    def test_notification_read_endpoints_cannot_modify_another_users_notification(self):
        notification = Notification.objects.create(
            recipient=self.assignee,
            task=self.task,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
            message="Assigned to task",
        )
        self.authenticate(self.member)

        response = self.client.patch(
            self.notification_read_url(notification),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        notification.refresh_from_db()
        self.assertFalse(notification.is_read)

    def test_mark_all_notifications_read_returns_updated_count(self):
        Notification.objects.create(
            recipient=self.assignee,
            task=self.task,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
            message="Unread one",
        )
        Notification.objects.create(
            recipient=self.assignee,
            task=self.task,
            notification_type=Notification.NotificationType.TASK_STATUS_CHANGED,
            message="Unread two",
        )
        Notification.objects.create(
            recipient=self.member,
            task=self.task,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
            message="Other user",
        )
        self.authenticate(self.assignee)

        response = self.client.post(self.notification_read_all_url(), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["updated_count"], 2)
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.assignee,
                is_read=False,
            ).count(),
            0,
        )

    def test_task_detail_is_readable_by_members_and_protected_from_outsiders(self):
        self.authenticate(self.member)
        member_response = self.client.get(self.task_url())

        self.authenticate(self.outsider)
        outsider_response = self.client.get(self.task_url())

        self.assertEqual(member_response.status_code, status.HTTP_200_OK)
        self.assertEqual(outsider_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_assigned_member_can_update_their_task(self):
        self.authenticate(self.assignee)

        response = self.client.patch(
            self.task_url(), {"status": Task.Status.IN_PROGRESS}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.IN_PROGRESS)

    def test_member_cannot_update_a_task_assigned_to_someone_else(self):
        self.authenticate(self.member)

        response = self.client.patch(
            self.task_url(), {"title": "Unauthorized change"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_update_and_delete_any_task(self):
        self.authenticate(self.admin)

        update_response = self.client.patch(
            self.task_url(), {"priority": Task.Priority.HIGH}, format="json"
        )
        delete_response = self.client.delete(self.task_url())

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())

    def test_regular_member_cannot_delete_a_task(self):
        self.authenticate(self.assignee)

        response = self.client.delete(self.task_url())

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())

    def test_task_title_is_required(self):
        self.authenticate(self.admin)

        response = self.client.post(self.task_list_url(), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", response.data)


class ProjectAndTaskModelTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "creator@example.com", "Creator", "password123"
        )
        self.organization = Organization.objects.create(name="Acme Team")
        self.project = Project.objects.create(
            organization=self.organization,
            name="Website refresh",
            created_by=self.user,
        )

    def test_project_and_task_string_representations_use_their_names(self):
        task = Task.objects.create(
            project=self.project, title="Review copy", created_by=self.user
        )

        self.assertEqual(str(self.project), "Website refresh")
        self.assertEqual(str(task), "Review copy")
