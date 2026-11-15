"""Generated output.

The headline test is `TestScaleAgreement`. LinuxCNC believes the INI's SCALE;
the firmware believes its own STEPS_PER_MM. If those two numbers ever differ,
nothing errors - the machine simply cuts everything at the wrong scale, and
every file looks individually correct while you hunt for the cause.

We have paid for this exact bug class once already, on the Mega Zero, where a
stale rotation_distance left over from a different extruder gave 2.5x
over-extrusion and took months to find. Here it is a unit test.
"""

from __future__ import annotations

import re

import pytest
from machinegen import (
    fingerprint,
    generate_all,
    load_machine,
    parse_machine,
    render_firmware_header,
    render_ini,
    render_udev_rules,
)
from machinegen.emit import GENERATED_BANNER
from machinegen.model import default_machine_path


def ini_value(ini: str, section: str, key: str) -> str:
    """Pull one key out of one INI section."""
    body = ini.split(f"[{section}]", 1)[1].split("\n[", 1)[0]
    match = re.search(rf"^{key}\s*=\s*(.+)$", body, re.MULTILINE)
    assert match, f"{key} not found in [{section}]"
    return match.group(1).strip()


def define_value(header: str, name: str) -> str:
    match = re.search(rf"^#define {name}\s+(.+)$", header, re.MULTILINE)
    assert match, f"#define {name} not found"
    return match.group(1).strip()


@pytest.fixture
def real_machine():
    return load_machine(default_machine_path())


class TestScaleAgreement:
    """The INI and the firmware must agree about steps per mm."""

    def test_scale_matches_for_every_axis(self, real_machine):
        ini = render_ini(real_machine)
        for node in real_machine.motion_nodes:
            header = render_firmware_header(real_machine, node)
            for axis_name in node.axes:
                axis = real_machine.axis(axis_name)
                joint = real_machine.ordered_axes.index(axis)
                ini_scale = float(ini_value(ini, f"JOINT_{joint}", "SCALE"))
                fw_scale = float(
                    define_value(header, f"{axis_name.upper()}_STEPS_PER_MM").rstrip("f")
                )
                assert ini_scale == pytest.approx(fw_scale), (
                    f"axis {axis_name}: INI says {ini_scale} steps/mm but firmware "
                    f"says {fw_scale}. The machine would cut at the wrong scale."
                )

    def test_scale_tracks_a_change_in_microsteps(self, machine_dict):
        """Change one input; both outputs must move together."""
        machine_dict["axis"]["x"]["microsteps"] = 16
        machine = parse_machine(machine_dict)
        ini = render_ini(machine)
        header = render_firmware_header(machine, machine.node("motion0"))
        assert float(ini_value(ini, "JOINT_0", "SCALE")) == pytest.approx(640.0)
        assert float(define_value(header, "X_STEPS_PER_MM").rstrip("f")) == pytest.approx(640.0)

    def test_scale_tracks_a_change_in_lead(self, machine_dict):
        machine_dict["axis"]["x"]["screw_pitch_mm"] = 10.0
        machine = parse_machine(machine_dict)
        ini = render_ini(machine)
        header = render_firmware_header(machine, machine.node("motion0"))
        assert float(ini_value(ini, "JOINT_0", "SCALE")) == pytest.approx(160.0)
        assert float(define_value(header, "X_STEPS_PER_MM").rstrip("f")) == pytest.approx(160.0)


class TestIni:
    def test_carries_the_do_not_edit_banner(self, real_machine):
        assert GENERATED_BANNER in render_ini(real_machine)

    def test_soft_limits_reach_the_joint_section(self, real_machine):
        ini = render_ini(real_machine)
        axis = real_machine.axis("x")
        assert float(ini_value(ini, "JOINT_0", "MIN_LIMIT")) == pytest.approx(axis.soft_min_mm)
        assert float(ini_value(ini, "JOINT_0", "MAX_LIMIT")) == pytest.approx(axis.soft_max_mm)

    def test_joint_count_matches_axes(self, real_machine):
        ini = render_ini(real_machine)
        assert int(ini_value(ini, "KINS", "JOINTS")) == len(real_machine.ordered_axes)

    def test_servo_period_matches_control(self, real_machine):
        ini = render_ini(real_machine)
        assert int(ini_value(ini, "EMCMOT", "SERVO_PERIOD")) == real_machine.control.servo_period_ns

    def test_home_search_direction_follows_the_axis(self, real_machine):
        """Z homes up; a negative search velocity would drive it into the table."""
        ini = render_ini(real_machine)
        z_joint = real_machine.ordered_axes.index(real_machine.axis("z"))
        assert float(ini_value(ini, f"JOINT_{z_joint}", "HOME_SEARCH_VEL")) > 0


class TestFirmwareHeader:
    def test_only_the_owned_axes_appear(self, machine_dict):
        machine_dict["axis"]["y"] = dict(machine_dict["axis"]["x"], travel_mm=130.0)
        machine_dict["node"]["motion0"]["axes"] = ["x"]
        machine_dict["node"]["motion1"] = {
            "transport": "spi", "role": "motion", "spi_cs": 1, "axes": ["y"],
        }
        machine = parse_machine(machine_dict)
        header0 = render_firmware_header(machine, machine.node("motion0"))
        assert "X_STEPS_PER_MM" in header0
        assert "Y_STEPS_PER_MM" not in header0, "a node must not see another node's axis"

    def test_joint_numbering_stays_global_when_split(self, machine_dict):
        machine_dict["axis"]["y"] = dict(machine_dict["axis"]["x"], travel_mm=130.0)
        machine_dict["node"]["motion0"]["axes"] = ["x"]
        machine_dict["node"]["motion1"] = {
            "transport": "spi", "role": "motion", "spi_cs": 1, "axes": ["y"],
        }
        machine = parse_machine(machine_dict)
        header1 = render_firmware_header(machine, machine.node("motion1"))
        assert define_value(header1, "Y_JOINT") == "1", "Y is joint 1 even alone on its board"

    def test_driver_timing_floor_is_exported(self, real_machine):
        node = real_machine.motion_nodes[0]
        header = render_firmware_header(real_machine, node)
        assert define_value(header, "STEP_PULSE_MIN_NS") == "2500u"
        assert define_value(header, "DIR_SETUP_MIN_NS") == "5000u"

    def test_include_guard_is_node_specific(self, real_machine):
        node = real_machine.motion_nodes[0]
        header = render_firmware_header(real_machine, node)
        assert f"MACHINE_CONFIG_{node.name.upper()}_H" in header


class TestUdevRules:
    def test_usb_node_gets_a_stable_symlink(self, machine):
        rules = render_udev_rules(machine)
        assert 'SYMLINK+="cnc/pendant"' in rules
        assert 'ATTRS{serial}=="E6614103E72B4C21"' in rules

    def test_spi_nodes_are_not_listed(self, machine):
        assert "motion0" not in render_udev_rules(machine)


class TestDeterminism:
    def test_rendering_twice_is_identical(self, real_machine, tmp_path):
        """Generated output must be byte-stable, or `verify` is useless."""
        first = generate_all(real_machine, tmp_path, "abc123")
        second = generate_all(real_machine, tmp_path, "abc123")
        assert first == second

    def test_fingerprint_changes_with_content(self, tmp_path):
        a = tmp_path / "a.toml"
        b = tmp_path / "b.toml"
        a.write_text("x = 1")
        b.write_text("x = 2")
        assert fingerprint(a) != fingerprint(b)

    def test_every_target_is_under_the_repo_root(self, real_machine, tmp_path):
        for path in generate_all(real_machine, tmp_path, "fp"):
            assert tmp_path in path.parents
