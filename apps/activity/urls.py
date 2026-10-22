from django.urls import path

from .views import (
    NotificationListView,
    NotificationMarkAllReadView,
    NotificationMarkReadView,
    TaskActivityListView,
)

urlpatterns = [
    path(
        "tasks/<int:task_id>/activity/",
        TaskActivityListView.as_view(),
        name="task-activity",
    ),
    path(
        "notifications/",
        NotificationListView.as_view(),
        name="notification-list",
    ),
    path(
        "notifications/<int:pk>/read/",
        NotificationMarkReadView.as_view(),
        name="notification-mark-read",
    ),
    path(
        "notifications/read-all/",
        NotificationMarkAllReadView.as_view(),
        name="notification-mark-all-read",
    ),
]
