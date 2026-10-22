from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Membership, Organization

User = get_user_model()


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization

        fields = (
            "id",
            "name",
            "slug",
            "created_at",
        )

        read_only_fields = (
            "id",
            "slug",
            "created_at",
        )


class MembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(
        source="user.email",
        read_only=True,
    )

    class Meta:
        model = Membership

        fields = (
            "id",
            "user",
            "user_email",
            "role",
            "joined_at",
        )

        read_only_fields = (
            "id",
            "joined_at",
        )


class AddMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=[
            Membership.Role.ADMIN,
            Membership.Role.MEMBER,
        ],
        default=Membership.Role.MEMBER,
    )

    def validate(self, attrs):
        try:
            user = User.objects.get(email=attrs["email"])
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {"email": "No user exists with this email."}
            )

        attrs["user"] = user
        return attrs


class UpdateMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = ("role",)

    def validate_role(self, value):
        if value == Membership.Role.OWNER:
            raise serializers.ValidationError(
                "Ownership cannot be assigned through this endpoint."
            )

        return value
