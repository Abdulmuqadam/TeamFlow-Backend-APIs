from .notification_models import Notification


def notify_task_assigned(*, task, recipient, actor):
    # Don't notify a user about their own action.
    if recipient == actor:
        return None

    return Notification.objects.create(
        recipient=recipient,
        task=task,
        notification_type=(Notification.NotificationType.TASK_ASSIGNED),
        message=f'You were assigned to "{task.title}".',
    )


def notify_task_status_changed(
    *,
    task,
    recipient,
    actor,
    old_status,
    new_status,
):
    if recipient == actor:
        return None

    return Notification.objects.create(
        recipient=recipient,
        task=task,
        notification_type=(Notification.NotificationType.TASK_STATUS_CHANGED),
        message=(f'Task "{task.title}" changed from {old_status} to {new_status}.'),
    )
