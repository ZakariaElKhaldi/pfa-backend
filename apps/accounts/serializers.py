from dj_rest_auth.registration.serializers import RegisterSerializer as BaseRegisterSerializer
from rest_framework import serializers

from .models import CustomUser, UserPreference


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["id", "email", "username", "role", "is_active", "date_joined"]
        read_only_fields = ["id", "is_active", "date_joined"]


class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = [
            "theme",
            "default_ticker",
            "alert_email",
            "alert_push",
            "digest_frequency",
        ]


class CrowdSignalRegisterSerializer(BaseRegisterSerializer):
    """
    Override dj-rest-auth registration to auto-generate username from email,
    since CustomUser requires a username but we don't expose it at signup.
    """

    username = None  # remove the field from the form

    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        email = data.get("email", "")
        # Use the local part of the email as username; keep it unique via UUID suffix if needed
        data["username"] = email.split("@")[0]
        return data

    def validate_email(self, email):
        """
        Ensure email is unique (case-insensitive) and provide a friendly
        validation error rather than raising an IntegrityError during save.
        """
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("A user with that email already exists.")
        return email

    def save(self, request):
        from django.utils.crypto import get_random_string
        user = super().save(request)
        if not user.username:
            user.username = user.email.split("@")[0]
            # Ensure uniqueness
            base = user.username
            while CustomUser.objects.filter(username=user.username).exclude(pk=user.pk).exists():
                user.username = f"{base}_{get_random_string(4)}"
            user.save(update_fields=["username"])
        return user
