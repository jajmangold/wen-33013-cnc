"""Physical constraints.

Every ERROR case here corresponds to a way the machine can hurt itself or cut
the wrong shape without complaining. The DM542T cases matter most: when a
step/dir driver is pushed past its timing limits it does not report an error,
it just silently drops pulses, and the axis loses position mid-cut.
"""

from __future__ import annotations

import pytest
from machinegen import Severity, check_machine, errors, load_machine, parse_machine
from machinegen.model import default_machine_path


def _messages(violations) -> str:
    return "\n".join(str(v) for v in violations)


class TestStepRateCeiling:
    def test_within_the_ceiling_is_clean(self, machine):
        assert not errors(check_machine(machine))

    def test_exceeding_driver_max_is_an_error(self, machine_dict):
        # 320 steps/mm * 700 mm/s = 224 kHz, past the DM542T's 200 kHz.
        machine_dict["axis"]["x"]["max_velocity_mm_s"] = 700.0
        found = errors(check_machine(parse_machine(machine_dict)))
        assert found, "a step rate above the driver ceiling must be an error"
        assert "tops out" in _messages(found)

    def test_error_names_the_velocity_that_would_fit(self, machine_dict):
        machine_dict["axis"]["x"]["max_velocity_mm_s"] = 700.0
        found = errors(check_machine(parse_machine(machine_dict)))
        assert "625.00 mm/s" in _messages(found)

    def test_close_to_the_ceiling_warns(self, machine_dict):
        # 0.85 * 200kHz / 320 steps/mm = 531 mm/s
        machine_dict["axis"]["x"]["max_velocity_mm_s"] = 531.0
        violations = check_machine(parse_machine(machine_dict))
        assert not errors(violations)
        assert any(v.severity is Severity.WARNING for v in violations)

    def test_more_microsteps_can_push_past_the_ceiling(self, machine_dict):
        """The trap: raising microsteps for resolution raises step rate too."""
        machine_dict["axis"]["x"]["microsteps"] = 128      # 5120 steps/mm
        machine_dict["axis"]["x"]["max_velocity_mm_s"] = 41.67
        found = errors(check_machine(parse_machine(machine_dict)))
        assert found, "128 microsteps at 41.67 mm/s needs 213 kHz"


class TestPulseWidth:
    def test_pulse_width_floor_is_enforced(self, machine_dict):
        # Pretend a driver that needs an absurdly long pulse: at 13 kHz a 50%
        # duty pulse is 37.5 us, so a 50 us minimum cannot be met.
        machine_dict["driver"]["min_pulse_us"] = 50.0
        machine_dict["axis"]["x"]["max_velocity_mm_s"] = 41.67
        found = errors(check_machine(parse_machine(machine_dict)))
        assert any("below the" in str(v) for v in found)

    def test_real_driver_timing_passes(self, machine):
        assert not any("min_pulse" in str(v) for v in check_machine(machine))


class TestSoftLimits:
    def test_zero_margin_warns(self, machine_dict):
        machine_dict["axis"]["x"]["soft_limit_margin_mm"] = 0.0
        violations = check_machine(parse_machine(machine_dict))
        assert any("no soft limit margin" in str(v) for v in violations)


class TestAccel:
    def test_accel_distance_over_half_travel_warns(self, machine_dict):
        machine_dict["axis"]["x"]["max_velocity_mm_s"] = 100.0
        machine_dict["axis"]["x"]["max_accel_mm_s2"] = 10.0   # needs 500 mm
        violations = check_machine(parse_machine(machine_dict))
        assert any("to reach max velocity" in str(v) for v in violations)


class TestServoThread:
    def test_burst_larger_than_the_protocol_field_is_an_error(self, machine_dict):
        """A slow servo thread plus fine microstepping overflows the burst field.

        Note this cannot happen at 1 kHz: the DM542T's own 200 kHz ceiling caps
        the burst at 200 steps/cycle, below the 255 the protocol encodes. It
        only becomes reachable on a slower servo thread, which is why the test
        sets one explicitly rather than relying on the fixture.
        """
        machine_dict["control"]["servo_period_ns"] = 5_000_000   # 200 Hz
        machine_dict["axis"]["x"]["microsteps"] = 128            # 5120 steps/mm
        machine_dict["axis"]["x"]["max_velocity_mm_s"] = 38.0    # 194.6 kHz
        found = errors(check_machine(parse_machine(machine_dict)))
        assert any("steps per servo cycle" in str(v) for v in found)

    def test_unreachable_at_1khz_with_this_driver(self, machine_dict):
        """Guards the claim above: at 1 kHz the driver ceiling binds first."""
        machine_dict["axis"]["x"]["microsteps"] = 128
        machine_dict["axis"]["x"]["max_velocity_mm_s"] = 39.0    # 199.7 kHz
        found = check_machine(parse_machine(machine_dict))
        assert not any("steps per servo cycle" in str(v) for v in found)


class TestRealMachine:
    def test_the_wen_has_no_constraint_errors(self):
        """The committed machine description must always be buildable."""
        machine = load_machine(default_machine_path())
        found = errors(check_machine(machine))
        assert not found, f"machine/wen33013.toml has errors:\n{_messages(found)}"

    @pytest.mark.parametrize("axis_name", ["x", "y", "z"])
    def test_every_axis_stays_under_the_driver_ceiling(self, axis_name):
        machine = load_machine(default_machine_path())
        axis = machine.axis(axis_name)
        assert axis.max_step_rate_hz <= machine.driver.max_step_rate_hz
