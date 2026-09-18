from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from mouth_monitor.app import create_app


class FakeEngine:
    def __init__(self) -> None:
        self.started_with: int | None = None
        self.latest_jpeg: bytes | None = None
        self.settings_update: dict[str, Any] | None = None

    def snapshot(self) -> dict[str, Any]:
        return {"state": "stopped", "state_label": "已停止", "settings": {}}

    def available_cameras(self) -> list[dict[str, int | str]]:
        return [{"index": 0, "label": "摄像头 0"}]

    def start(self, camera_index: int) -> None:
        self.started_with = camera_index

    def pause(self) -> None:
        return None

    def stop(self) -> None:
        return None

    def begin_calibration(self, mode: str) -> None:
        return None

    def reset_calibration(self) -> None:
        return None

    def update_settings(self, **settings: Any) -> None:
        self.settings_update = settings

    def test_reminder(self) -> bool:
        return True


def test_index_and_status() -> None:
    engine = FakeEngine()
    with TestClient(create_app(engine)) as client:
        response = client.get("/")
        status = client.get("/api/status")

    assert response.status_code == 200
    assert "嘴唇闭合提醒器" in response.text
    assert status.json()["state"] == "stopped"


def test_start_and_update_settings() -> None:
    engine = FakeEngine()
    with TestClient(create_app(engine)) as client:
        start = client.post("/api/start", json={"camera_index": 2})
        settings = client.post(
            "/api/settings",
            json={
                "sustained_seconds": 6,
                "cooldown_seconds": 20,
                "movement_sensitivity": 0.01,
                "sound_enabled": False,
            },
        )

    assert start.status_code == 200
    assert settings.status_code == 200
    assert engine.started_with == 2
    assert engine.settings_update == {
        "sustained_seconds": 6.0,
        "cooldown_seconds": 20.0,
        "movement_sensitivity": 0.01,
        "sound_enabled": False,
    }
