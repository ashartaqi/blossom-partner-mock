"""Member-facing banking endpoints.

Every one of them is scoped to ``request.user``. There is no endpoint here that
takes a member id, because an endpoint that takes a member id is an endpoint that
eventually gets called with somebody else's.
"""

from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from banking.models import Account, Transaction
from banking.serializers import AccountSerializer, TransactionSerializer


def _accounts_for(user):
    return Account.objects.filter(member=user)


class AccountList(APIView):
    """The member's accounts, primary first."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        accounts = _accounts_for(request.user)
        return Response(AccountSerializer(accounts, many=True).data)


class AccountTransactions(APIView):
    """One account's history, newest first."""

    permission_classes = (IsAuthenticated,)
    LIMIT = 100

    def get(self, request, account_id):
        # Filtered by member as well as id, so a guessed id belonging to someone
        # else is a 404 rather than a disclosure.
        account = _accounts_for(request.user).filter(id=account_id).first()
        if not account:
            return Response(status=404)

        rows = account.transactions.all()[: self.LIMIT]
        return Response(
            {
                "account": AccountSerializer(account).data,
                "transactions": TransactionSerializer(rows, many=True).data,
            }
        )


class Summary(APIView):
    """Totals for the dashboard: what the member holds, and last month's flow."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        accounts = _accounts_for(request.user)
        since = timezone.now() - timedelta(days=30)

        recent = Transaction.objects.filter(account__member=request.user, posted_at__gte=since)
        money_in = recent.filter(amount__gt=0).aggregate(n=Sum("amount"))["n"] or 0
        money_out = recent.filter(amount__lt=0).aggregate(n=Sum("amount"))["n"] or 0

        return Response(
            {
                "total_balance": sum((a.balance for a in accounts), start=0),
                "accounts": AccountSerializer(accounts, many=True).data,
                "last_30_days": {
                    "money_in": money_in,
                    # Reported positive; the sign is in the label, not the number.
                    "money_out": abs(money_out),
                },
                "recent_transactions": TransactionSerializer(
                    Transaction.objects.filter(account__member=request.user)[:8],
                    many=True,
                ).data,
            }
        )
