import pytest
from channels.testing import WebsocketCommunicator

from config.asgi import application


def _communicator(path: str) -> WebsocketCommunicator:
    return WebsocketCommunicator(
        application,
        path,
        headers=[(b"origin", b"http://testserver")],
    )


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_signals_ws_rejects_anonymous():
    communicator = _communicator("/ws/signals/")
    connected, _ = await communicator.connect()
    assert not connected


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_signals_ws_accepts_valid_jwt(admin_client):
    auth_header = admin_client._credentials["HTTP_AUTHORIZATION"]
    token = auth_header.split(" ", 1)[1]
    communicator = _communicator(f"/ws/signals/?token={token}")
    connected, _ = await communicator.connect()
    assert connected
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_signals_ws_rejects_invalid_jwt():
    communicator = _communicator("/ws/signals/?token=invalid.token.value")
    connected, _ = await communicator.connect()
    assert not connected
