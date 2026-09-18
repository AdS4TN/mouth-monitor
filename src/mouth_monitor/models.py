from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


CONFIG_VERSION = 1


class MonitorState(StrEnum):
    STOPPED = "stopped"
    PAUSED = "paused"
    STARTING = "starting"
    NO_CAMERA = "no_camera"
    NO_FACE = "no_face"
    NOT_CALIBRATED = "not_calibrated"
    CALIBRATING = "calibrating"
    CLOSED = "closed"
    MOUTH_ACTIVE = "mouth_active"
    OPEN_CANDIDATE = "open_candidate"
    SUSTAINED_OPEN = "sustained_open"
    COOLDOWN = "cooldown"
    ERROR = "error"


STATE_LABELS = {
    MonitorState.STOPPED: "已停止",
    MonitorState.PAUSED: "已暂停",
    MonitorState.STARTING: "正在启动",
    MonitorState.NO_CAMERA: "摄像头不可用",
    MonitorState.NO_FACE: "未检测到人脸",
    MonitorState.NOT_CALIBRATED: "尚未校准",
    MonitorState.CALIBRATING: "校准中",
    MonitorState.CLOSED: "嘴唇闭合",
    MonitorState.MOUTH_ACTIVE: "嘴部活动",
    MonitorState.OPEN_CANDIDATE: "疑似持续张嘴",
    MonitorState.SUSTAINED_OPEN: "持续张嘴",
    MonitorState.COOLDOWN: "已提醒，冷却中",
    MonitorState.ERROR: "运行错误",
}


@dataclass(slots=True)
class CalibrationProfile:
    closed_baseline: float
    open_baseline: float
    enter_threshold: float
    exit_threshold: float
    camera_index: int
    version: int = CONFIG_VERSION

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CalibrationProfile":
        return cls(
            closed_baseline=float(data["closed_baseline"]),
            open_baseline=float(data["open_baseline"]),
            enter_threshold=float(data["enter_threshold"]),
            exit_threshold=float(data["exit_threshold"]),
            camera_index=int(data.get("camera_index", 0)),
            version=int(data.get("version", CONFIG_VERSION)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AppSettings:
    camera_index: int = 0
    sustained_seconds: float = 8.0
    cooldown_seconds: float = 30.0
    movement_sensitivity: float = 0.012
    sound_enabled: bool = True
    calibration: CalibrationProfile | None = None
    version: int = CONFIG_VERSION

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppSettings":
        calibration_data = data.get("calibration")
        return cls(
            camera_index=int(data.get("camera_index", 0)),
            sustained_seconds=float(data.get("sustained_seconds", 8.0)),
            cooldown_seconds=float(data.get("cooldown_seconds", 30.0)),
            movement_sensitivity=float(data.get("movement_sensitivity", 0.012)),
            sound_enabled=bool(data.get("sound_enabled", True)),
            calibration=(
                CalibrationProfile.from_dict(calibration_data)
                if isinstance(calibration_data, dict)
                else None
            ),
            version=int(data.get("version", CONFIG_VERSION)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MouthFeatures:
    ratio: float
    smoothed_ratio: float
    movement_variance: float
    timestamp: float


@dataclass(slots=True)
class FaceObservation:
    detected: bool
    ratio: float | None
    points: dict[str, Any] | None = None
    brightness: float = 0.0


@dataclass(slots=True)
class StateResult:
    state: MonitorState
    open_duration: float
    smoothed_ratio: float | None
    movement_variance: float
