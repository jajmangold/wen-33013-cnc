"""Hardware tests: these MOVE THE MACHINE.

Never run unattended, never in CI, never without a hand on the E-stop. They
exist so commissioning measurements are repeatable and recorded, not so they
can be automated.

Run deliberately:

    make hardware           # after reading docs/commissioning/README.md

Every test here must be safe to abort at any instant, must start from a homed
machine, and must not depend on a previous test having run.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.hardware


@pytest.fixture
def machine_is_homed():
    """Refuse to move an unhomed machine.

    Soft limits mean nothing before homing, so a jog on an unhomed machine is
    a jog with no limits at all.
    """
    pytest.skip("not implemented: assert LinuxCNC reports all joints homed")


@pytest.mark.parametrize("axis", ["x", "y", "z"])
def test_commanded_travel_matches_measured(axis, machine_is_homed):
    """Command 50 mm, measure with an indicator, compare against the model.

    This is the test that catches a steps/mm error - the failure that
    otherwise shows up as every part being the wrong size. It needs a human
    with an indicator, so it prompts rather than automating.
    """
    pytest.skip("manual procedure: see /commission-axis")


@pytest.mark.parametrize("axis", ["x", "y", "z"])
def test_encoder_agrees_with_commanded(axis, machine_is_homed):
    """The belt encoder measures the table; disagreement is real, not noise.

    A constant ratio means pulley_teeth or belt_pitch_mm is wrong in the TOML.
    A drifting difference means lost steps - which is exactly what these
    encoders were fitted to find.
    """
    pytest.skip("manual procedure: see /commission-axis")


def test_estop_removes_driver_power():
    """Pressing E-stop must kill driver power with the Pi still running.

    Verified physically, at the contactor. Never by forcing a HAL pin: that
    tests the software's opinion of the chain, not the chain (ADR-0007).
    """
    pytest.skip("manual procedure: see docs/commissioning/README.md")
