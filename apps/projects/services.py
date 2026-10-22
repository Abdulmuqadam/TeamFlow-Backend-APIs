from django.db import transaction

from apps.activity.models import Activity
from apps.activity.services import record_task_activity
from apps.activity.notification_services import (
    notify_task_assigned,
    notify_task_status_changed,
)
from .models import Task


@transaction.atomic
def update_task_with_events(*, serializer, actor):
    """
    Update a task and save its activity records and notifications
    in the same database transaction.
    """
    task_id = serializer.instance.pk

    # Lock the database row while this update is processed.
    task = (
        Task.objects.select_for_update()
        .select_related("project__organization")
        .get(pk=task_id)
    )

    old_status = task.status
    old_assignee_id = task.assigned_to_id

    # Ensure the serializer updates the locked instance.
    serializer.instance = task
    updated_task = serializer.save()

    # Record an assignment change.
    if old_assignee_id != updated_task.assigned_to_id:
        if updated_task.assigned_to is not None:
            record_task_activity(
                task=updated_task,
                actor=actor,
                action=Activity.Action.TASK_ASSIGNED,
                message=(
                    f'{actor.email} assigned "{updated_task.title}" '
                    f"to {updated_task.assigned_to.email}."
                ),
                metadata={
                    "old_assignee_id": old_assignee_id,
                    "new_assignee_id": updated_task.assigned_to_id,
                },
            )

            notify_task_assigned(
                task=updated_task,
                recipient=updated_task.assigned_to,
                actor=actor,
            )

    # Record a status change.
    if old_status != updated_task.status:
        record_task_activity(
            task=updated_task,
            actor=actor,
            action=Activity.Action.STATUS_CHANGED,
            message=(
                f'"{updated_task.title}" changed from '
                f"{old_status} to {updated_task.status}."
            ),
            metadata={
                "old_status": old_status,
                "new_status": updated_task.status,
            },
        )

        if updated_task.assigned_to is not None and updated_task.assigned_to != actor:
            notify_task_status_changed(
                task=updated_task,
                recipient=updated_task.assigned_to,
                actor=actor,
                old_status=old_status,
                new_status=updated_task.status,
            )

    return updated_task
