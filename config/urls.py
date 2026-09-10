from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

url_path = "api/v1"

urlpatterns = [
    path("admin/", admin.site.urls),
    # OpenAPI schema
    path(f"{url_path}/schema/", SpectacularAPIView.as_view(), name="schema"),
    # Swagger UI
    path(f"{url_path}/docs/", SpectacularSwaggerView.as_view(), name="swagger-ui"),
    # Redoc UI
    path(f"{url_path}/redoc/", SpectacularRedocView.as_view(), name="redoc"),
    # Authentication
    path(f"{url_path}/auth/", include("apps.users.urls")),
    # JWT
    path(
        f"{url_path}/auth/login/",
        TokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),
    path(
        f"{url_path}/auth/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),
    # Orginizations
    path(f"{url_path}/organizations/", include("apps.organizations.urls")),
    # Projects
    path(f"{url_path}/", include("apps.projects.urls")),
]
