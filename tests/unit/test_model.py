"""The machine model: derived arithmetic and validation.

The arithmetic tests are not ceremony. `steps_per_mm` is the number that
decides whether the machine cuts a 10 mm slot or a 25 mm one, and it is
derived in exactly one place so that it can be pinned down here.
"""

from __future__ import annotations

import pytest
from machinegen import (
    MachineConfigError,
    default_machine_path,
    load_machine,
    parse_machine,
)


class TestDerivedScale:
    def test_steps_per_mm_is_microsteps_over_lead(self, machine):
        # 200 full steps * 8 microsteps = 1600 per rev, over a 5 mm lead.
        assert machine.axis("x").steps_per_mm == pytest.approx(320.0)

    def test_steps_per_rev(self, machine):
        assert machine.axis("x").steps_per_rev == 1600

    def test_resolution_is_the_reciprocal(self, machine):
        axis = machine.axis("x")
        assert axis.resolution_mm == pytest.approx(1 / 320.0)
        assert axis.resolution_mm * axis.steps_per_mm == pytest.approx(1.0)

    def test_max_step_rate_follows_velocity(self, machine):
        axis = machine.axis("x")
        assert axis.max_step_rate_hz == pytest.approx(41.67 * 320.0)

    @pytest.mark.parametrize(
        ("microsteps", "pitch", "expected"),
        [
            (1, 5.0, 40.0),
            (8, 5.0, 320.0),
            (16, 5.0, 640.0),
            (8, 10.0, 160.0),
            (32, 2.0, 3200.0),
        ],
    )
    def test_scale_table(self, machine_dict, microsteps, pitch, expected):
        machine_dict["axis"]["x"]["microsteps"] = microsteps
        machine_dict["axis"]["x"]["screw_pitch_mm"] = pitch
        assert parse_machine(machine_dict).axis("x").steps_per_mm == pytest.approx(expected)


class TestSoftLimits:
    def test_margins_inset_both_ends(self, machine):
        axis = machine.axis("x")
        assert axis.soft_min_mm == pytest.approx(2.0)
        assert axis.soft_max_mm == pytest.approx(298.0)

    def test_margins_cannot_eat_the_travel(self, machine_dict):
        machine_dict["axis"]["x"]["soft_limit_margin_mm"] = 150.0
        with pytest.raises(MachineConfigError, match="consume the entire"):
            parse_machine(machine_dict)


class TestValidation:
    def test_rejects_microstep_the_driver_cannot_do(self, machine_dict):
        machine_dict["axis"]["x"]["microsteps"] = 7
        with pytest.raises(MachineConfigError, match="not a DM542T setting"):
            parse_machine(machine_dict)

    def test_rejects_zero_lead(self, machine_dict):
        machine_dict["axis"]["x"]["screw_pitch_mm"] = 0.0
        with pytest.raises(MachineConfigError, match="screw_pitch_mm"):
            parse_machine(machine_dict)

    def test_rejects_negative_velocity(self, machine_dict):
        machine_dict["axis"]["x"]["max_velocity_mm_s"] = -1.0
        with pytest.raises(MachineConfigError, match="max_velocity_mm_s"):
            parse_machine(machine_dict)

    def test_rejects_bad_home_direction(self, machine_dict):
        machine_dict["axis"]["x"]["home_direction"] = 0
        with pytest.raises(MachineConfigError, match="home_direction"):
            parse_machine(machine_dict)

    def test_rejects_current_outside_drive_range(self, machine_dict):
        machine_dict["driver"]["current_a"] = 9.0
        with pytest.raises(MachineConfigError, match="outside drive range"):
            parse_machine(machine_dict)

    def test_rejects_unknown_axis_name(self, machine_dict):
        machine_dict["axis"]["w"] = dict(machine_dict["axis"]["x"])
        with pytest.raises(MachineConfigError, match="unknown axis"):
            parse_machine(machine_dict)

    def test_rejects_missing_section(self, machine_dict):
        del machine_dict["driver"]
        with pytest.raises(MachineConfigError, match=r"\[driver\]"):
            parse_machine(machine_dict)

    def test_missing_file_is_a_config_error(self, tmp_path):
        with pytest.raises(MachineConfigError, match="not found"):
            load_machine(tmp_path / "nope.toml")


class TestRealMachine:
    """The actual WEN 33013 description must stay loadable and sane."""

    def test_loads(self):
        machine = load_machine(default_machine_path())
        assert machine.base_machine == "WEN 33013"

    def test_has_three_axes_in_xyz_order(self):
        machine = load_machine(default_machine_path())
        assert [a.name for a in machine.ordered_axes] == ["x", "y", "z"]

    def test_travels_match_the_stock_machine(self):
        # WEN publishes X 11-13/16in, Y 5-1/8in, Z 7in. Our travels must not
        # exceed the table the conversion inherits.
        machine = load_machine(default_machine_path())
        assert machine.axis("x").travel_mm <= 300.1
        assert machine.axis("y").travel_mm <= 130.3
        assert machine.axis("z").travel_mm <= 177.9

    def test_z_homes_up(self):
        # Z homing downward drives the spindle into the table.
        assert load_machine(default_machine_path()).axis("z").home_direction == 1
