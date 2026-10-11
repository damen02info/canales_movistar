from typing import Any, Optional
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Request and response Pydantic models
# ---------------------------------------------------------------------------
class PlayRequest(BaseModel):
    channel_id: str = Field(..., description="Channel ID, code or name to play")

class ControlRequest(BaseModel):
    action: str = Field(..., description="Action to perform: play, pause, toggle_play, mute, fullscreen, volume_up, volume_down")

class ChannelItem(BaseModel):
    id: str
    name: str
    code: Optional[str] = None
    logo_url: Optional[str] = None
    category: Optional[str] = None

class PlaybackResponse(BaseModel):
    status: str
    channel: Optional[ChannelItem] = None
    video: Optional[dict[str, Any]] = None

class StatusResponse(BaseModel):
    active: bool
    state: str
    channel: Optional[ChannelItem] = None
    video: Optional[dict[str, Any]] = None
