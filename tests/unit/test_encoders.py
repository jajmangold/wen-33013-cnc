"""Encoder feedback: resolution arithmetic and wiring sanity.

The arithmetic here is easy to get wrong in a way that looks right. A
belt-mounted encoder's resolution comes from the PULLEY, not the ballscrew, so
reusing the screw lead gives a number that is out by the ratio between them -
and the machine would then trip following errors, or fail to trip them, for
reasons nobody can see.
"""

from __future__ import annotations

import pytest
from machinegen import MachineConfigError, check_machine, errors, load_machine, parse_machine
from machinegen.model import Encoder, default_machine_path

GT2_20T = {
    "bits": 14,
    "interface": "spi1",
    "cs": 0,
    "mount": "belt",
    "pulley_teeth": 20,
    "belt_pitch_mm": 2.0,
}


class TestResolutionArithmetic:
    def test_belt_resolution_comes_from_the_pulley(self, machine_dict):
        machine_dict["axis"]["x"]["encoder"] = dict(GT2_20T)
        axis = parse_machine(machine_dict).axis("x")
        # 2**14 counts over a 20T * 2mm = 40mm circumference
        assert axis.counts_per_mm == pytest.approx(16384 / 40)
        assert axis.counts_per_mm == pytest.approx(409.6)

    def test_motor_mount_resolution_comes_from_the_screw(self, machine_dict):
        machine_dict["axis"]["x"]["encoder"] = {
            "bits": 14, "interface": "spi1", "cs": 0, "mount": "motor",
        }
        axis = parse_machine(machine_dict).axis("x")
        assert axis.counts_per_mm == pytest.approx(16384 / 5.0)

    def test_the_two_mountings_disagree(self, machine_dict):
        """Guards against anyone 'simplifying' travel_per_rev_mm away."""
        belt = dict(machine_dict["axis"]["x"], encoder=dict(GT2_20T))
        motor = dict(
            machine_dict["axis"]["x"],
            encoder={"bits": 14, "interface": "spi1", "cs": 0, "mount": "motor"},
        )
        machine_dict["axis"]["x"] = belt
        belt_cpm = parse_machine(machine_dict).axis("x").counts_per_mm
        machine_dict["axis"]["x"] = motor
        motor_cpm = parse_machine(machine_dict).axis("x").counts_per_mm
        assert belt_cpm != motor_cpm

    def test_smaller_pulley_resolves_finer(self, machine_dict):
        fine = dict(GT2_20T, pulley_teeth=12)
        machine_dict["axis"]["x"]["encoder"] = fine
        axis = parse_machine(machine_dict).axis("x")
        assert axis.encoder_resolution_mm < 1 / 409.6

    def test_counts_per_rev_is_two_to_the_bits(self):
        assert Encoder(bits=14, interface="spi1", cs=0).counts_per_rev == 16384
        assert Encoder(bits=12, interface="spi1", cs=0).counts_per_rev == 4096


class TestValidation:
    def test_belt_mount_requires_pulley_geometry(self, machine_dict):
        machine_dict["axis"]["x"]["encoder"] = {
            "bits": 14, "interface": "spi1", "cs": 0, "mount": "belt",
        }
        with pytest.raises(MachineConfigError, match="needs pulley_teeth"):
            parse_machine(machine_dict)

    def test_spi0_is_refused(self, machine_dict):
        """SPI0 is the slave link to the Pi; encoders cannot share it."""
        machine_dict["axis"]["x"]["encoder"] = dict(GT2_20T, interface="spi0")
        with pytest.raises(MachineConfigError, match="spi0 is the link to the Pi"):
            parse_machine(machine_dict)

    def test_absurd_bit_depth_is_refused(self, machine_dict):
        machine_dict["axis"]["x"]["encoder"] = dict(GT2_20T, bits=32)
        with pytest.raises(MachineConfigError, match="bits must be 8..20"):
            parse_machine(machine_dict)


class TestConstraints:
    def test_shared_chip_select_is_an_error(self, machine_dict):
        machine_dict["axis"]["y"] = dict(machine_dict["axis"]["x"], travel_mm=130.0)
        machine_dict["axis"]["x"]["encoder"] = dict(GT2_20T, cs=0)
        machine_dict["axis"]["y"]["encoder"] = dict(GT2_20T, cs=0)   # same CS
        machine_dict["node"]["motion0"]["axes"] = ["x", "y"]
        found = errors(check_machine(parse_machine(machine_dict)))
        assert any("collides with" in str(v) for v in found)

    def test_distinct_chip_selects_are_fine(self, machine_dict):
        machine_dict["axis"]["y"] = dict(machine_dict["axis"]["x"], travel_mm=130.0)
        machine_dict["axis"]["x"]["encoder"] = dict(GT2_20T, cs=0)
        machine_dict["axis"]["y"]["encoder"] = dict(GT2_20T, cs=1)
        machine_dict["node"]["motion0"]["axes"] = ["x", "y"]
        assert not errors(check_machine(parse_machine(machine_dict)))

    def test_coarser_than_a_microstep_only_warns(self, machine_dict):
        """Expected for a belt encoder - informative, not fatal.

        At 32x (the real machine) a microstep is 0.78 um while a 20T GT2 belt
        encoder resolves 2.44 um, so the encoder is the coarser of the two.
        At 8x it is the other way round, which is why this sets 32x rather
        than relying on the fixture.
        """
        machine_dict["axis"]["x"]["microsteps"] = 32
        machine_dict["axis"]["x"]["encoder"] = dict(GT2_20T)
        violations = check_machine(parse_machine(machine_dict))
        assert not errors(violations)
        assert any("coarser than the" in str(v) for v in violations)

    def test_finer_than_a_microstep_does_not_warn(self, machine_dict):
        machine_dict["axis"]["x"]["microsteps"] = 8      # 3.13 um microstep
        machine_dict["axis"]["x"]["encoder"] = dict(GT2_20T)   # 2.44 um
        violations = check_machine(parse_machine(machine_dict))
        assert not any("coarser than the" in str(v) for v in violations)

    def test_uselessly_coarse_feedback_is_an_error(self, machine_dict):
        # A 60T pulley: 16384 counts over 120mm = 7.3um... still fine. Drop to
        # 8 bits on a big pulley to make it genuinely useless.
        machine_dict["axis"]["x"]["encoder"] = dict(GT2_20T, bits=8, pulley_teeth=60)
        found = errors(check_machine(parse_machine(machine_dict)))
        assert any("too coarse" in str(v) for v in found)

    def test_open_loop_axis_warns(self, machine_dict):
        machine_dict["axis"]["x"].pop("encoder", None)
        violations = check_machine(parse_machine(machine_dict))
        assert any("open loop" in str(v) for v in violations)


class TestGeneratedOutput:
    def test_ferror_clears_the_encoder_resolution(self):
        from machinegen import render_ini

        from tests.unit.test_emit import ini_value  # noqa: PLC0415

        machine = load_machine(default_machine_path())
        ini = render_ini(machine)
        axis = machine.axis("x")
        min_ferror = float(ini_value(ini, "JOINT_0", "MIN_FERROR"))
        assert min_ferror > axis.encoder_resolution_mm * 5, (
            "MIN_FERROR must sit well clear of encoder resolution or noise trips it"
        )

    def test_firmware_header_carries_counts_per_mm(self):
        from machinegen import render_firmware_header

        machine = load_machine(default_machine_path())
        node = machine.motion_nodes[0]
        header = render_firmware_header(machine, node)
        assert "X_ENCODER_COUNTS_PER_MM 409.600000f" in header
        assert "X_HAS_ENCODER 1" in header


class TestRealMachine:
    @pytest.mark.parametrize("axis_name", ["x", "y", "z"])
    def test_every_axis_is_closed_loop(self, axis_name):
        machine = load_machine(default_machine_path())
        assert machine.axis(axis_name).is_closed_loop

    def test_no_encoder_errors(self):
        machine = load_machine(default_machine_path())
        found = [v for v in errors(check_machine(machine)) if "encoder" in str(v)]
        assert not found
