from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from partner.views import IntegrationView, LoginView, MeView, SignupView

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("integration/", IntegrationView.as_view(), name="integration"),
]
