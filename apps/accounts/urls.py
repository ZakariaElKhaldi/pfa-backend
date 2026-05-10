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

from .views import (
    APIKeyListCreateView,
    APIKeyRevokeView,
    AdminStatsView,
    AdminUserDetailView,
    AdminUserListView,
    GitHubLogin,
    GitHubOAuthRedirectView,
    GoogleLogin,
    GoogleOAuthRedirectView,
    UserPreferenceView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("user/", UserDetailsView.as_view(), name="auth-user"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("token/refresh/", get_refresh_view().as_view(), name="token-refresh"),
    path("registration/", include("dj_rest_auth.registration.urls")),
    path("github/", GitHubLogin.as_view(), name="github-login"),
    path("github/redirect/", GitHubOAuthRedirectView.as_view(), name="github-oauth-redirect"),
    path("google/", GoogleLogin.as_view(), name="google-login"),
    path("google/redirect/", GoogleOAuthRedirectView.as_view(), name="google-oauth-redirect"),
    # Password
    path("password/change/", PasswordChangeView.as_view(), name="password-change"),
    path("password/reset/", PasswordResetView.as_view(), name="password-reset"),
    path("password/reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    # Preferences
    path("preferences/", UserPreferenceView.as_view(), name="user-preferences"),
    path("api-keys/", APIKeyListCreateView.as_view(), name="api-key-list-create"),
    path("api-keys/<int:pk>/", APIKeyRevokeView.as_view(), name="api-key-revoke"),
    # Admin
    path("admin/users/", AdminUserListView.as_view(), name="admin-user-list"),
    path("admin/users/<int:pk>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("admin/stats/", AdminStatsView.as_view(), name="admin-stats"),
]
