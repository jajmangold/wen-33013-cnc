"""The pendant node: screen orientation and identity.

The orientation check is the point of this file. The DWIN panel's stock CFG
boots rotated 90 degrees, presenting the 480x272 LCD as a 272x480 portrait
frame - so the driver's own default is WIDTH=272, HEIGHT=480.

Our screens are drawn landscape. If the firmware forgets to call
set_orientation(0), every element lands off-screen or rotated and **the panel
reports nothing**. It is the same class of silent mismatch as steps/mm, so it
gets the same treatment: an assertion rather than a sentence in a README.
"""

from __future__ import annotations

import tomllib

import pytest
from dwinui import HEIGHT, WIDTH
from machinegen import load_machine
from machinegen.model import default_machine_path

# Physical LCD, independent of how the CFG presents it.
PANEL_LONG_EDGE = 480
PANEL_SHORT_EDGE = 272


@pytest.fixture
def pendant_raw() -> dict:
    """The pendant node as written, including fields the model ignores."""
    with default_machine_path().open("rb") as fh:
        return tomllib.load(fh)["node"]["pendant"]


class TestOrientation:
    def test_compiler_canvas_is_the_physical_panel(self):
        assert {WIDTH, HEIGHT} == {PANEL_LONG_EDGE, PANEL_SHORT_EDGE}

    def test_declared_orientation_matches_the_compiler(self, pendant_raw):
        """The TOML and ui/dwinui must not disagree about which way up it is."""
        declared = pendant_raw["orientation"]
        assert declared in ("landscape", "portrait")
        if declared == "landscape":
            assert (WIDTH, HEIGHT) == (PANEL_LONG_EDGE, PANEL_SHORT_EDGE), (
                "TOML says landscape but ui/dwinui is portrait"
            )
        else:
            assert (WIDTH, HEIGHT) == (PANEL_SHORT_EDGE, PANEL_LONG_EDGE), (
                "TOML says portrait but ui/dwinui is landscape"
            )

    def test_landscape_requires_an_explicit_rotation(self, pendant_raw):
        """Landscape is NOT the panel's default - it must be set at startup.

        Recorded as a test so that choosing landscape can never quietly become
        an assumption that the firmware does something it does not do.
        """
        if pendant_raw["orientation"] == "landscape":
            assert "set_orientation" in default_machine_path().read_text(encoding="utf-8"), (
                "landscape chosen but the TOML does not record that firmware "
                "must call set_orientation(0)"
            )


class TestIdentity:
    def test_usb_serial_is_recorded(self, pendant_raw):
        serial = pendant_raw["usb_serial"]
        assert serial and serial.upper() != "TBD", "record the running USB serial"

    def test_usb_serial_looks_like_an_rp2040_unique_id(self, pendant_raw):
        """RP2040 unique_id is 8 bytes -> 16 hex characters.

        Guards against pasting the BOOTSEL mass-storage serial, which is a
        different and shorter id.
        """
        serial = pendant_raw["usb_serial"]
        assert len(serial) == 16, f"expected 16 hex chars, got {len(serial)}: {serial}"
        int(serial, 16)

    def test_pendant_stays_off_the_realtime_path(self):
        machine = load_machine(default_machine_path())
        pendant = machine.node("pendant")
        assert pendant.transport == "usb"
        assert not pendant.is_realtime
        assert not pendant.safety_inputs
