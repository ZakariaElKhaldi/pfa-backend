from decimal import Decimal

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class CrowdSignalSocialAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        user.role = "user"
        user.save(update_fields=["role"])
        # Auto-create portfolio for new users
        from apps.portfolio.models import Portfolio

        Portfolio.objects.get_or_create(user=user, defaults={"cash": Decimal("100000.00")})
        return user
