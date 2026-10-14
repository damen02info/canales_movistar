import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator

# ---------------------------------------------------------------------------
# Standard stream fallback for windowed / noconsole execution
# ---------------------------------------------------------------------------
class _NullStream:
    def write(self, text: str) -> int:
        return len(text)

    def flush(self) -> None:
        pass

    def isatty(self) -> bool:
        return False

if sys.stdout is None:
    sys.stdout = _NullStream()

if sys.stderr is None:
    sys.stderr = _NullStream()

if sys.stdin is None:
    try:
        sys.stdin = open(os.devnull, "r", encoding="utf-8")
    except Exception:
        pass

if getattr(sys, "frozen", False):
    try:
        log_dir = Path(sys.executable).resolve().parent / "data"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = open(log_dir / "app.log", "a", encoding="utf-8")
        if isinstance(sys.stdout, _NullStream):
            sys.stdout = log_file
        if isinstance(sys.stderr, _NullStream):
            sys.stderr = log_file
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Path setup ensuring root imports work from any working directory
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    ROOT_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
else:
    ROOT_DIR = Path(__file__).resolve().parent.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import uvicorn
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.routes import router
from src.browser.manager import manager
from src.core.autostart import load_settings
from src.core.config import settings
from src.tray.tray import tray_app

# ---------------------------------------------------------------------------
# Application lifespan and teardown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    try:
        tray_app.port = settings.port
        tray_app.run_detached()
    except Exception as exc:
        print(f"System tray start notice: {exc}")

    yield

    try:
        tray_app.stop()
    except Exception:
        pass
    try:
        await manager.stop_playback()
    except Exception:
        pass

# ---------------------------------------------------------------------------
# FastAPI factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and root web UI
STATIC_DIR = ROOT_DIR / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> Response:
        fav_icon = STATIC_DIR / "favicon.ico"
        if fav_icon.exists():
            return FileResponse(fav_icon, media_type="image/x-icon")
# WebSocket bridge endpoint for Chrome extension
from fastapi import WebSocket, WebSocketDisconnect
from src.browser.bridge import bridge

@app.websocket("/ws/browser")
async def ws_browser_endpoint(websocket: WebSocket) -> None:
    await bridge.register(websocket)
    try:
        while True:
            msg = await websocket.receive_json()
            bridge.handle_message(msg)
    except (WebSocketDisconnect, Exception):
        bridge.unregister()

app.include_router(router)

def run_server() -> None:
    app_settings = load_settings()
    server_port = int(app_settings.get("port", settings.port))
    settings.port = server_port
    uvicorn.run(app, host=settings.host, port=server_port, reload=False)

if __name__ == "__main__":
    run_server()
