from dj_rest_auth.jwt_auth import get_refresh_view
from dj_rest_auth.views import LogoutView, UserDetailsView
from django.urls import path

from allauth.socialaccount.views import signup as socialaccount_signup

from .views import GitHubLogin, GoogleLogin

urlpatterns = [
    path("user/", UserDetailsView.as_view(), name="auth-user"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("token/refresh/", get_refresh_view().as_view(), name="token-refresh"),
    path("github/", GitHubLogin.as_view(), name="github-login"),
    path("google/", GoogleLogin.as_view(), name="google-login"),
]
