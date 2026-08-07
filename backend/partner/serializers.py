from django.contrib.auth import authenticate
from rest_framework import serializers

from partner.models import PartnerUser


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = PartnerUser
        fields = ("email", "password", "first_name", "last_name")

    def create(self, validated_data):
        return PartnerUser.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs["email"], password=attrs["password"])
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("This account is disabled.")
        attrs["user"] = user
        return attrs


class PartnerUserSerializer(serializers.ModelSerializer):
    external_user_id = serializers.CharField(read_only=True)
    picture = serializers.CharField(read_only=True)

    class Meta:
        model = PartnerUser
        fields = (
            "id",
            "external_user_id",
            "email",
            "first_name",
            "last_name",
            "picture",
            "created_at",
            # Drives whether the app offers the provider console at all. The
            # console enforces this itself; this only spares a member a nav item
            # that would answer 403.
            "is_staff",
        )
        read_only_fields = ("is_staff",)
