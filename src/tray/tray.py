import threading
import webbrowser
from pathlib import Path
from PIL import Image, ImageDraw
import pystray

from src.core.autostart import get_autostart_enabled, load_settings, set_autostart_enabled

# ---------------------------------------------------------------------------
# Tray icon loader and procedural fallback
# ---------------------------------------------------------------------------
import sys

def create_tray_icon_image() -> Image.Image:
    if getattr(sys, "frozen", False):
        base_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    else:
        base_dir = Path(__file__).resolve().parent.parent.parent

    icon_path = base_dir / "static" / "icon.png"
    if icon_path.exists():
        try:
            return Image.open(icon_path).convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)
        except Exception:
            pass

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle(
        [(8, 12), (56, 44)],
        radius=6,
        outline=(244, 244, 245, 255),
        width=3,
    )
    draw.line([(24, 52), (40, 52)], fill=(244, 244, 245, 255), width=3)
    draw.line([(32, 44), (32, 52)], fill=(244, 244, 245, 255), width=3)
    draw.ellipse([(30, 26), (34, 30)], fill=(244, 244, 245, 255))
    return img

# ---------------------------------------------------------------------------
# System Tray Manager
# ---------------------------------------------------------------------------
class SystemTrayApp:
    def __init__(self, port: int = 8765) -> None:
        self.port = port
        self.icon: pystray.Icon | None = None
        self._thread: threading.Thread | None = None

    def _open_dashboard(self, icon=None, item=None) -> None:
        webbrowser.open(f"http://localhost:{self.port}/")

    def _toggle_autostart(self, icon=None, item=None) -> None:
        current = get_autostart_enabled()
        set_autostart_enabled(not current)

    def _on_exit(self, icon=None, item=None) -> None:
        if self.icon:
            self.icon.stop()
        # Trigger clean exit
        import os
        import signal
        os.kill(os.getpid(), signal.SIGINT)

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem("Abrir Panel de Control", self._open_dashboard, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Iniciar con Windows",
                self._toggle_autostart,
                checked=lambda item: get_autostart_enabled(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Salir", self._on_exit),
        )

    def run_detached(self) -> None:
        image = create_tray_icon_image()
        menu = self._build_menu()
        self.icon = pystray.Icon(
            name="MovistarPlusController",
            icon=image,
            title="Movistar Plus+ Controller",
            menu=menu,
        )

        def _runner():
            try:
                self.icon.run()
            except Exception as exc:
                print(f"System tray runner exception: {exc}")

        self._thread = threading.Thread(target=_runner, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass

tray_app = SystemTrayApp()
