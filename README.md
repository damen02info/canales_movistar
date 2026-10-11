# Movistar Plus+ Controller

Automation engine and web dashboard for controlling Movistar Plus+ channel playback on a dedicated host PC from any device on your local network.

## Features

- **Web Dashboard**: Responsive dark-mode interface optimized for desktop, tablets, and mobile devices.
- **Channel Switching**: Fast channel search and instant switching across the channel grid.
- **Playback Controls**: Full control over volume, mute, play/pause toggle, fullscreen, and session shutdown.
- **System Tray Integration**: Native tray menu with background execution and autostart toggle.
- **Session Persistence**: Chrome persistent profile keeps your Movistar Plus+ credentials and cookies stored locally.
- **RESTful API**: Clean HTTP endpoints for integration into home automation setups (e.g. Home Assistant, stream decks).

## Requirements

- Python 3.10+
- **Google Chrome** (official release required for Widevine DRM support on Movistar Plus+)
- Windows 10/11 (for executable builds and autostart integration) or Linux

## Setup & Local Run

1. Clone the repository and navigate to the project directory:
   ```bash
   git clone <repository-url>
   cd CanalesMovistar
   ```

2. Create and activate a virtual environment:
   - On Windows:
     ```cmd
     python -m venv .venv
     .venv\Scripts\activate
     ```
   - On Linux/macOS:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```

3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Start the application:
   ```bash
   python src/main.py
   ```

5. Open your browser and navigate to `http://localhost:8765` (or `http://<host-ip>:8765` from a mobile device on your LAN).

## Building for Windows (`.exe`)

PyInstaller packages the application into a distribution folder containing the executable, static assets, and configurations.

1. Ensure Google Chrome and Python are installed on the Windows target machine.
2. In the project root, activate your virtual environment with all dependencies installed.
3. Run PyInstaller using the provided `.spec` file:
   ```cmd
   pyinstaller MovistarPlusController.spec
   ```
4. The output will be located in:
   ```
   dist/MovistarPlusController/
   ```
5. Distribute the entire `dist/MovistarPlusController` folder (do not move `MovistarPlusController.exe` out of its folder).

### First-Time Authentication

When you trigger playback for the first time:
1. Google Chrome will launch in full screen with your local profile stored in `data/chrome_profile/`.
2. Enter your Movistar Plus+ account credentials in the opened browser window.
3. Once logged in, your session cookies and tokens remain stored in `data/chrome_profile/` across restarts.

## Configuration

Settings are saved in `config/settings.json` upon runtime changes:

| Setting | Type | Default | Description |
|---|---|---|---|
| `port` | Integer | `8765` | HTTP server port |
| `autostart` | Boolean | `false` | Launch on Windows startup |
| `default_channel` | String | `"la_1"` | Initial channel on launch |
| `auto_fullscreen` | Boolean | `true` | Automatically enter fullscreen |
| `auto_stop_idle_minutes` | Integer | `0` | Auto-stop timer (`0` disables) |

## Project Structure

```
.
├── config/
│   └── channels.json           # Channel definitions and URLs
├── scripts/
│   └── generate_icon.py        # Icon generator script
├── src/
│   ├── api/                    # FastAPI endpoints
│   ├── browser/                # Playwright automation manager
│   ├── core/                   # App configuration and autostart
│   ├── tray/                   # System tray integration
│   └── main.py                 # Application entry point
├── static/
│   ├── app.js                  # Frontend UI logic
│   ├── index.html              # Dashboard markup
│   ├── styles.css              # Obsidian theme styles
│   ├── icon.ico                # Multi-size executable icon
│   └── icon.png                # High-res application icon
├── MovistarPlusController.spec # PyInstaller build specification
└── requirements.txt            # Python dependencies
```
