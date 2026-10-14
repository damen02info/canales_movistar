import sys
from pathlib import Path
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Path resolutions and system settings
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))
else:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    BUNDLE_DIR = BASE_DIR

PROFILE_DIR = BASE_DIR / "data" / "chrome_profile"
CHANNELS_FILE = BASE_DIR / "config" / "channels.json"
if not CHANNELS_FILE.exists() and (BUNDLE_DIR / "config" / "channels.json").exists():
    CHANNELS_FILE = BUNDLE_DIR / "config" / "channels.json"

CHANNELS_URL = "https://ver.movistarplus.es/canales"

class Settings(BaseModel):
    app_name: str = "Movistar Plus+ Channel Controller"
    host: str = "0.0.0.0"
    port: int = 8765
    browser_channel: str = "chrome"
    headless: bool = False
    window_maximized: bool = True
    page_load_timeout_ms: int = 30000
    video_wait_timeout_ms: int = 15000

settings = Settings()
