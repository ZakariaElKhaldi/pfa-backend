import pytest
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator

from config.asgi import application


def market_communicator(path: str) -> WebsocketCommunicator:
    return WebsocketCommunicator(
        application,
        path,
        headers=[(b"origin", b"http://testserver")],
    )


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_consumer_connects_and_receives_message():
    communicator = market_communicator("/ws/market/AAPL/")
    connected, _ = await communicator.connect()
    assert connected

    # Simulate a message pushed from the server side (e.g., by the pipeline)
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        "market_AAPL",
        {"type": "market.update", "data": {"type": "price", "price": "150.00"}},
    )

    response = await communicator.receive_json_from(timeout=2)
    assert response["type"] == "price"
    assert response["price"] == "150.00"

    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_consumer_disconnects_cleanly():
    communicator = market_communicator("/ws/market/TSLA/")
    connected, _ = await communicator.connect()
    assert connected
    await communicator.disconnect()
