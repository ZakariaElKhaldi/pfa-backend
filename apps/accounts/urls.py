from django.urls import include, path
from dj_rest_auth.jwt_auth import get_refresh_view
from dj_rest_auth.views import (
    LoginView,
    LogoutView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetView,
    UserDetailsView,
)

from .views import AdminStatsView, AdminUserDetailView, AdminUserListView, GitHubLogin, GoogleLogin

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("user/", UserDetailsView.as_view(), name="auth-user"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("token/refresh/", get_refresh_view().as_view(), name="token-refresh"),
    path("registration/", include("dj_rest_auth.registration.urls")),
    path("github/", GitHubLogin.as_view(), name="github-login"),
    path("google/", GoogleLogin.as_view(), name="google-login"),
    # Password
    path("password/change/", PasswordChangeView.as_view(), name="password-change"),
    path("password/reset/", PasswordResetView.as_view(), name="password-reset"),
    path("password/reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    # Admin
    path("admin/users/", AdminUserListView.as_view(), name="admin-user-list"),
    path("admin/users/<int:pk>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("admin/stats/", AdminStatsView.as_view(), name="admin-stats"),
]
