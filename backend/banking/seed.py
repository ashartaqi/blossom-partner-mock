"""Give a new member a plausible banking history.

A member who signs up with nothing has no balance to show, no transactions to
list and nothing to fund an investment from — which makes every screen look
broken for reasons that have nothing to do with the code.

So signup opens real accounts and posts real transactions. The figures are
generated, and this file is the only place that is true: from here on every
screen, every endpoint and every total reads the database like any other
platform would. Balances are derived by summing the rows rather than assigned,
so the ledger and the balance cannot disagree.
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from banking.models import Account, Transaction

# Merchant, category, and the range a charge there plausibly falls in.
MERCHANTS = [
    ("Whole Foods Market", Transaction.Category.GROCERIES, 18, 140),
    ("Trader Joe's", Transaction.Category.GROCERIES, 22, 95),
    ("Blue Bottle Coffee", Transaction.Category.DINING, 5, 18),
    ("Chipotle", Transaction.Category.DINING, 11, 32),
    ("Thai Basil", Transaction.Category.DINING, 24, 78),
    ("Uber", Transaction.Category.TRANSPORT, 8, 46),
    ("Shell", Transaction.Category.TRANSPORT, 35, 82),
    ("Transit Authority", Transaction.Category.TRANSPORT, 2, 15),
    ("Pacific Gas & Electric", Transaction.Category.BILLS, 60, 190),
    ("Comcast", Transaction.Category.BILLS, 55, 110),
    ("Verizon Wireless", Transaction.Category.BILLS, 40, 95),
    ("Amazon", Transaction.Category.SHOPPING, 12, 220),
    ("Target", Transaction.Category.SHOPPING, 20, 160),
    ("Apple", Transaction.Category.SHOPPING, 15, 300),
]

PAYROLL = "Payroll — Direct Deposit"


def _money(low, high, rng):
    return Decimal(f"{rng.uniform(low, high):.2f}")


def open_accounts(member, rng=None):
    """Open a checking and a savings account and post a few months of history.

    Idempotent: a member who already has accounts is left alone, so a re-run —
    a backfill, a retried signup — cannot double their money.
    """
    if Account.objects.filter(member=member).exists():
        return list(Account.objects.filter(member=member))

    # Seeded from the member id so a given member's history is stable across
    # re-seeds, while different members still look different.
    rng = rng or random.Random(str(member.id))
    now = timezone.now()

    checking = Account.objects.create(
        member=member,
        name="Everyday Checking",
        kind=Account.Kind.CHECKING,
        number_last4=f"{rng.randint(0, 9999):04d}",
        is_primary=True,
        opened_at=(now - timedelta(days=rng.randint(400, 2200))).date(),
    )
    savings = Account.objects.create(
        member=member,
        name="Rainy Day Savings",
        kind=Account.Kind.SAVINGS,
        number_last4=f"{rng.randint(0, 9999):04d}",
        opened_at=(now - timedelta(days=rng.randint(200, 1500))).date(),
    )

    rows = []

    # Opening deposit, so the running balance never goes negative on day one.
    rows.append(
        Transaction(
            account=checking,
            description="Opening deposit",
            category=Transaction.Category.TRANSFER,
            amount=_money(1800, 3600, rng),
            posted_at=now - timedelta(days=95),
        )
    )

    # Salary on the 1st and 15th, which is what makes a checking balance behave
    # like a checking balance rather than a random walk downwards.
    salary = _money(2100, 3400, rng)
    for day_offset in range(90, 0, -15):
        rows.append(
            Transaction(
                account=checking,
                description=PAYROLL,
                category=Transaction.Category.INCOME,
                amount=salary,
                posted_at=now - timedelta(days=day_offset, hours=rng.randint(0, 6)),
            )
        )

    # Everyday spending.
    for day_offset in range(90, 0, -1):
        for _ in range(rng.randint(0, 3)):
            merchant, category, low, high = rng.choice(MERCHANTS)
            rows.append(
                Transaction(
                    account=checking,
                    description=merchant,
                    category=category,
                    amount=-_money(low, high, rng),
                    posted_at=now
                    - timedelta(days=day_offset, hours=rng.randint(0, 23)),
                )
            )

    # A standing transfer into savings.
    for day_offset in range(90, 0, -30):
        moved = _money(150, 500, rng)
        when = now - timedelta(days=day_offset, hours=2)
        rows.append(
            Transaction(
                account=checking,
                description="Transfer to Rainy Day Savings",
                category=Transaction.Category.TRANSFER,
                amount=-moved,
                posted_at=when,
            )
        )
        rows.append(
            Transaction(
                account=savings,
                description="Transfer from Everyday Checking",
                category=Transaction.Category.TRANSFER,
                amount=moved,
                posted_at=when,
            )
        )

    rows.append(
        Transaction(
            account=savings,
            description="Opening deposit",
            category=Transaction.Category.TRANSFER,
            amount=_money(900, 4200, rng),
            posted_at=now - timedelta(days=95),
        )
    )

    # The most recent day or two is still settling, as it would be on any real
    # statement.
    for row in rows:
        if (now - row.posted_at) < timedelta(days=2) and row.amount < 0:
            row.status = Transaction.Status.PENDING

    Transaction.objects.bulk_create(rows)

    for account in (checking, savings):
        recalculate(account)

    return [checking, savings]


def recalculate(account):
    """Set the balance from the ledger.

    Derived, never assigned. A balance that is stored independently of the rows
    that produced it is a balance that will eventually disagree with them.
    """
    totals = account.transactions.aggregate(
        posted=Sum("amount", filter=~Q(status=Transaction.Status.PENDING)),
        total=Sum("amount"),
    )
    account.balance = totals["posted"] or Decimal("0")
    # Pending debits are already spent as far as the member is concerned.
    account.available_balance = totals["total"] or Decimal("0")
    account.save(update_fields=["balance", "available_balance"])
