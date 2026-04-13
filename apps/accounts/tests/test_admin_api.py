import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import CustomUser


@pytest.mark.django_db
def test_register_creates_user(db):
    client = APIClient()
    resp = client.post("/api/auth/registration/", {
        "email": "new@example.com",
        "password1": "securepass123!",
        "password2": "securepass123!",
    })
    assert resp.status_code == 201
    assert CustomUser.objects.filter(email="new@example.com").exists()


@pytest.mark.django_db
def test_register_password_mismatch_returns_400(db):
    client = APIClient()
    resp = client.post("/api/auth/registration/", {
        "email": "bad@example.com",
        "password1": "pass1",
        "password2": "pass2",
    })
    assert resp.status_code == 400


@pytest.mark.django_db
def test_admin_stats_requires_admin(auth_client):
    resp = auth_client.get("/api/auth/admin/stats/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_admin_stats_returns_counts(admin_client, user, ticker):
    resp = admin_client.get("/api/auth/admin/stats/")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_users" in data
    assert "total_tickers" in data
    assert "signals_today" in data
    assert "total_posts" in data


@pytest.mark.django_db
def test_admin_user_list(admin_client, user):
    resp = admin_client.get("/api/auth/admin/users/")
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.json()]
    assert user.email in emails


@pytest.mark.django_db
def test_admin_user_update_role(admin_client, user):
    resp = admin_client.patch(f"/api/auth/admin/users/{user.id}/", {"role": "admin"})
    assert resp.status_code == 200
    user.refresh_from_db()
    assert user.role == "admin"


@pytest.mark.django_db
def test_admin_user_delete(admin_client, user):
    user_id = user.id
    resp = admin_client.delete(f"/api/auth/admin/users/{user_id}/")
    assert resp.status_code == 204
    assert not CustomUser.objects.filter(id=user_id).exists()
