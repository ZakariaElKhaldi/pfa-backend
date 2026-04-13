from decimal import Decimal

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class CrowdSignalAccountAdapter(DefaultAccountAdapter):
    """
    API-only backend — suppress all flash messages (no browser UI to receive them).
    Also works around a Python 3.14 + Django 4.2 Context.__copy__ crash when allauth
    tries to render message templates during the post-login flow.
    """

    def add_message(self, request, level, message_template=None,
                    message_context=None, extra_tags="", message=None):
        pass  # no-op: pure API backend has no flash message consumers


class CrowdSignalSocialAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        user.role = "user"
        user.save(update_fields=["role"])
        # Auto-create portfolio for new users
        from apps.portfolio.models import Portfolio

        Portfolio.objects.get_or_create(user=user, defaults={"cash": Decimal("100000.00")})
        return user
