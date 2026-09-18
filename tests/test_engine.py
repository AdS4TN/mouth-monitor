from pathlib import Path

from mouth_monitor.engine import MonitorEngine
from mouth_monitor.models import AppSettings, CalibrationProfile
from mouth_monitor.storage import SettingsRepository


def test_switching_camera_clears_bound_calibration(tmp_path: Path) -> None:
    repository = SettingsRepository(tmp_path / "config.json")
    repository.save(
        AppSettings(
            camera_index=0,
            calibration=CalibrationProfile(0.04, 0.12, 0.076, 0.06, camera_index=0),
        )
    )
    engine = MonitorEngine(repository)
    engine._camera_loop = lambda: None

    engine.start(camera_index=1)
    engine.stop()

    saved, warning = repository.load()
    assert warning is None
    assert saved.camera_index == 1
    assert saved.calibration is None
