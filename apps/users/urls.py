from django.urls import path
from .views import RegisterUserView, UserDetailView

urlpatterns = [
    path('register/', RegisterUserView.as_view(), name='register'),
    path('me/', UserDetailView.as_view(), name='user-detail'),
]