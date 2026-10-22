from django.test import TestCase

from apps.organizations.models import Membership, Organization
from apps.projects.models import Project, Task
from apps.users.models import User

from .models import Activity
from .notification_models import Notification
from .notification_services import (
    notify_task_assigned,
    notify_task_status_changed,
)
from .services import record_task_activity


class ActivityServiceTests(TestCase):
    def setUp(self):
        self.actor = User.objects.create_user(
            "actor@example.com",
            "Actor",
            "password123",
        )
        self.recipient = User.objects.create_user(
            "recipient@example.com",
            "Recipient",
            "password123",
        )
        self.organization = Organization.objects.create(name="Acme Team")
        Membership.objects.create(
            organization=self.organization,
            user=self.actor,
            role=Membership.Role.OWNER,
        )
        Membership.objects.create(
            organization=self.organization,
            user=self.recipient,
        )
        self.project = Project.objects.create(
            organization=self.organization,
            name="Website refresh",
            created_by=self.actor,
        )
        self.task = Task.objects.create(
            project=self.project,
            title="Review copy",
            created_by=self.actor,
        )

    def test_record_task_activity_populates_related_tenant_data(self):
        activity = record_task_activity(
            task=self.task,
            actor=self.actor,
            action=Activity.Action.TASK_CREATED,
            message="Created task",
            metadata={"source": "api"},
        )

        self.assertEqual(activity.organization, self.organization)
        self.assertEqual(activity.project, self.project)
        self.assertEqual(activity.task, self.task)
        self.assertEqual(activity.actor, self.actor)
        self.assertEqual(activity.metadata, {"source": "api"})

    def test_assignment_notification_skips_actor_and_notifies_recipient(self):
        self.assertIsNone(
            notify_task_assigned(
                task=self.task,
                recipient=self.actor,
                actor=self.actor,
            )
        )
        notification = notify_task_assigned(
            task=self.task,
            recipient=self.recipient,
            actor=self.actor,
        )

        self.assertIsNotNone(notification)
        self.assertEqual(notification.recipient, self.recipient)
        self.assertEqual(
            notification.notification_type,
            Notification.NotificationType.TASK_ASSIGNED,
        )
        self.assertFalse(notification.is_read)

    def test_status_notification_contains_old_and_new_status(self):
        notification = notify_task_status_changed(
            task=self.task,
            recipient=self.recipient,
            actor=self.actor,
            old_status=Task.Status.TODO,
            new_status=Task.Status.DONE,
        )

        self.assertEqual(
            notification.message,
            'Task "Review copy" changed from TODO to DONE.',
        )
        self.assertEqual(
            notification.notification_type,
            Notification.NotificationType.TASK_STATUS_CHANGED,
        )
