"""The member's actual banking data.

Blossom is the platform a credit union runs its members on, so a member has
accounts and those accounts have transactions. Before this existed the app showed
an account pill with a hardcoded name and a made-up last-four, which is fine for a
screenshot and misleading for anything else — the balance never moved, the number
belonged to nobody, and no API served it.

These are real rows. They are seeded when a member signs up rather than typed into
the interface, so every screen reads them the way it would read production data,
and the SSO hand-off carries a member who demonstrably has something to hand over.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models


class Account(models.Model):
    """One deposit or credit account belonging to a member."""

    class Kind(models.TextChoices):
        CHECKING = "checking", "Checking"
        SAVINGS = "savings", "Savings"
        CREDIT = "credit", "Credit card"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="accounts"
    )
    name = models.CharField(max_length=80)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.CHECKING)

    # Only the last four. A mock platform has no business holding a full account
    # number, and every screen that shows one shows these four digits anyway.
    number_last4 = models.CharField(max_length=4)

    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    available_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0")
    )
    currency = models.CharField(max_length=3, default="USD")

    # The account the topbar opens on, and the one Investments would fund from.
    is_primary = models.BooleanField(default=False)
    opened_at = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_primary", "name"]
        constraints = [
            # One primary per member, enforced here rather than in whichever view
            # happens to write next.
            models.UniqueConstraint(
                fields=["member"],
                condition=models.Q(is_primary=True),
                name="one_primary_account_per_member",
            )
        ]

    def __str__(self):
        return f"{self.name} ••{self.number_last4} ({self.member_id})"

    @property
    def display_number(self):
        return f"···· {self.number_last4}"


class Transaction(models.Model):
    """A posted movement on an account.

    ``amount`` is signed: negative is money leaving. Storing a sign rather than a
    separate debit/credit flag means a balance is a sum, and no screen can get the
    direction wrong by reading the wrong column.
    """

    class Category(models.TextChoices):
        GROCERIES = "groceries", "Groceries"
        DINING = "dining", "Dining"
        TRANSPORT = "transport", "Transport"
        BILLS = "bills", "Bills & utilities"
        SHOPPING = "shopping", "Shopping"
        INCOME = "income", "Income"
        TRANSFER = "transfer", "Transfer"
        FEES = "fees", "Fees"

    class Status(models.TextChoices):
        POSTED = "posted", "Posted"
        PENDING = "pending", "Pending"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="transactions"
    )
    description = models.CharField(max_length=120)
    category = models.CharField(
        max_length=16, choices=Category.choices, default=Category.SHOPPING
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.POSTED
    )
    posted_at = models.DateTimeField()

    class Meta:
        ordering = ["-posted_at"]
        indexes = [models.Index(fields=["account", "-posted_at"])]

    def __str__(self):
        return f"{self.description} {self.amount}"
