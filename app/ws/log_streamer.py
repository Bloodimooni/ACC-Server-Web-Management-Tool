import asyncio

import aiofiles
from fastapi import WebSocket, WebSocketDisconnect

from app.auth.session import read_session
from app.config import settings


class LogBroadcaster:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._clients.discard(ws)

    async def broadcast(self, message: str) -> None:
        dead: set[WebSocket] = set()
        for client in self._clients:
            try:
                await client.send_text(message)
            except Exception:
                dead.add(client)
        self._clients -= dead


broadcaster = LogBroadcaster()


async def stream_logs(websocket: WebSocket) -> None:
    # Must accept before sending any response (including close frames).
    # Starlette converts close-before-accept into an HTTP 403.
    await websocket.accept()

    # Authenticate via session cookie (cookies are sent with the WS handshake)
    try:
        read_session(websocket)
    except Exception:
        await websocket.send_text("[Not authenticated — please log in and refresh]\n")
        await websocket.close(code=4401)
        return

    broadcaster._clients.add(websocket)

    # Replay the last 16 KB of the existing log file so the console isn't empty on load
    log_path = settings.SERVER_DIR / "log" / "server.log"
    if log_path.exists():
        try:
            async with aiofiles.open(str(log_path), "r", encoding="utf-8", errors="replace") as f:
                await f.seek(0, 2)
                size = await f.tell()
                seek_pos = max(0, size - 16384)
                await f.seek(seek_pos)
                history = await f.read()
                if history:
                    await websocket.send_text(history)
        except Exception:
            pass

    # Keep the connection alive; new content arrives via broadcaster.broadcast()
    try:
        while True:
            try:
                # Receive anything from client (ping frames, etc.) — we ignore content
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                # Send an empty keepalive so the browser doesn't time out
                try:
                    await websocket.send_text("")
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        broadcaster.disconnect(websocket)
