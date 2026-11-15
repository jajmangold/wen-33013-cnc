"""Integration: the generated config must actually load into LinuxCNC.

Runs on the Pi, where LinuxCNC exists. Skipped everywhere else rather than
failing, because a dev box legitimately cannot run these.

A config that loads is NOT a config that is correct - scale, direction and
limits are only proven against a physical indicator by /commission-axis. What
these catch is the other failure: a generated INI that is malformed, or
references a HAL file or pin that does not exist.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

CONFIG = Path(__file__).resolve().parents[2] / "linuxcnc" / "configs" / "wen33013"

requires_linuxcnc = pytest.mark.skipif(
    shutil.which("halrun") is None,
    reason="LinuxCNC not installed (run this on the Pi)",
)


@requires_linuxcnc
def test_hal_files_parse():
    """Every HAL file must load into a bare halrun without error."""
    for hal in sorted((CONFIG).glob("*.hal")):
        result = subprocess.run(
            ["halrun", "-f", str(hal)], capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, f"{hal.name} failed to load:\n{result.stderr}"


@requires_linuxcnc
def test_ini_is_well_formed():
    import configparser

    ini = CONFIG / "wen33013.ini"
    parser = configparser.ConfigParser(strict=False)
    parser.read(ini, encoding="utf-8")
    assert parser.has_section("EMC")
    assert parser.has_section("KINS")
    joints = int(parser["KINS"]["JOINTS"])
    for index in range(joints):
        assert parser.has_section(f"JOINT_{index}"), f"JOINT_{index} missing"


def test_config_directory_exists():
    """Runs anywhere: catches a generator that stopped writing output."""
    assert (CONFIG / "wen33013.ini").exists(), "run `make gen`"
