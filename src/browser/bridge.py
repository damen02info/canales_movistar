import asyncio
import logging
import uuid
from typing import Any
from fastapi import WebSocket

# ---------------------------------------------------------------------------
# Logger setup
# ---------------------------------------------------------------------------
logger = logging.getLogger("movistar.bridge")

# ---------------------------------------------------------------------------
# WebSocket Bridge for Chrome Extension Communication
# ---------------------------------------------------------------------------
class BrowserBridge:
    def __init__(self) -> None:
        self.active_socket: WebSocket | None = None
        self._connected_event = asyncio.Event()
        self._pending: dict[str, asyncio.Future[Any]] = {}

    def is_connected(self) -> bool:
        return self.active_socket is not None

    async def wait_for_connection(self, timeout: float = 20.0) -> bool:
        if self.is_connected():
            return True
        try:
            await asyncio.wait_for(self._connected_event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def register(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active_socket = ws
        self._connected_event.set()
        logger.info("Extension WebSocket registered and active.")

    def unregister(self) -> None:
        self.active_socket = None
        self._connected_event.clear()
        for fut in self._pending.values():
            if not fut.done():
                fut.set_exception(ConnectionResetError("Browser extension disconnected"))
        self._pending.clear()
        logger.info("Extension WebSocket connection cleared.")

    async def send_command(self, action: str, timeout: float = 30.0, **kwargs: Any) -> Any:
        if not self.is_connected() or self.active_socket is None:
            raise RuntimeError("Browser extension is not connected.")

        req_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        future: asyncio.Future[Any] = loop.create_future()
        self._pending[req_id] = future

        payload = {"id": req_id, "action": action, **kwargs}
        try:
            await self.active_socket.send_json(payload)
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            self._pending.pop(req_id, None)

    def handle_message(self, message: dict[str, Any]) -> None:
        req_id = message.get("id")
        if req_id and req_id in self._pending:
            fut = self._pending[req_id]
            if not fut.done():
                if message.get("ok"):
                    fut.set_result(message.get("data"))
                else:
                    fut.set_exception(RuntimeError(message.get("error", "Unknown extension error")))

bridge = BrowserBridge()
