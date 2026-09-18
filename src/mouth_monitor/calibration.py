from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from typing import Literal

from .models import CalibrationProfile


CalibrationMode = Literal["closed", "open"]


@dataclass(slots=True)
class CalibrationSession:
    mode: CalibrationMode
    duration_seconds: float = 3.0
    started_at: float = field(default_factory=time.monotonic)
    samples: list[float] = field(default_factory=list)

    @property
    def deadline(self) -> float:
        return self.started_at + self.duration_seconds

    def add(self, value: float) -> None:
        self.samples.append(value)

    def remaining(self, now: float | None = None) -> float:
        current = time.monotonic() if now is None else now
        return max(0.0, self.deadline - current)

    def complete(self, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        return current >= self.deadline

    def median(self, minimum_samples: int = 10, max_stddev: float = 0.025) -> float:
        if len(self.samples) < minimum_samples:
            raise ValueError("有效样本不足，请保持面部可见后重试")
        if statistics.pstdev(self.samples) > max_stddev:
            raise ValueError("校准期间波动过大，请保持姿势稳定后重试")
        return statistics.median(self.samples)


def build_profile(closed: float, opened: float, camera_index: int) -> CalibrationProfile:
    if opened <= closed + 0.008:
        raise ValueError("张嘴参考与闭嘴基线太接近，请重新采集")
    gap = opened - closed
    return CalibrationProfile(
        closed_baseline=closed,
        open_baseline=opened,
        enter_threshold=closed + gap * 0.45,
        exit_threshold=closed + gap * 0.25,
        camera_index=camera_index,
    )
