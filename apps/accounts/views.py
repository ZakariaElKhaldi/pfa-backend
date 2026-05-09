from urllib.parse import urlencode

from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from django.conf import settings
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import generics
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CustomUser, UserPreference
from .permissions import IsAdmin
from .serializers import UserPreferenceSerializer, UserSerializer


@method_decorator(ratelimit(key="ip", rate="20/m", method="POST", block=True), name="post")
class GitHubLogin(SocialLoginView):
    adapter_class = GitHubOAuth2Adapter
    client_class = OAuth2Client

    @property
    def callback_url(self):
        return f"{settings.FRONTEND_URL}/auth/callback/github"


@method_decorator(ratelimit(key="ip", rate="20/m", method="POST", block=True), name="post")
class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client

    @property
    def callback_url(self):
        return f"{settings.FRONTEND_URL}/auth/callback/google"


class GoogleOAuthRedirectView(APIView):
    """GET — redirect browser to Google's OAuth consent page."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        client_id = settings.SOCIALACCOUNT_PROVIDERS["google"]["APP"]["client_id"]
        callback_url = f"{settings.FRONTEND_URL}/auth/callback/google"
        params = urlencode({
            "client_id": client_id,
            "redirect_uri": callback_url,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
        })
        return redirect(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")


class GitHubOAuthRedirectView(APIView):
    """GET — redirect browser to GitHub's OAuth consent page."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        client_id = settings.SOCIALACCOUNT_PROVIDERS["github"]["APP"]["client_id"]
        callback_url = f"{settings.FRONTEND_URL}/auth/callback/github"
        params = urlencode({
            "client_id": client_id,
            "redirect_uri": callback_url,
            "scope": "read:user user:email",
        })
        return redirect(f"https://github.com/login/oauth/authorize?{params}")


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


class UserPreferenceView(APIView):
    """GET / PATCH /api/auth/preferences/ — auto-creates row on first GET."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pref, _ = UserPreference.objects.get_or_create(user=request.user)
        return Response(UserPreferenceSerializer(pref).data)

    def patch(self, request):
        pref, _ = UserPreference.objects.get_or_create(user=request.user)
        serializer = UserPreferenceSerializer(pref, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        serializer.save()
        return Response(serializer.data)
