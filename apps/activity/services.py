from .models import Activity


def record_task_activity(
    *,
    task: object,
    actor: object,
    action: str,
    message: str,
    metadata: dict | None = None,
):
    return Activity.objects.create(
        organization=task.project.organization,
        project=task.project,
        task=task,
        actor=actor,
        action=action,
        message=message,
        metadata=metadata or {},
    )
