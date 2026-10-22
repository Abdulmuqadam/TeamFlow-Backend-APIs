from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.organizations.models import Membership
from apps.projects.models import Task

from .models import Activity
from .notification_models import Notification
from .serializers import ActivitySerializer, NotificationSerializer


class TaskActivityListView(generics.ListAPIView):
    serializer_class = ActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        task = get_object_or_404(
            Task.objects.select_related(
                "project",
                "project__organization",
            ),
            id=self.kwargs["task_id"],
        )

        is_member = Membership.objects.filter(
            user=self.request.user,
            organization=task.project.organization,
        ).exists()

        if not is_member:
            raise PermissionDenied("You are not a member of this organization.")

        return Activity.objects.filter(task=task).select_related("actor")


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user,
        ).select_related("task")


class NotificationMarkReadView(generics.UpdateAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["patch"]

    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user,
        )

    def patch(self, request, *args, **kwargs):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=["is_read"])

        return Response(
            NotificationSerializer(notification).data,
            status=status.HTTP_200_OK,
        )


class NotificationMarkAllReadView(generics.GenericAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        updated_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).update(is_read=True)

        return Response(
            {
                "detail": "Notifications marked as read.",
                "updated_count": updated_count,
            }
        )
