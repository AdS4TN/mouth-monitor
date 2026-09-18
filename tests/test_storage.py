from pathlib import Path

from mouth_monitor.models import AppSettings, CalibrationProfile
from mouth_monitor.storage import SettingsRepository


def test_settings_round_trip(tmp_path: Path) -> None:
    repository = SettingsRepository(tmp_path / "config.json")
    expected = AppSettings(
        camera_index=2,
        sustained_seconds=9,
        cooldown_seconds=45,
        calibration=CalibrationProfile(0.03, 0.1, 0.0615, 0.0475, 2),
    )

    repository.save(expected)
    actual, warning = repository.load()

    assert warning is None
    assert actual == expected


def test_invalid_config_falls_back_to_defaults(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("not-json", encoding="utf-8")

    settings, warning = SettingsRepository(path).load()

    assert settings == AppSettings()
    assert warning is not None
