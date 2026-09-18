from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any

from .models import FaceObservation


LIP_INDICES = {"upper": 13, "lower": 14, "left": 78, "right": 308}


def resource_path(*parts: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS, "mouth_monitor", *parts)
    return Path(__file__).resolve().parent.joinpath(*parts)


def model_path() -> Path:
    return resource_path("assets", "face_landmarker.task")


def distance(first: Any, second: Any) -> float:
    return math.hypot(first.x - second.x, first.y - second.y)


class FaceAnalyzer:
    def __init__(self, path: Path | None = None) -> None:
        import mediapipe as mp

        selected_path = path or model_path()
        if not selected_path.exists():
            raise RuntimeError(f"缺少 MediaPipe 模型文件：{selected_path}")
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(selected_path)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._mp = mp
        self._landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)
        self._last_timestamp_ms = 0

    def close(self) -> None:
        self._landmarker.close()

    def analyze(self, frame: Any, timestamp: float) -> FaceObservation:
        import cv2
        import numpy as np

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=np.asarray(rgb))
        timestamp_ms = max(self._last_timestamp_ms + 1, int(timestamp * 1000))
        self._last_timestamp_ms = timestamp_ms
        result = self._landmarker.detect_for_video(image, timestamp_ms)
        brightness = float(np.mean(rgb))
        if not result.face_landmarks:
            return FaceObservation(detected=False, ratio=None, brightness=brightness)

        landmarks = result.face_landmarks[0]
        raw_points = {name: landmarks[index] for name, index in LIP_INDICES.items()}
        horizontal = distance(raw_points["left"], raw_points["right"])
        if horizontal <= 1e-6:
            return FaceObservation(detected=False, ratio=None, brightness=brightness)
        vertical = distance(raw_points["upper"], raw_points["lower"])
        points = {
            name: {"x": float(point.x), "y": float(point.y)}
            for name, point in raw_points.items()
        }
        return FaceObservation(
            detected=True,
            ratio=vertical / horizontal,
            points=points,
            brightness=brightness,
        )


def annotate_frame(frame: Any, observation: FaceObservation, label: str, alerting: bool) -> Any:
    import cv2

    height, width = frame.shape[:2]
    if observation.points:
        pixels = {
            name: (int(point["x"] * width), int(point["y"] * height))
            for name, point in observation.points.items()
        }
        for pixel in pixels.values():
            cv2.circle(frame, pixel, 5, (54, 226, 145), -1)
        cv2.line(frame, pixels["upper"], pixels["lower"], (80, 180, 255), 2)
        cv2.line(frame, pixels["left"], pixels["right"], (190, 120, 255), 2)

    color = (60, 60, 255) if alerting else (54, 226, 145)
    cv2.rectangle(frame, (0, 0), (width, 56), (20, 24, 31), -1)
    cv2.putText(frame, label, (16, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.72, color, 2)
    return frame
