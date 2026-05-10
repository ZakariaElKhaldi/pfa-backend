import pytest

from apps.accounts.models import APIKey


@pytest.mark.django_db
def test_create_api_key_returns_raw_key_once(auth_client):
    resp = auth_client.post("/api/auth/api-keys/", {
        "name": "integration",
        "scopes": ["signals.read", "portfolio.read"],
    }, format="json")
    assert resp.status_code == 201
    body = resp.json()
    assert "key" in body
    assert len(body["key"]) == 64
    db_key = APIKey.objects.get(id=body["id"])
    assert db_key.key == body["key"]
    assert db_key.scopes == ["signals.read", "portfolio.read"]


@pytest.mark.django_db
def test_list_and_revoke_api_key(auth_client):
    create_resp = auth_client.post("/api/auth/api-keys/", {
        "name": "to-revoke",
        "scopes": ["signals.read"],
    }, format="json")
    assert create_resp.status_code == 201
    key_id = create_resp.json()["id"]

    list_resp = auth_client.get("/api/auth/api-keys/")
    assert list_resp.status_code == 200
    assert any(k["id"] == key_id for k in list_resp.json())

    del_resp = auth_client.delete(f"/api/auth/api-keys/{key_id}/")
    assert del_resp.status_code == 204
    assert APIKey.objects.get(id=key_id).is_active is False


@pytest.mark.django_db
def test_api_key_auth_with_scope_can_access_scoped_read_endpoint(user, ticker):
    key = APIKey.objects.create(
        user=user,
        key="a" * 64,
        name="signals-key",
        scopes=["signals.read"],
    )
    assert key.is_active

    from rest_framework.test import APIClient
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"ApiKey {key.key}")

    resp = client.get("/api/signals/recent/?limit=1")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_api_key_without_scope_gets_403(user):
    key = APIKey.objects.create(
        user=user,
        key="b" * 64,
        name="no-signal-scope",
        scopes=["portfolio.read"],
    )

    from rest_framework.test import APIClient
    client = APIClient()
    client.credentials(HTTP_X_API_KEY=key.key)

    resp = client.get("/api/signals/recent/?limit=1")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_api_key_cannot_manage_other_api_keys(user):
    key = APIKey.objects.create(
        user=user,
        key="c" * 64,
        name="self-key",
        scopes=["signals.read"],
    )

    from rest_framework.test import APIClient
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"ApiKey {key.key}")

    resp = client.get("/api/auth/api-keys/")
    assert resp.status_code == 403
