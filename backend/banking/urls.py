from django.urls import path

from banking.views import AccountList, AccountTransactions, Summary

urlpatterns = [
    path("summary/", Summary.as_view(), name="banking-summary"),
    path("accounts/", AccountList.as_view(), name="banking-accounts"),
    path(
        "accounts/<uuid:account_id>/transactions/",
        AccountTransactions.as_view(),
        name="banking-account-transactions",
    ),
]
