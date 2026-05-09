import asyncio
import websockets
import json

async def test_ws():
    uri = "ws://localhost:8000/ws/market/AAPL/"
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")
            # Wait for one message
            message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            print(f"Received: {message}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_ws())
