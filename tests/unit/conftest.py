"""Fixtures for machinegen unit tests.

`machine_dict` is a minimal VALID machine. Tests mutate a copy of it to
produce the specific invalid case they are about, so each test states exactly
one thing.
"""

from __future__ import annotations

import copy
import re

import pytest
from machinegen import parse_machine

BASE: dict = {
    "machine": {
        "name": "test-machine",
        "base_machine": "WEN 33013",
        "description": "fixture",
    },
    "control": {
        "host": "lcnc",
        "servo_period_ns": 1_000_000,
        "transport": "spi",
        "spi_clock_hz": 10_000_000,
    },
    "driver": {
        "model": "DM542T",
        "min_pulse_us": 2.5,
        "min_dir_setup_us": 5.0,
        "max_step_rate_hz": 200_000,
        "current_min_a": 1.0,
        "current_max_a": 4.5,
        "current_a": 2.8,
    },
    "motor": {
        "model": "NEMA 23",
        "steps_per_rev": 200,
        "holding_torque_nm": 1.9,
        "rated_current_a": 2.8,
    },
    "spindle": {"min_rpm": 100, "max_rpm": 2500, "control": "manual"},
    "node": {
        "motion0": {
            "transport": "spi",
            "role": "motion",
            "spi_cs": 0,
            "axes": ["x"],
            "safety_inputs": True,
        },
        "pendant": {
            "transport": "usb",
            "role": "hmi",
            "usb_serial": "E6614103E72B4C21",
        },
    },
    "axis": {
        "x": {
            "travel_mm": 300.0,
            "screw_pitch_mm": 5.0,
            "microsteps": 8,
            "max_velocity_mm_s": 41.67,
            "max_accel_mm_s2": 400.0,
            "home_direction": -1,
            "soft_limit_margin_mm": 2.0,
            "invert_direction": False,
        }
    },
}


def _ini_value(ini: str, section: str, key: str) -> str:
    """Pull one key out of one INI section."""
    body = ini.split(f"[{section}]", 1)[1].split("\n[", 1)[0]
    match = re.search(rf"^{key}\s*=\s*(.+)$", body, re.MULTILINE)
    assert match, f"{key} not found in [{section}]"
    return match.group(1).strip()


def _define_value(header: str, name: str) -> str:
    """Pull one #define out of a generated C header."""
    match = re.search(rf"^#define {name}\s+(.+)$", header, re.MULTILINE)
    assert match, f"#define {name} not found"
    return match.group(1).strip()


@pytest.fixture
def ini_value():
    """Shared as a fixture so test modules never import each other."""
    return _ini_value


@pytest.fixture
def define_value():
    return _define_value


@pytest.fixture
def machine_dict() -> dict:
    return copy.deepcopy(BASE)


@pytest.fixture
def machine(machine_dict):
    return parse_machine(machine_dict)
