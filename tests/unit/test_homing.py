"""Homing order and direction.

Both failures here are physical, not logical. Homing Z downward drives the
spindle into the table; homing X or Y before Z retracts drags the table under
a tool that is still down. Neither produces an error message - the first
symptom is a noise.

ADR-0006.
"""

from __future__ import annotations

import pytest
from machinegen import check_machine, errors, load_machine, parse_machine, render_ini
from machinegen.emit import home_sequence
from machinegen.model import default_machine_path


@pytest.fixture
def real_machine():
    return load_machine(default_machine_path())


class TestOrder:
    def test_z_homes_first(self, real_machine):
        assert home_sequence(real_machine)["z"] == 0

    def test_everything_else_homes_after_z(self, real_machine):
        order = home_sequence(real_machine)
        for name, seq in order.items():
            if name != "z":
                assert seq > order["z"], f"{name} homes at or before Z"

    def test_sequences_are_unique(self, real_machine):
        order = home_sequence(real_machine)
        assert len(set(order.values())) == len(order)

    def test_ini_carries_the_order(self, real_machine, ini_value):
        """The generated file, not just the helper, must have Z first."""
        ini = render_ini(real_machine)
        for index, axis in enumerate(real_machine.ordered_axes):
            seq = int(ini_value(ini, f"JOINT_{index}", "HOME_SEQUENCE"))
            if axis.name == "z":
                assert seq == 0, "Z is not first in the generated INI"
            else:
                assert seq > 0

    def test_a_machine_without_z_still_numbers_from_zero(self, machine_dict):
        """XY-only machines must not end up with a gap at sequence 0."""
        machine_dict["axis"].pop("z", None)
        machine_dict["axis"]["y"] = dict(machine_dict["axis"]["x"], travel_mm=130.0)
        machine_dict["node"]["motion0"]["axes"] = ["x", "y"]
        order = home_sequence(parse_machine(machine_dict))
        assert sorted(order.values()) == [0, 1]


class TestDirection:
    def test_z_search_velocity_is_positive(self, real_machine, ini_value):
        """Negative would search downward, toward the table."""
        ini = render_ini(real_machine)
        z_index = real_machine.ordered_axes.index(real_machine.axis("z"))
        assert float(ini_value(ini, f"JOINT_{z_index}", "HOME_SEARCH_VEL")) > 0

    def test_z_latches_in_the_same_direction_as_it_searches(self, real_machine, ini_value):
        ini = render_ini(real_machine)
        z_index = real_machine.ordered_axes.index(real_machine.axis("z"))
        search = float(ini_value(ini, f"JOINT_{z_index}", "HOME_SEARCH_VEL"))
        latch = float(ini_value(ini, f"JOINT_{z_index}", "HOME_LATCH_VEL"))
        assert (search > 0) == (latch > 0)


class TestConstraint:
    def test_real_machine_passes(self, real_machine):
        found = [v for v in errors(check_machine(real_machine)) if "home" in str(v).lower()]
        assert not found
