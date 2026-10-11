import json
from src.core.config import CHANNELS_FILE

# ---------------------------------------------------------------------------
# Channel catalog repository
# ---------------------------------------------------------------------------
class ChannelCatalog:
    def __init__(self) -> None:
        self._channels: list[dict] = []
        self._by_id: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if not CHANNELS_FILE.exists():
            self._channels = []
            return

        with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
            self._channels = json.load(f)

        self._by_id = {ch["id"]: ch for ch in self._channels}

    def get_all(self) -> list[dict]:
        return self._channels

    def find(self, identifier: str) -> dict | None:
        # 1. Exact ID match
        if identifier in self._by_id:
            return self._by_id[identifier]

        # 2. Exact case-insensitive name match
        norm = identifier.strip().lower()
        for ch in self._channels:
            if ch["name"].strip().lower() == norm:
                return ch

        # 3. Partial name match
        for ch in self._channels:
            if norm in ch["name"].strip().lower():
                return ch

        return None

catalog = ChannelCatalog()
