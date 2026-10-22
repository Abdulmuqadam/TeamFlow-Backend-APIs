from django.urls import path

from .views import TaskActivityListView

urlpatterns = [
    path(
        "tasks/<int:task_id>/activity/",
        TaskActivityListView.as_view(),
        name="task-activity",
    ),
]
