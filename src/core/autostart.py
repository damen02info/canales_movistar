import json
import os
import sys
from pathlib import Path

from src.core.config import BASE_DIR

# ---------------------------------------------------------------------------
# Settings file and Windows registry keys
# ---------------------------------------------------------------------------
SETTINGS_FILE = BASE_DIR / "config" / "settings.json"
APP_NAME = "MovistarPlusController"

DEFAULT_SETTINGS = {
    "autostart": False,
    "port": 8765,
    "default_channel": "la_1",
    "auto_fullscreen": True,
    "auto_stop_idle_minutes": 0,
}

# ---------------------------------------------------------------------------
# Settings persistence
# ---------------------------------------------------------------------------
def load_settings() -> dict:
    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        return dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            merged = dict(DEFAULT_SETTINGS)
            merged.update(data)
            return merged
    except Exception:
        return dict(DEFAULT_SETTINGS)

def save_settings(data: dict) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ---------------------------------------------------------------------------
# Windows Autostart Manager (Registry Run key)
# ---------------------------------------------------------------------------
def is_windows() -> bool:
    return sys.platform.startswith("win")

def get_autostart_enabled() -> bool:
    settings = load_settings()
    if not is_windows():
        return settings.get("autostart", False)

    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ,
        )
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False

def set_autostart_enabled(enabled: bool) -> bool:
    settings = load_settings()
    settings["autostart"] = enabled
    save_settings(settings)

    if not is_windows():
        return enabled

    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_WRITE,
        )
        if enabled:
            exe_path = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(sys.argv[0])
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return enabled
    except Exception as exc:
        print(f"Failed to update Windows registry autostart: {exc}")
        return False
