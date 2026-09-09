from django.urls import path

from .views import (
    OrganizationListCreateView,
    OrganizationMemberDetailView,
    OrganizationMemberListView,
)

urlpatterns = [
    path(
        "",
        OrganizationListCreateView.as_view(),
        name="organization-list-create",
    ),
    path(
        "<int:organization_id>/members/",
        OrganizationMemberListView.as_view(),
        name="organization-members",
    ),
    path(
        "<int:organization_id>/members/<int:membership_id>/",
        OrganizationMemberDetailView.as_view(),
        name="organization-member-detail",
    ),
]
