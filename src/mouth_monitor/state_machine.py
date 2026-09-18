from __future__ import annotations

import statistics
from collections import deque

from .models import AppSettings, MonitorState, StateResult


class MouthStateMachine:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self._history: deque[tuple[float, float]] = deque(maxlen=80)
        self._state = MonitorState.NOT_CALIBRATED
        self._open_started_at: float | None = None

    def update_settings(self, settings: AppSettings) -> None:
        self.settings = settings
        if settings.calibration is None:
            self.reset(MonitorState.NOT_CALIBRATED)

    def reset(self, state: MonitorState = MonitorState.STOPPED) -> None:
        self._history.clear()
        self._open_started_at = None
        self._state = state

    def no_face(self) -> StateResult:
        self._history.clear()
        self._open_started_at = None
        self._state = MonitorState.NO_FACE
        return StateResult(self._state, 0.0, None, 0.0)

    def process(self, ratio: float, timestamp: float) -> StateResult:
        profile = self.settings.calibration
        if profile is None:
            self._state = MonitorState.NOT_CALIBRATED
            return StateResult(self._state, 0.0, ratio, 0.0)

        self._history.append((timestamp, ratio))
        recent = [value for sample_time, value in self._history if timestamp - sample_time <= 1.0]
        smoothed = statistics.median(recent[-5:])
        variance = statistics.pstdev(recent) if len(recent) >= 3 else 0.0

        if variance >= self.settings.movement_sensitivity:
            self._state = MonitorState.MOUTH_ACTIVE
            self._open_started_at = None
            return StateResult(self._state, 0.0, smoothed, variance)

        if ratio <= profile.exit_threshold:
            self._state = MonitorState.CLOSED
            self._open_started_at = None
            return StateResult(self._state, 0.0, smoothed, variance)

        if smoothed >= profile.enter_threshold:
            if self._open_started_at is None:
                self._open_started_at = timestamp
            duration = timestamp - self._open_started_at
            self._state = (
                MonitorState.SUSTAINED_OPEN
                if duration >= self.settings.sustained_seconds
                else MonitorState.OPEN_CANDIDATE
            )
            return StateResult(self._state, duration, smoothed, variance)

        if self._open_started_at is not None:
            duration = timestamp - self._open_started_at
            self._state = MonitorState.OPEN_CANDIDATE
            return StateResult(self._state, duration, smoothed, variance)

        self._state = MonitorState.CLOSED
        return StateResult(self._state, 0.0, smoothed, variance)
