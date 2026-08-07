from rest_framework import serializers

from banking.models import Account, Transaction


class TransactionSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = Transaction
        fields = (
            "id",
            "description",
            "category",
            "category_label",
            "amount",
            "status",
            "posted_at",
        )


class AccountSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    display_number = serializers.CharField(read_only=True)

    class Meta:
        model = Account
        fields = (
            "id",
            "name",
            "kind",
            "kind_label",
            "number_last4",
            "display_number",
            "balance",
            "available_balance",
            "currency",
            "is_primary",
            "opened_at",
        )
