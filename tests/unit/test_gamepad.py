"""Gamepad safety configuration.

A stick is a proportional motion command with no detent and no spring-loaded
honesty about whether anyone is holding it. On a mill that is fine only if
three things are true, and all three are asserted here rather than left to a
HAL file nobody re-reads:

  - a deadman must be held for motion to happen at all
  - losing the pad must stop motion, not freeze the last command
  - a worn stick's resting drift must fall inside the deadzone

See docs/ui/README.md section 3 and ADR-0008.
"""

from __future__ import annotations

import tomllib

import pytest
from machinegen.model import default_machine_path


@pytest.fixture
def gamepad() -> dict:
    with default_machine_path().open("rb") as fh:
        return tomllib.load(fh)["input"]["gamepad"]


class TestDeadman:
    def test_a_deadman_is_declared(self, gamepad):
        assert gamepad.get("deadman"), (
            "a gamepad without a deadman can command motion from a dropped "
            "controller"
        )

    def test_watchdog_is_short_enough_to_matter(self, gamepad):
        """A wireless pad that dies mid-jog leaves its sticks deflected.

        At a 41.67 mm/s rapid, 150 ms of unnoticed motion is ~6 mm. Anything
        approaching a second is far enough to break a cutter.
        """
        ms = gamepad["watchdog_ms"]
        assert 0 < ms <= 250, f"watchdog_ms={ms} is too long to stop a runaway jog"

    def test_watchdog_travel_is_bounded(self, gamepad):
        """State the consequence in millimetres, not milliseconds."""
        from machinegen import load_machine

        machine = load_machine(default_machine_path())
        fastest = max(a.max_velocity_mm_s for a in machine.ordered_axes)
        travel_mm = fastest * gamepad["watchdog_ms"] / 1000.0
        assert travel_mm < 10.0, (
            f"a lost gamepad could travel {travel_mm:.1f} mm before the "
            f"watchdog fires"
        )


class TestDeadzone:
    def test_deadzone_is_present_and_sane(self, gamepad):
        dz = gamepad["deadzone"]
        assert 0.0 < dz < 0.5, f"deadzone {dz} is not a usable fraction"

    def test_deadzone_leaves_usable_range(self, gamepad):
        """Too large a deadzone makes slow jogging impossible."""
        assert gamepad["deadzone"] <= 0.25


class TestNoEstopOnThePad:
    def test_no_button_is_mapped_to_estop(self, gamepad):
        """E-stop is the hardwired contactor chain (ADR-0007).

        A pad button labelled E-stop is worse than none, because it will be
        trusted - and it fails silently when the pad disconnects, which is
        exactly when you need it.
        """
        for key, value in gamepad.items():
            assert "estop" not in key.lower(), f"{key} maps something to E-stop"
            if isinstance(value, str):
                assert "estop" not in value.lower().replace("-", "")


class TestJogFeel:
    def test_jog_curve_is_not_linear(self, gamepad):
        """Linear sticks make precise jogging and fast traverse mutually
        exclusive; squaring gives both on one axis of travel."""
        assert gamepad["jog_curve"] in ("squared", "cubed")
