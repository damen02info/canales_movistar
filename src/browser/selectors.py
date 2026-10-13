# ---------------------------------------------------------------------------
# DOM selectors for Movistar Plus+ web application
# ---------------------------------------------------------------------------
COOKIE_ACCEPT = "#onetrust-accept-btn-handler, button:has-text('Aceptar todas'), button:has-text('Aceptar')"
CHANNEL_POSTER = "button.poster"
VIDEO_TAG = "video"
ERROR_MODAL_ACCEPT = "button:has-text('ACEPTAR'), button:has-text('Aceptar')"

# Helper for locating a specific channel button by its name
def channel_button_selector(channel_name: str) -> str:
    escaped = channel_name.replace("'", "\\'")
    return f"button.poster:has(img[alt='{escaped}' i])"

