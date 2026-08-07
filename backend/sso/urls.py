from django.urls import path

from sso.views import SSOExchangeView, SSOInitiateView

urlpatterns = [
    path("initiate/", SSOInitiateView.as_view(), name="sso-initiate"),
    path("exchange/", SSOExchangeView.as_view(), name="sso-exchange"),
]
