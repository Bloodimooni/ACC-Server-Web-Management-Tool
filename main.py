"""
ACC Server Management Dashboard
Run:  python main.py
Add a user:  python main.py adduser <username>
"""
import sys

# Must be set before uvicorn/asyncio starts on Windows
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import argparse
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import FileResponse, RedirectResponse

from app.api.routes_auth import router as auth_router
from app.api.routes_config import router as config_router
from app.api.routes_server import router as server_router
from app.auth.session import read_session
from app.config import settings
from app.process import manager
from app.ws.log_streamer import broadcaster, stream_logs

FRONTEND_DIR = Path(__file__).parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    manager.set_broadcaster(broadcaster)
    yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)

app.include_router(auth_router)
app.include_router(config_router)
app.include_router(server_router)


@app.get("/login")
async def login_page():
    return FileResponse(FRONTEND_DIR / "login.html")


@app.get("/")
async def index(request: Request):
    try:
        read_session(request)
    except Exception:
        return RedirectResponse("/login", status_code=302)
    return FileResponse(FRONTEND_DIR / "index.html")


@app.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket):
    await stream_logs(websocket)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="ACC Server Dashboard")
    sub = parser.add_subparsers(dest="cmd")
    add_cmd = sub.add_parser("adduser", help="Add or update a local dashboard user")
    add_cmd.add_argument("username")
    args = parser.parse_args()

    if args.cmd == "adduser":
        import getpass
        from app.auth.local import add_user
        pw = getpass.getpass(f"Password for '{args.username}': ")
        pw2 = getpass.getpass("Confirm password: ")
        if pw != pw2:
            print("Passwords do not match.")
            sys.exit(1)
        add_user(args.username, pw)
        print(f"User '{args.username}' saved.")
    else:
        import uvicorn
        uvicorn.run(app, host=settings.HOST, port=settings.PORT)


if __name__ == "__main__":
    main()
