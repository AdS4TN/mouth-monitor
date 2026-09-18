from __future__ import annotations

import json
import os
from pathlib import Path

from .models import AppSettings, CONFIG_VERSION


def default_config_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
    return base / "MouthMonitor" / "config.json"


class SettingsRepository:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_config_path()

    def load(self) -> tuple[AppSettings, str | None]:
        if not self.path.exists():
            return AppSettings(), None
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if int(data.get("version", CONFIG_VERSION)) != CONFIG_VERSION:
                return AppSettings(), "配置版本不兼容，已恢复默认设置"
            return AppSettings.from_dict(data), None
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            return AppSettings(), "配置文件损坏，已恢复默认设置"

    def save(self, settings: AppSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(settings.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)
