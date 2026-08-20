import asyncio
import json

import websockets


async def main():
    async with websockets.connect("ws://127.0.0.1:8000/ws") as ws:
        first = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
        print("first frame type:", first.get("type"), "| pools:", len(first.get("data", [])))
        # Grab one more frame (event/alert) if it arrives quickly, else report.
        try:
            second = json.loads(await asyncio.wait_for(ws.recv(), timeout=8))
            print("second frame type:", second.get("type"))
        except asyncio.TimeoutError:
            print("second frame: none within 8s (stream is idle but open)")


asyncio.run(main())
