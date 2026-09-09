from django.urls import path

from .views import OrganizationListCreateView, OrganizationMemberListView

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
]
