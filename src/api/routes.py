import asyncio
import logging
import os
import signal
from typing import Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.api.schemas import ChannelItem, ControlRequest, PlaybackResponse, PlayRequest, StatusResponse
from src.browser.manager import manager
from src.core.autostart import get_autostart_enabled, load_settings, save_settings, set_autostart_enabled
from src.core.catalog import catalog

# ---------------------------------------------------------------------------
# Logger setup
# ---------------------------------------------------------------------------
logger = logging.getLogger("movistar.api")

# ---------------------------------------------------------------------------
# Pydantic schemas for settings
# ---------------------------------------------------------------------------
class SettingsUpdate(BaseModel):
    autostart: bool | None = None
    default_channel: str | None = None
    auto_stop_idle_minutes: int | None = None

# ---------------------------------------------------------------------------
# API endpoints router
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/api", tags=["playback"])

@router.get("/channels", response_model=list[ChannelItem])
async def list_channels() -> list[dict[str, Any]]:
    return catalog.get_all()

@router.post("/playback/start", response_model=PlaybackResponse)
async def start_playback(req: PlayRequest) -> dict[str, Any]:
    logger.info(f"Petición POST /api/playback/start recibida para: '{req.channel_id}'")
    channel = catalog.find(req.channel_id)
    if not channel:
        logger.error(f"Canal no encontrado en catálogo: '{req.channel_id}'")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Channel '{req.channel_id}' not found in catalog.",
        )

    try:
        result = await manager.start_playback(channel)
        return result
    except Exception as exc:
        logger.exception(f"Fallo al iniciar canal '{channel['name']}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start channel '{channel['name']}': {exc}",
        )

@router.post("/playback/stop")
async def stop_playback() -> dict[str, str]:
    logger.info("Petición POST /api/playback/stop recibida.")
    try:
        return await manager.stop_playback()
    except Exception as exc:
        logger.exception(f"Fallo al detener reproducción: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop playback: {exc}",
        )

@router.post("/playback/control")
async def control_playback(req: ControlRequest) -> dict[str, Any]:
    logger.info(f"Petición POST /api/playback/control: '{req.action}'")
    try:
        return await manager.send_control(req.action)
    except (RuntimeError, ValueError) as exc:
        logger.warning(f"Control inválido o sin sesión activa: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception(f"Fallo en ejecución de control: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Control execution failed: {exc}",
        )

@router.get("/playback/status", response_model=StatusResponse)
async def get_status() -> dict[str, Any]:
    return await manager.get_status()

# ---------------------------------------------------------------------------
# Settings and system management endpoints
# ---------------------------------------------------------------------------
@router.get("/settings")
async def get_system_settings() -> dict[str, Any]:
    current = load_settings()
    current["autostart"] = get_autostart_enabled()
    return current

@router.post("/settings")
async def update_system_settings(payload: SettingsUpdate) -> dict[str, Any]:
    current = load_settings()
    if payload.autostart is not None:
        set_autostart_enabled(payload.autostart)
        current["autostart"] = payload.autostart
    if payload.default_channel is not None:
        current["default_channel"] = payload.default_channel
    if payload.auto_stop_idle_minutes is not None:
        current["auto_stop_idle_minutes"] = payload.auto_stop_idle_minutes

    save_settings(current)
    logger.info(f"Ajustes actualizados: {current}")
    return current

@router.post("/system/shutdown")
async def shutdown_system() -> dict[str, str]:
    logger.info("Petición de apagado del servidor recibida.")
    async def _delayed_kill():
        await asyncio.sleep(0.5)
        await manager.stop_playback()
        os.kill(os.getpid(), signal.SIGINT)

    asyncio.create_task(_delayed_kill())
    return {"status": "shutting_down"}
