from mouth_monitor.models import AppSettings, CalibrationProfile, MonitorState
from mouth_monitor.state_machine import MouthStateMachine


def settings() -> AppSettings:
    return AppSettings(
        sustained_seconds=2.0,
        movement_sensitivity=0.02,
        calibration=CalibrationProfile(
            closed_baseline=0.04,
            open_baseline=0.12,
            enter_threshold=0.076,
            exit_threshold=0.06,
            camera_index=0,
        ),
    )


def test_sustained_open_transition() -> None:
    machine = MouthStateMachine(settings())

    assert machine.process(0.1, 0.0).state == MonitorState.OPEN_CANDIDATE
    assert machine.process(0.1, 1.0).state == MonitorState.OPEN_CANDIDATE
    assert machine.process(0.1, 2.1).state == MonitorState.SUSTAINED_OPEN


def test_closing_resets_open_duration() -> None:
    machine = MouthStateMachine(settings())
    machine.process(0.1, 0.0)
    machine.process(0.1, 1.0)

    result = machine.process(0.04, 1.5)

    assert result.state == MonitorState.CLOSED
    assert result.open_duration == 0.0


def test_mouth_activity_avoids_open_timer() -> None:
    machine = MouthStateMachine(settings())
    machine.process(0.04, 0.0)
    machine.process(0.12, 0.1)
    result = machine.process(0.04, 0.2)

    assert result.state == MonitorState.MOUTH_ACTIVE
