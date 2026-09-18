from __future__ import annotations

import statistics
import threading
import time
from collections import deque
from dataclasses import replace
from typing import Any, Literal

from .calibration import CalibrationSession, build_profile
from .camera import open_camera, scan_cameras
from .models import AppSettings, MonitorState, STATE_LABELS, StateResult
from .reminder import ReminderController
from .state_machine import MouthStateMachine
from .storage import SettingsRepository
from .vision import FaceAnalyzer, annotate_frame


class MonitorEngine:
    def __init__(self, repository: SettingsRepository | None = None) -> None:
        self.repository = repository or SettingsRepository()
        self.settings, self.config_warning = self.repository.load()
        self.state_machine = MouthStateMachine(self.settings)
        self.reminder = ReminderController()
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.capture: Any | None = None
        self.analyzer: FaceAnalyzer | None = None
        self.state = MonitorState.STOPPED
        self.error: str | None = None
        self.latest_jpeg: bytes | None = None
        self.face_detected = False
        self.ratio: float | None = None
        self.smoothed_ratio: float | None = None
        self.movement_variance = 0.0
        self.open_duration = 0.0
        self.inference_ms = 0.0
        self.processing_fps = 0.0
        self.last_frame_at = 0.0
        self.fps_history: deque[float] = deque(maxlen=30)
        self.calibration: CalibrationSession | None = None
        self.closed_reference: float | None = (
            self.settings.calibration.closed_baseline if self.settings.calibration else None
        )
        self.calibration_message = (
            "校准已加载" if self.settings.calibration else "请先完成闭嘴与轻微张嘴校准"
        )
        self.alerting = False

    def start(self, camera_index: int | None = None) -> None:
        with self.lock:
            if self.thread and self.thread.is_alive():
                return
            if camera_index is not None:
                profile = self.settings.calibration
                if profile is not None and profile.camera_index != camera_index:
                    self.settings.calibration = None
                    self.closed_reference = None
                    self.state_machine.update_settings(self.settings)
                    self.calibration_message = "摄像头已更换，请重新完成双点校准"
                self.settings.camera_index = camera_index
                self._save_settings()
            self.error = None
            self.state = MonitorState.STARTING
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._camera_loop, daemon=True, name="mouth-monitor")
            self.thread.start()

    def pause(self) -> None:
        self._shutdown(MonitorState.PAUSED)

    def stop(self) -> None:
        self._shutdown(MonitorState.STOPPED)

    def _shutdown(self, final_state: MonitorState) -> None:
        self.stop_event.set()
        thread = self.thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=3)
        with self.lock:
            self.state = final_state
            self.face_detected = False
            self.alerting = False
            self.open_duration = 0.0
            self.state_machine.reset(final_state)

    def available_cameras(self) -> list[dict[str, int | str]]:
        return scan_cameras()

    def begin_calibration(self, mode: Literal["closed", "open"]) -> None:
        with self.lock:
            if not self.thread or not self.thread.is_alive():
                raise RuntimeError("请先启动摄像头")
            if mode == "open" and self.closed_reference is None:
                raise RuntimeError("请先完成闭嘴校准")
            if mode == "closed":
                self.settings.calibration = None
                self.closed_reference = None
                self.state_machine.update_settings(self.settings)
            self.calibration = CalibrationSession(mode=mode)
            self.calibration_message = (
                "请舒适闭嘴并保持不动" if mode == "closed" else "请轻微张嘴并保持不动"
            )
            self.state = MonitorState.CALIBRATING
            self.alerting = False

    def reset_calibration(self) -> None:
        with self.lock:
            self.calibration = None
            self.closed_reference = None
            self.settings.calibration = None
            self.state_machine.update_settings(self.settings)
            self.state = MonitorState.NOT_CALIBRATED
            self.calibration_message = "校准已清除，请重新采集"
            self._save_settings()

    def update_settings(
        self,
        sustained_seconds: float,
        cooldown_seconds: float,
        movement_sensitivity: float,
        sound_enabled: bool,
    ) -> None:
        if not 1.0 <= sustained_seconds <= 60.0:
            raise ValueError("持续时间必须在 1 到 60 秒之间")
        if not 0.0 <= cooldown_seconds <= 300.0:
            raise ValueError("冷却时间必须在 0 到 300 秒之间")
        if not 0.002 <= movement_sensitivity <= 0.05:
            raise ValueError("运动阈值必须在 0.002 到 0.05 之间")
        with self.lock:
            self.settings = replace(
                self.settings,
                sustained_seconds=sustained_seconds,
                cooldown_seconds=cooldown_seconds,
                movement_sensitivity=movement_sensitivity,
                sound_enabled=sound_enabled,
            )
            self.state_machine.update_settings(self.settings)
            self._save_settings()

    def test_reminder(self) -> bool:
        return self.reminder.remind(self.settings.sound_enabled)

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            profile = self.settings.calibration
            calibration_remaining = self.calibration.remaining() if self.calibration else 0.0
            return {
                "state": self.state.value,
                "state_label": STATE_LABELS[self.state],
                "running": bool(self.thread and self.thread.is_alive()),
                "error": self.error,
                "config_warning": self.config_warning,
                "face_detected": self.face_detected,
                "ratio": self.ratio,
                "smoothed_ratio": self.smoothed_ratio,
                "movement_variance": self.movement_variance,
                "open_duration": self.open_duration,
                "cooldown_remaining": self.reminder.cooldown_remaining(self.settings.cooldown_seconds),
                "inference_ms": self.inference_ms,
                "processing_fps": self.processing_fps,
                "alerting": self.alerting,
                "calibration_mode": self.calibration.mode if self.calibration else None,
                "calibration_remaining": calibration_remaining,
                "calibration_message": self.calibration_message,
                "closed_baseline": profile.closed_baseline if profile else self.closed_reference,
                "open_baseline": profile.open_baseline if profile else None,
                "enter_threshold": profile.enter_threshold if profile else None,
                "exit_threshold": profile.exit_threshold if profile else None,
                "settings": self.settings.to_dict(),
            }

    def _save_settings(self) -> None:
        self.repository.save(self.settings)

    def _camera_loop(self) -> None:
        try:
            import cv2

            self.analyzer = FaceAnalyzer()
            self.capture = open_camera(self.settings.camera_index)
            next_analysis_at = 0.0
            while not self.stop_event.is_set():
                ok, frame = self.capture.read()
                if not ok:
                    raise RuntimeError("无法读取摄像头画面")
                frame = cv2.flip(frame, 1)
                now = time.monotonic()
                if now < next_analysis_at:
                    time.sleep(min(0.01, next_analysis_at - now))
                    continue
                next_analysis_at = now + 0.1
                started = time.perf_counter()
                observation = self.analyzer.analyze(frame, now)
                inference_ms = (time.perf_counter() - started) * 1000
                self._apply_observation(observation, now, inference_ms)
                label = STATE_LABELS[self.state]
                annotated = annotate_frame(frame, observation, label, self.alerting)
                encoded_ok, encoded = cv2.imencode(
                    ".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 78]
                )
                if encoded_ok:
                    with self.lock:
                        self.latest_jpeg = encoded.tobytes()
        except Exception as exc:
            with self.lock:
                self.error = str(exc)
                self.state = MonitorState.ERROR
                self.alerting = False
        finally:
            if self.analyzer is not None:
                self.analyzer.close()
                self.analyzer = None
            if self.capture is not None:
                self.capture.release()
                self.capture = None

    def _apply_observation(self, observation: Any, now: float, inference_ms: float) -> None:
        with self.lock:
            self.inference_ms = inference_ms
            if self.last_frame_at:
                delta = now - self.last_frame_at
                if delta > 0:
                    self.fps_history.append(1.0 / delta)
                    self.processing_fps = statistics.fmean(self.fps_history)
            self.last_frame_at = now
            self.face_detected = observation.detected
            self.ratio = observation.ratio

            if observation.ratio is None:
                result = self.state_machine.no_face()
                self._apply_result(result)
                return

            if self.calibration is not None:
                self.calibration.add(observation.ratio)
                self.state = MonitorState.CALIBRATING
                self.smoothed_ratio = observation.ratio
                if self.calibration.complete(now):
                    self._finish_calibration()
                return

            result = self.state_machine.process(observation.ratio, now)
            self._apply_result(result)
            if result.state == MonitorState.SUSTAINED_OPEN:
                self.alerting = True
                if self.reminder.can_remind(self.settings.cooldown_seconds, now):
                    self.reminder.remind(self.settings.sound_enabled, now)
            else:
                self.alerting = False

    def _apply_result(self, result: StateResult) -> None:
        self.state = result.state
        self.open_duration = result.open_duration
        self.smoothed_ratio = result.smoothed_ratio
        self.movement_variance = result.movement_variance

    def _finish_calibration(self) -> None:
        session = self.calibration
        self.calibration = None
        if session is None:
            return
        try:
            baseline = session.median()
            if session.mode == "closed":
                self.closed_reference = baseline
                self.calibration_message = "闭嘴基线完成，请继续采集轻微张嘴参考"
                self.state = MonitorState.NOT_CALIBRATED
            else:
                if self.closed_reference is None:
                    raise ValueError("请先完成闭嘴校准")
                profile = build_profile(
                    self.closed_reference,
                    baseline,
                    self.settings.camera_index,
                )
                self.settings.calibration = profile
                self.state_machine.update_settings(self.settings)
                self.state_machine.reset(MonitorState.CLOSED)
                self.calibration_message = "双点校准完成，监控已开始"
                self.state = MonitorState.CLOSED
                self._save_settings()
        except ValueError as exc:
            self.calibration_message = str(exc)
            self.state = MonitorState.NOT_CALIBRATED
