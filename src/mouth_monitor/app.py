from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Literal

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from .engine import MonitorEngine
from .vision import resource_path


class StartRequest(BaseModel):
    camera_index: int = Field(default=0, ge=0, le=20)


class SettingsRequest(BaseModel):
    sustained_seconds: float = Field(ge=1.0, le=60.0)
    cooldown_seconds: float = Field(ge=0.0, le=300.0)
    movement_sensitivity: float = Field(ge=0.002, le=0.05)
    sound_enabled: bool = True


def create_app(engine: MonitorEngine | None = None) -> FastAPI:
    monitor = engine or MonitorEngine()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        monitor.stop()

    app = FastAPI(title="嘴唇闭合提醒器", version="0.1.0", lifespan=lifespan)
    app.state.monitor = monitor

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        path = resource_path("web", "index.html")
        return Path(path).read_text(encoding="utf-8")

    @app.get("/api/status")
    async def status() -> dict[str, object]:
        return monitor.snapshot()

    @app.get("/api/cameras")
    async def cameras() -> dict[str, object]:
        return {"cameras": await asyncio.to_thread(monitor.available_cameras)}

    @app.post("/api/start")
    async def start(payload: StartRequest) -> dict[str, bool]:
        monitor.start(payload.camera_index)
        return {"ok": True}

    @app.post("/api/pause")
    async def pause() -> dict[str, bool]:
        await asyncio.to_thread(monitor.pause)
        return {"ok": True}

    @app.post("/api/stop")
    async def stop() -> dict[str, bool]:
        await asyncio.to_thread(monitor.stop)
        return {"ok": True}

    @app.post("/api/calibrate/{mode}")
    async def calibrate(mode: Literal["closed", "open"]) -> dict[str, bool]:
        try:
            monitor.begin_calibration(mode)
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"ok": True}

    @app.post("/api/calibration/reset")
    async def reset_calibration() -> dict[str, bool]:
        monitor.reset_calibration()
        return {"ok": True}

    @app.post("/api/settings")
    async def update_settings(payload: SettingsRequest) -> dict[str, bool]:
        try:
            monitor.update_settings(**payload.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"ok": True}

    @app.post("/api/reminder/test")
    async def test_reminder() -> dict[str, bool]:
        return {"ok": True, "played": monitor.test_reminder()}

    @app.get("/video")
    async def video() -> StreamingResponse:
        async def frames() -> AsyncIterator[bytes]:
            last_frame: bytes | None = None
            while True:
                current = monitor.latest_jpeg
                if current and current is not last_frame:
                    last_frame = current
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + current + b"\r\n"
                await asyncio.sleep(0.05)

        return StreamingResponse(frames(), media_type="multipart/x-mixed-replace; boundary=frame")

    @app.websocket("/ws")
    async def websocket_status(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                await websocket.send_json(monitor.snapshot())
                await asyncio.sleep(0.1)
        except (WebSocketDisconnect, RuntimeError):
            return

    return app


app = create_app()
