"""Node topology: which RP2040 is allowed to do what.

This file exists because the cost of getting it wrong is not a failed build,
it is a machine that keeps moving when it should have stopped. The rule being
defended: anything realtime or safety-related lives on SPI; USB is for the
screen and other things that may stutter harmlessly.
"""

from __future__ import annotations

import pytest
from machinegen import MachineConfigError, check_machine, errors, load_machine, parse_machine
from machinegen.model import default_machine_path


def _messages(violations) -> str:
    return "\n".join(str(v) for v in violations)


class TestTransportRules:
    def test_motion_over_usb_is_rejected(self, machine_dict):
        machine_dict["node"]["motion0"]["transport"] = "usb"
        del machine_dict["node"]["motion0"]["spi_cs"]
        found = errors(check_machine(parse_machine(machine_dict)))
        assert any("cannot run over usb" in str(v) for v in found)

    def test_io_over_usb_is_rejected(self, machine_dict):
        machine_dict["node"]["io1"] = {"transport": "usb", "role": "io"}
        found = errors(check_machine(parse_machine(machine_dict)))
        assert any("node.io1" in str(v) and "cannot run over usb" in str(v) for v in found)

    def test_hmi_over_usb_is_fine(self, machine):
        """The screen is explicitly allowed on USB - it is not in the stop path."""
        found = errors(check_machine(machine))
        assert not any("pendant" in str(v) for v in found)

    def test_safety_inputs_over_usb_are_rejected(self, machine_dict):
        machine_dict["node"]["pendant"]["safety_inputs"] = True
        found = errors(check_machine(parse_machine(machine_dict)))
        assert any("safety inputs cannot run" in str(v) for v in found)

    def test_usb_node_without_a_serial_warns(self, machine_dict):
        machine_dict["node"]["pendant"]["usb_serial"] = "TBD"
        violations = check_machine(parse_machine(machine_dict))
        assert any("no USB serial recorded" in str(v) for v in violations)


class TestStructuralValidation:
    def test_spi_node_needs_a_chip_select(self, machine_dict):
        del machine_dict["node"]["motion0"]["spi_cs"]
        with pytest.raises(MachineConfigError, match="needs spi_cs"):
            parse_machine(machine_dict)

    def test_usb_node_must_not_declare_chip_select(self, machine_dict):
        machine_dict["node"]["pendant"]["spi_cs"] = 1
        with pytest.raises(MachineConfigError, match="must not declare spi_cs"):
            parse_machine(machine_dict)

    def test_non_motion_node_cannot_own_axes(self, machine_dict):
        machine_dict["node"]["pendant"]["axes"] = ["x"]
        with pytest.raises(MachineConfigError, match="must not own axes"):
            parse_machine(machine_dict)

    def test_motion_node_must_own_something(self, machine_dict):
        machine_dict["node"]["motion0"]["axes"] = []
        with pytest.raises(MachineConfigError, match="must own at least one axis"):
            parse_machine(machine_dict)


class TestAxisOwnership:
    def test_unowned_axis_is_an_error(self, machine_dict):
        machine_dict["node"]["motion0"]["axes"] = []
        machine_dict["node"]["motion0"]["role"] = "io"
        found = errors(check_machine(parse_machine(machine_dict)))
        assert any("no node owns this axis" in str(v) for v in found)

    def test_axis_claimed_twice_is_an_error(self, machine_dict):
        machine_dict["node"]["motion1"] = {
            "transport": "spi",
            "role": "motion",
            "spi_cs": 1,
            "axes": ["x"],
        }
        found = errors(check_machine(parse_machine(machine_dict)))
        assert any("claimed by multiple nodes" in str(v) for v in found)

    def test_owning_an_undefined_axis_is_an_error(self, machine_dict):
        machine_dict["node"]["motion0"]["axes"] = ["x", "z"]
        found = errors(check_machine(parse_machine(machine_dict)))
        assert any("undefined axis" in str(v) for v in found)

    def test_duplicate_chip_select_is_an_error(self, machine_dict):
        machine_dict["node"]["motion1"] = {
            "transport": "spi",
            "role": "motion",
            "spi_cs": 0,
            "axes": [],
        }
        machine_dict["node"]["motion1"]["axes"] = ["x"]
        found = errors(check_machine(parse_machine(machine_dict)))
        assert any("already used by node" in str(v) for v in found)


class TestMultiNodeSplit:
    """Splitting axes across boards must keep global joint numbering."""

    def test_axes_can_be_split_across_two_spi_nodes(self, machine_dict):
        machine_dict["axis"]["y"] = dict(machine_dict["axis"]["x"], travel_mm=130.0)
        machine_dict["node"]["motion0"]["axes"] = ["x"]
        machine_dict["node"]["motion1"] = {
            "transport": "spi",
            "role": "motion",
            "spi_cs": 1,
            "axes": ["y"],
        }
        machine = parse_machine(machine_dict)
        assert not errors(check_machine(machine))
        assert machine.node_owning("x").name == "motion0"
        assert machine.node_owning("y").name == "motion1"


class TestRealMachine:
    def test_topology_is_valid(self):
        machine = load_machine(default_machine_path())
        found = errors(check_machine(machine))
        assert not found, _messages(found)

    def test_every_axis_has_exactly_one_owner(self):
        machine = load_machine(default_machine_path())
        for axis in machine.ordered_axes:
            assert machine.node_owning(axis.name) is not None

    def test_the_screen_is_not_on_the_spi_path(self):
        machine = load_machine(default_machine_path())
        assert machine.node("pendant").transport == "usb"
        assert not machine.node("pendant").is_realtime
