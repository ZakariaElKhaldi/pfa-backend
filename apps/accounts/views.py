from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CustomUser
from .permissions import IsAdmin
from .serializers import UserSerializer


@method_decorator(ratelimit(key="ip", rate="20/m", method="POST", block=True), name="post")
class GitHubLogin(SocialLoginView):
    adapter_class = GitHubOAuth2Adapter
    client_class = OAuth2Client


@method_decorator(ratelimit(key="ip", rate="20/m", method="POST", block=True), name="post")
class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client


class AdminUserListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = CustomUser.objects.all().order_by("date_joined")
    pagination_class = None


class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = CustomUser.objects.all()


class AdminStatsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        from django.utils import timezone
        from apps.signals.models import SignalSnapshot
        from apps.tickers.models import Ticker
        from apps.social.models import SocialPost

        return Response({
            "total_users": CustomUser.objects.count(),
            "total_tickers": Ticker.objects.count(),
            "signals_today": SignalSnapshot.objects.filter(
                created_at__date=timezone.now().date()
            ).count(),
            "total_posts": SocialPost.objects.count(),
        })
