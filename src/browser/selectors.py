# ---------------------------------------------------------------------------
# DOM selectors for Movistar Plus+ web application
# ---------------------------------------------------------------------------
COOKIE_ACCEPT = "#onetrust-accept-btn-handler, button:has-text('Aceptar todas'), button:has-text('Aceptar')"
CHANNEL_POSTER = "button.poster, a.mplus-collection__image, .brand-carousel li"
VIDEO_TAG = "video"
ERROR_MODAL_ACCEPT = "button:has-text('ACEPTAR'), button:has-text('Aceptar')"

# Helper for locating a specific channel element by name or technical code
def channel_button_selector(channel_name: str, code: str = "") -> str:
    escaped = channel_name.replace("'", "\\'")
    selectors = [
        f"button.poster:has(img[alt*='{escaped}' i])",
        f"a.mplus-collection__image:has(img[alt*='{escaped}' i])",
        f"a.mplus-collection__image[aria-label*='{escaped}' i]",
        f"button:has(img[alt*='{escaped}' i])",
        f"a:has(img[alt*='{escaped}' i])",
    ]
    if code:
        code_esc = code.replace("'", "\\'")
        selectors.extend([
            f"a.mplus-collection__image:has(img[src*='{code_esc}' i])",
            f"button.poster:has(img[src*='{code_esc}' i])",
            f"a[href*='id={code_esc.lower()}']",
            f"a:has(img[src*='{code_esc}' i])",
        ])
    return ", ".join(selectors)
