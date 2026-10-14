import asyncio
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from src.browser.bridge import bridge
from src.core.config import CHANNELS_URL, EXTENSION_DIR, PROFILE_DIR, settings

# ---------------------------------------------------------------------------
# Logger setup
# ---------------------------------------------------------------------------
logger = logging.getLogger("movistar.browser")

# ---------------------------------------------------------------------------
# Browser and playback lifecycle manager (Native Chrome + WebSocket Extension)
# ---------------------------------------------------------------------------
class BrowserManager:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._process: subprocess.Popen[bytes] | None = None
        self._current_channel: dict[str, Any] | None = None

    def _find_chrome_executable(self) -> str:
        # 1. Check environment variable override
        env_chrome = os.environ.get("CHROME_BIN")
        if env_chrome and Path(env_chrome).exists():
            return env_chrome

        # 2. Windows standard candidate locations
        if sys.platform == "win32":
            win_candidates = [
                Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "Google" / "Chrome" / "Application" / "chrome.exe",
                Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")) / "Google" / "Chrome" / "Application" / "chrome.exe",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe",
            ]
            for candidate in win_candidates:
                if candidate.exists():
                    return str(candidate)

        # 3. Linux and Unix search paths
        unix_names = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]
        for name in unix_names:
            resolved = shutil.which(name)
            if resolved:
                return resolved

        unix_paths = [
            Path("/usr/bin/google-chrome"),
            Path("/usr/bin/google-chrome-stable"),
            Path("/opt/google/chrome/chrome"),
        ]
        for candidate in unix_paths:
            if candidate.exists():
                return str(candidate)

        raise FileNotFoundError("Google Chrome official binary not found on this system.")

    def is_running(self) -> bool:
        if self._process is None:
            return False
        return self._process.poll() is None

    async def _cleanup(self) -> None:
        if self._process:
            logger.info("Terminating existing Chrome browser process...")
            try:
                self._process.terminate()
                # Non-blocking poll wait
                for _ in range(10):
                    if self._process.poll() is not None:
                        break
                    await asyncio.sleep(0.1)
                if self._process.poll() is None:
                    self._process.kill()
            except Exception as exc:
                logger.warning(f"Error during Chrome process termination: {exc}")
        self._process = None
        self._current_channel = None

    async def _launch_browser(self) -> None:
        await self._cleanup()
        chrome_bin = self._find_chrome_executable()
        logger.info(f"Launching official Chrome ({chrome_bin}) targeting profile: {PROFILE_DIR}")

        PROFILE_DIR.mkdir(parents=True, exist_ok=True)

        cmd = [
            chrome_bin,
            f"--user-data-dir={PROFILE_DIR}",
            f"--load-extension={EXTENSION_DIR}",
            "--start-fullscreen",
            "--no-default-browser-check",
            "--disable-infobars",
            "--disable-notifications",
            "--disable-search-engine-choice-screen",
            CHANNELS_URL,
        ]

        logger.info(f"Executing: {' '.join(cmd)}")
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        logger.info("Waiting for Chrome extension WebSocket connection...")
        connected = await bridge.wait_for_connection(timeout=30.0)
        if not connected:
            await self._cleanup()
            raise TimeoutError("Timed out waiting for Chrome extension to connect via WebSocket.")
        logger.info("Chrome extension successfully connected and ready.")

    async def start_playback(self, channel_info: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            channel_name = channel_info["name"]
            t_start = time.time()
            logger.info(f">>> INICIANDO SINTONIZACIÓN: '{channel_name}' (ID: {channel_info['id']})")

            if not self.is_running() or not bridge.is_connected():
                await self._launch_browser()

            timeout_sec = max(15.0, settings.page_load_timeout_ms / 1000.0)
            res = await bridge.send_command(
                "play_channel",
                channel=channel_info,
                timeout=timeout_sec,
            )

            self._current_channel = channel_info
            duration = round(time.time() - t_start, 2)
            logger.info(f">>> SINTONIZACIÓN COMPLETADA en {duration}s: '{channel_name}'")

            return {
                "status": "playing",
                "channel": channel_info,
                "video": res.get("video") if isinstance(res, dict) else None,
            }

    async def stop_playback(self) -> dict[str, str]:
        async with self._lock:
            logger.info("Stopping playback session and terminating browser...")
            await self._cleanup()
            return {"status": "stopped"}

    async def send_control(self, action: str) -> dict[str, Any]:
        async with self._lock:
            if not self.is_running() or not bridge.is_connected():
                raise RuntimeError("No active playback session or extension disconnected.")

            act = action.lower()
            logger.info(f"Applying media control: '{act}'")
            res = await bridge.send_command("control", control_action=act, timeout=10.0)

            video_details = res.get("video") if isinstance(res, dict) else None
            return {"status": "ok", "action_applied": act, "video": video_details}

    async def get_status(self) -> dict[str, Any]:
        async with self._lock:
            if not self.is_running() or not bridge.is_connected():
                return {
                    "active": False,
                    "state": "stopped",
                    "channel": None,
                    "video": None,
                }

            try:
                res = await bridge.send_command("status", timeout=5.0)
                state = res.get("state", "idle")
                return {
                    "active": res.get("active", True),
                    "state": state,
                    "channel": self._current_channel,
                    "video": res.get("video"),
                }
            except Exception:
                return {
                    "active": True,
                    "state": "idle",
                    "channel": self._current_channel,
                    "video": None,
                }

manager = BrowserManager()
