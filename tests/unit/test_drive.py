"""The drive train between motor shaft and screw.

A belt reduction multiplies `steps_per_mm`. Getting it wrong does not raise:
the machine simply cuts everything at the wrong size, which is the failure
mode AGENTS.md section 2 exists to prevent. So the reduction is part of the
model, derived in one place, and pinned here.
"""

from __future__ import annotations

import pytest
from machinegen import MachineConfigError, load_machine, parse_machine
from machinegen.model import default_machine_path


@pytest.fixture
def real_machine():
    return load_machine(default_machine_path())


def _belt(machine_dict, motor_teeth=20, screw_teeth=40, **kw):
    drive = {
        "kind": "belt",
        "motor_teeth": motor_teeth,
        "screw_teeth": screw_teeth,
        "belt_pitch_mm": 2.0,
    }
    drive.update(kw)
    machine_dict["axis"]["x"]["drive"] = drive
    return machine_dict


class TestReduction:
    def test_an_axis_with_no_drive_declared_is_direct(self, machine):
        assert machine.axis("x").drive.reduction == pytest.approx(1.0)

    def test_belt_reduction_is_screw_teeth_over_motor_teeth(self, machine_dict):
        axis = parse_machine(_belt(machine_dict)).axis("x")
        assert axis.drive.reduction == pytest.approx(2.0)

    def test_reduction_multiplies_steps_per_mm(self, machine_dict):
        direct = parse_machine(machine_dict).axis("x").steps_per_mm
        belted = parse_machine(_belt(machine_dict)).axis("x").steps_per_mm
        assert belted == pytest.approx(2.0 * direct)

    def test_a_step_up_divides_steps_per_mm(self, machine_dict):
        """screw_teeth < motor_teeth is legal - it trades torque for speed."""
        axis = parse_machine(_belt(machine_dict, motor_teeth=40, screw_teeth=20)).axis("x")
        assert axis.drive.reduction == pytest.approx(0.5)

    @pytest.mark.parametrize(
        ("motor_teeth", "screw_teeth", "microsteps", "pitch", "expected"),
        [
            (20, 40, 32, 2.0, 6400.0),
            (20, 40, 8, 5.0, 640.0),
            (16, 48, 8, 5.0, 960.0),
            (20, 20, 8, 5.0, 320.0),
        ],
    )
    def test_scale_table(
        self, machine_dict, motor_teeth, screw_teeth, microsteps, pitch, expected
    ):
        machine_dict["axis"]["x"]["microsteps"] = microsteps
        machine_dict["axis"]["x"]["screw_pitch_mm"] = pitch
        axis = parse_machine(_belt(machine_dict, motor_teeth, screw_teeth)).axis("x")
        assert axis.steps_per_mm == pytest.approx(expected)


class TestTravelPerMotorRev:
    def test_belt_reduction_slows_the_screw(self, machine_dict):
        """2:1 means one motor turn is half a screw turn, so half a lead."""
        axis = parse_machine(_belt(machine_dict)).axis("x")
        assert axis.travel_per_motor_rev_mm == pytest.approx(2.5)


class TestValidation:
    def test_belt_drive_requires_both_tooth_counts(self, machine_dict):
        machine_dict["axis"]["x"]["drive"] = {"kind": "belt", "motor_teeth": 20}
        with pytest.raises(MachineConfigError, match="screw_teeth"):
            parse_machine(machine_dict)

    def test_zero_teeth_is_rejected(self, machine_dict):
        with pytest.raises(MachineConfigError, match="teeth"):
            parse_machine(_belt(machine_dict, motor_teeth=0))

    def test_unknown_drive_kind_is_rejected(self, machine_dict):
        machine_dict["axis"]["x"]["drive"] = {"kind": "chain"}
        with pytest.raises(MachineConfigError, match="chain"):
            parse_machine(machine_dict)

    def test_a_direct_drive_may_not_claim_teeth(self, machine_dict):
        """Teeth on a direct drive means someone half-edited the TOML."""
        machine_dict["axis"]["x"]["drive"] = {"kind": "direct", "motor_teeth": 20}
        with pytest.raises(MachineConfigError, match="direct"):
            parse_machine(machine_dict)


class TestRealMachine:
    def test_x_is_belted_one_to_one(self, real_machine):
        """1:1 since 2026-11-20, when the lead turned out to be 1.5875.

        The 2:1 was chosen against an assumed 2.0 mm lead. At the real lead
        the screw is already reduction enough - 300 N at the table is 0.35 Nm
        at the screw - and the gearing only halved an axis that is slow to
        start with. This asserts the decision, not an arbitrary number: if
        someone puts a 20T back on the motor, the INI and the firmware both
        move and nothing else would notice.
        """
        assert real_machine.axis("x").drive.reduction == pytest.approx(1.0)

    def test_x_pulleys_match_the_cad(self, real_machine):
        """hardware/mechanical/x-end builds around these two tooth counts."""
        drive = real_machine.axis("x").drive
        assert (drive.motor_teeth, drive.screw_teeth) == (40, 40)

    def test_x_scale_follows_the_measured_lead(self, real_machine):
        """2016 steps/mm, and the arithmetic that gets there.

        Guards two numbers that were each wrong by a lot within the same day:
        the lead (guessed 2.0, documented 1.5875) and the reduction (2:1,
        now 1:1). Both feed the same product, so a mistake in either is
        invisible in the output alone.
        """
        x = real_machine.axis("x")
        assert x.screw_pitch_mm == pytest.approx(1.5875)
        assert x.steps_per_mm == pytest.approx(200 * 16 * 1.0 / 1.5875)


class TestCadAgreesWithTheModel:
    """The pulleys that get cut must be the pulleys the scale assumes.

    `hardware/mechanical/x-drive/params.py` reads the machine model rather
    than restating it. This asserts that it really does - a params.py that
    quietly hard-coded 20 and 40 would pass every other test in this file
    while the metal and the INI drifted apart.
    """

    @staticmethod
    def _cad_params():
        import importlib.util
        from pathlib import Path

        path = (Path(__file__).resolve().parents[2]
                / "hardware" / "mechanical" / "x-drive" / "params.py")
        spec = importlib.util.spec_from_file_location("x_drive_params", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_tooth_counts_come_from_the_model(self, real_machine):
        cad = self._cad_params()
        drive = real_machine.axis("x").drive
        assert (drive.motor_teeth, drive.screw_teeth) == (cad.MOTOR_TEETH, cad.TEETH)

    def test_belt_width_and_pitch_come_from_the_model(self, real_machine):
        cad = self._cad_params()
        drive = real_machine.axis("x").drive
        assert (drive.belt_pitch_mm, drive.belt_width_mm) == (cad.PITCH, cad.BELT_W)

    def test_the_toothed_seat_is_wider_than_the_belt(self):
        """A seat narrower than the belt throws it. Cheap, and it has happened."""
        cad = self._cad_params()
        assert cad.SEAT_W > cad.BELT_W
