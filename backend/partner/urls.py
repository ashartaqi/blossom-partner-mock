from django.urls import path

from partner.views import IntegrationView, LoginView, MeView, SignupView

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("me/", MeView.as_view(), name="me"),
    path("integration/", IntegrationView.as_view(), name="integration"),
]
