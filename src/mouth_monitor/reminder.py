from __future__ import annotations

import time


class ReminderController:
    def __init__(self) -> None:
        self.last_reminded_at: float | None = None
        self.last_error: str | None = None

    def cooldown_remaining(self, cooldown_seconds: float, now: float | None = None) -> float:
        if self.last_reminded_at is None:
            return 0.0
        current = time.monotonic() if now is None else now
        return max(0.0, cooldown_seconds - (current - self.last_reminded_at))

    def can_remind(self, cooldown_seconds: float, now: float | None = None) -> bool:
        return self.cooldown_remaining(cooldown_seconds, now) <= 0

    def remind(self, enabled: bool = True, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        self.last_reminded_at = current
        self.last_error = None
        if not enabled:
            return False
        try:
            import winsound

            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            return True
        except (ImportError, RuntimeError, OSError) as exc:
            self.last_error = str(exc)
            return False

    def reset(self) -> None:
        self.last_reminded_at = None
        self.last_error = None
