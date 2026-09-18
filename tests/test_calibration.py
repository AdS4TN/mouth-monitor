import pytest

from mouth_monitor.calibration import CalibrationSession, build_profile


def test_build_profile_generates_hysteresis_thresholds() -> None:
    profile = build_profile(0.04, 0.12, camera_index=2)

    assert profile.exit_threshold < profile.enter_threshold
    assert profile.closed_baseline < profile.exit_threshold
    assert profile.enter_threshold < profile.open_baseline
    assert profile.camera_index == 2


def test_build_profile_rejects_indistinguishable_samples() -> None:
    with pytest.raises(ValueError):
        build_profile(0.04, 0.045, camera_index=0)


def test_calibration_session_rejects_unstable_samples() -> None:
    session = CalibrationSession("closed")
    session.samples = [0.01, 0.08] * 6

    with pytest.raises(ValueError):
        session.median()
