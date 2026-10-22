from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from apps.organizations.models import Membership
from apps.projects.models import Task

from .serializers import ActivitySerializer


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

        return task.activities.select_related("actor")
