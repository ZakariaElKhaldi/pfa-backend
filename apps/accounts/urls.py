from django.urls import include, path
from dj_rest_auth.jwt_auth import get_refresh_view
from dj_rest_auth.views import LogoutView, UserDetailsView

from .views import AdminStatsView, AdminUserDetailView, AdminUserListView, GitHubLogin, GoogleLogin

urlpatterns = [
    path("user/", UserDetailsView.as_view(), name="auth-user"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("token/refresh/", get_refresh_view().as_view(), name="token-refresh"),
    path("registration/", include("dj_rest_auth.registration.urls")),
    path("github/", GitHubLogin.as_view(), name="github-login"),
    path("google/", GoogleLogin.as_view(), name="google-login"),
    # Admin
    path("admin/users/", AdminUserListView.as_view(), name="admin-user-list"),
    path("admin/users/<int:pk>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("admin/stats/", AdminStatsView.as_view(), name="admin-stats"),
]
