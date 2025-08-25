"""FastAPI application exposing system actions."""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException

from .action_registry import ActionRegistry
from . import system_actions

logger = logging.getLogger(__name__)

registry = ActionRegistry()
registry.register("web.open", system_actions.open_website)
registry.register("audio.volume.get", system_actions.get_volume)
registry.register("audio.volume.set", system_actions.set_volume)

app = FastAPI(title="Alice PC Control App", version="0.1.0")


@app.get("/api/v1/ping")
async def ping() -> dict[str, bool]:
    """Simple health check endpoint."""
    return {"ok": True}


@app.get("/api/v1/web/open")
async def web_open(url: str) -> dict[str, bool]:
    """Open a website in the default browser."""
    try:
        registry.execute("web.open", url=url)
    except Exception as exc:  # pragma: no cover - runtime errors
        logger.exception("web.open failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True}


@app.get("/api/v1/audio/volume")
async def volume_get() -> dict[str, int | bool]:
    """Return the current volume level."""
    try:
        value = registry.execute("audio.volume.get")
    except NotImplementedError as exc:  # pragma: no cover - platform
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    return {"ok": True, "value": value}


@app.post("/api/v1/audio/volume/set")
async def volume_set(value: int) -> dict[str, int | bool]:
    """Set the system volume level."""
    try:
        value = registry.execute("audio.volume.set", value=value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NotImplementedError as exc:  # pragma: no cover - platform
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    return {"ok": True, "value": value}
