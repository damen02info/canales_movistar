import asyncio
import logging
import time
from typing import Any
from playwright.async_api import BrowserContext, Page, Playwright, async_playwright

from src.browser.selectors import (
    CHANNEL_POSTER,
    COOKIE_ACCEPT,
    VIDEO_TAG,
    channel_button_selector,
)
from src.core.config import CHANNELS_URL, PROFILE_DIR, settings

# ---------------------------------------------------------------------------
# Logger setup
# ---------------------------------------------------------------------------
logger = logging.getLogger("movistar.browser")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ---------------------------------------------------------------------------
# Browser and playback lifecycle manager
# ---------------------------------------------------------------------------
class BrowserManager:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._current_channel: dict | None = None

    def is_running(self) -> bool:
        if self._context is None or self._page is None:
            return False
        try:
            return not self._page.is_closed()
        except Exception:
            return False

    async def _cleanup(self) -> None:
        logger.info("Cleaning up browser session resources...")
        try:
            if self._context:
                await self._context.close()
        except Exception:
            pass
        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass
        self._context = None
        self._page = None
        self._playwright = None
        self._current_channel = None

    async def _launch_browser(self) -> None:
        await self._cleanup()
        logger.info(f"Launching official Google Chrome targeting: {PROFILE_DIR}")
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        self._playwright = await async_playwright().start()

        launch_args = [
            "--start-fullscreen",
            "--no-default-browser-check",
            "--disable-infobars",
            "--disable-notifications",
            "--disable-blink-features=AutomationControlled",
        ]

        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel=settings.browser_channel,
            headless=settings.headless,
            args=launch_args,
            ignore_default_args=["--no-sandbox", "--enable-automation"],
            no_viewport=True,
        )

        await self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        self._attach_page_debug_listeners(self._page)


    def _attach_page_debug_listeners(self, page: Page) -> None:
        def on_console(msg: Any) -> None:
            text = msg.text
            msg_type = msg.type
            if msg_type in ("error", "warning") or "PL01" in text or "error" in text.lower() or "widevine" in text.lower() or "drm" in text.lower():
                logger.info(f"[BROWSER-CONSOLE:{msg_type.upper()}] {text}")

        def on_page_error(err: Any) -> None:
            logger.error(f"[BROWSER-UNCAUGHT-EXCEPTION] {err}")

        page.on("console", on_console)
        page.on("pageerror", on_page_error)

    async def _handle_cookies(self) -> None:
        if not self._page:
            return
        try:
            cookie_btn = self._page.locator(COOKIE_ACCEPT)
            if await cookie_btn.first.is_visible(timeout=1500):
                logger.info("Dismissing cookie banner...")
                await cookie_btn.first.click()
                await self._page.wait_for_timeout(300)
        except Exception:
            pass

    async def _handle_error_modal(self) -> bool:
        if not self._page:
            return False
        try:
            from src.browser.selectors import ERROR_MODAL_ACCEPT
            modal_btn = self._page.locator(ERROR_MODAL_ACCEPT)
            if await modal_btn.first.is_visible(timeout=1000):
                logger.warning("Detected error modal (e.g. PL01_417), dismissing dialog...")
                await modal_btn.first.click()
                await self._page.wait_for_timeout(500)
                return True
        except Exception:
            pass
        return False

    async def _teardown_current_player(self) -> None:
        if not self._page:
            return
        try:
            await self._page.evaluate("""() => {
                const video = document.querySelector('video');
                if (video) {
                    video.pause();
                    video.removeAttribute('src');
                    video.load();
                }
            }""")
            await self._page.keyboard.press("Escape")
        except Exception:
            pass

    async def _locate_and_click_channel(self, channel_name: str) -> None:
        assert self._page is not None
        selector = channel_button_selector(channel_name)
        channel_loc = self._page.locator(selector)

        # 1. Reset scroll to top of page so search is deterministic
        logger.info(f"Resetting scroll to top and searching for '{channel_name}'...")
        await self._page.evaluate("window.scrollTo(0, 0)")
        await self._page.wait_for_timeout(250)

        # 2. Scroll incrementally downwards to discover lazy-loaded channel posters
        found = False
        for attempt in range(25):
            if await channel_loc.count() > 0 and await channel_loc.first.is_visible():
                found = True
                logger.info(f"Channel '{channel_name}' found at scroll step {attempt + 1}")
                break
            await self._page.mouse.wheel(0, 1000)
            await self._page.wait_for_timeout(250)

        if not found and await channel_loc.count() > 0:
            await channel_loc.first.scroll_into_view_if_needed()
            found = await channel_loc.first.is_visible()

        if not found:
            logger.error(f"Channel '{channel_name}' not found after scrolling grid.")
            raise RuntimeError(f"Canal '{channel_name}' no encontrado en la parrilla.")

        # 3. Click target channel button
        btn = channel_loc.first
        await btn.scroll_into_view_if_needed()
        await self._page.wait_for_timeout(150)
        logger.info(f"Clicking channel button for '{channel_name}'...")
        await btn.click()

    async def start_playback(self, channel_info: dict) -> dict[str, Any]:
        async with self._lock:
            channel_name = channel_info["name"]
            t_start = time.time()
            logger.info(f">>> INICIANDO SINTONIZACIÓN: '{channel_name}' (ID: {channel_info['id']})")

            # 1. Check browser lifecycle, teardown any active player, and return cleanly to grid
            if self.is_running():
                try:
                    await self._teardown_current_player()
                    await self._page.goto(CHANNELS_URL, wait_until="domcontentloaded")
                except Exception as exc:
                    logger.warning(f"Session reconnect needed ({exc}), relaunching Chrome...")
                    await self._launch_browser()
                    assert self._page is not None
                    await self._page.goto(CHANNELS_URL, wait_until="domcontentloaded")
            else:
                await self._launch_browser()
                assert self._page is not None
                await self._page.goto(CHANNELS_URL, wait_until="domcontentloaded")

            await self._handle_cookies()

            # 2. Wait for grid posters to initialize
            logger.info("Waiting for channel posters to load...")
            await self._page.wait_for_selector(CHANNEL_POSTER, timeout=settings.page_load_timeout_ms)

            # 3. Search and click channel
            await self._locate_and_click_channel(channel_name)

            # 4. Check for warning dialogs before player loads
            dismissed = await self._handle_error_modal()
            if dismissed:
                logger.info(f"Retrying click for '{channel_name}' after error dismissal...")
                await self._locate_and_click_channel(channel_name)

            # 5. Wait for video element
            logger.info("Waiting for video player to initialize...")
            await self._page.wait_for_selector(VIDEO_TAG, timeout=settings.video_wait_timeout_ms)

            # 6. Check once more if error modal popped up after player mount
            if await self._handle_error_modal():
                logger.info(f"Retrying channel '{channel_name}' after player error modal dismissal...")
                await self._locate_and_click_channel(channel_name)
                await self._page.wait_for_selector(VIDEO_TAG, timeout=settings.video_wait_timeout_ms)

            # 7. Trigger player fullscreen directly via keyboard (avoid pointer overlay issues)
            logger.info("Setting player to fullscreen via keyboard...")
            await self._page.keyboard.press("f")
            await self._page.wait_for_timeout(300)
            self._current_channel = channel_info

            # 8. Evaluate video status
            details = None
            try:
                details = await self._page.evaluate("""() => {
                    const v = document.querySelector('video');
                    if (!v) return null;
                    return {
                        paused: v.paused,
                        readyState: v.readyState,
                        width: v.videoWidth,
                        height: v.videoHeight,
                        volume: v.volume,
                        muted: v.muted
                    };
                }""")
            except Exception:
                pass

            duration = round(time.time() - t_start, 2)
            logger.info(f">>> SINTONIZACIÓN COMPLETADA en {duration}s: '{channel_name}'")

            return {
                "status": "playing",
                "channel": channel_info,
                "video": details,
            }

    async def stop_playback(self) -> dict[str, str]:
        async with self._lock:
            logger.info("Stopping playback session...")
            await self._cleanup()
            return {"status": "stopped"}

    async def send_control(self, action: str) -> dict[str, Any]:
        async with self._lock:
            if not self.is_running() or not self._page or self._page.is_closed():
                raise RuntimeError("No active playback session.")

            act = action.lower()
            logger.info(f"Applying media control: '{act}'")

            if act == "play":
                await self._page.evaluate("document.querySelector('video')?.play()")
            elif act == "pause":
                await self._page.evaluate("document.querySelector('video')?.pause()")
            elif act in ("toggle_play", "toggle"):
                await self._page.evaluate("""() => {
                    const v = document.querySelector('video');
                    if (v) {
                        if (v.paused) { v.play(); } else { v.pause(); }
                    }
                }""")
            elif act == "fullscreen":
                await self._page.keyboard.press("f")
            elif act == "mute":
                await self._page.evaluate("""() => {
                    const v = document.querySelector('video');
                    if (v) {
                        v.muted = !v.muted;
                    }
                }""")
            elif act == "volume_up":
                await self._page.evaluate("""() => {
                    const v = document.querySelector('video');
                    if (v) {
                        v.muted = false;
                        v.volume = Math.min(1.0, v.volume + 0.1);
                    }
                }""")
            elif act == "volume_down":
                await self._page.evaluate("""() => {
                    const v = document.querySelector('video');
                    if (v) {
                        v.volume = Math.max(0.0, v.volume - 0.1);
                    }
                }""")
            else:
                raise ValueError(f"Unsupported action: '{action}'")

            details = None
            try:
                details = await self._page.evaluate("""() => {
                    const v = document.querySelector('video');
                    if (!v) return null;
                    return {
                        paused: v.paused,
                        volume: v.volume,
                        muted: v.muted
                    };
                }""")
            except Exception:
                pass

            return {"status": "ok", "action_applied": act, "video": details}

    async def get_status(self) -> dict[str, Any]:
        async with self._lock:
            if not self.is_running():
                return {
                    "active": False,
                    "state": "stopped",
                    "channel": None,
                    "video": None,
                }

            assert self._page is not None
            details = None
            try:
                details = await self._page.evaluate("""() => {
                    const v = document.querySelector('video');
                    if (!v) return null;
                    return {
                        paused: v.paused,
                        readyState: v.readyState,
                        width: v.videoWidth,
                        height: v.videoHeight,
                        volume: v.volume,
                        muted: v.muted
                    };
                }""")
            except Exception:
                pass

            state = "playing" if details and not details.get("paused") else "paused" if details else "idle"

            return {
                "active": True,
                "state": state,
                "channel": self._current_channel,
                "video": details,
            }

manager = BrowserManager()
