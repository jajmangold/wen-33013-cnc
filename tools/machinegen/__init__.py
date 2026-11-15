"""machinegen - derive every machine-dependent file from one description.

Public surface:

    load_machine(path)      -> Machine      parse + validate
    check_machine(machine)  -> [Violation]  physical/safety constraints
    generate_all(...)       -> {path: text} rendered outputs

Nothing in this package writes to disk except `cli`.
"""

from .constraints import Severity, Violation, check_machine, errors
from .emit import (
    fingerprint,
    firmware_header_path,
    generate_all,
    render_firmware_header,
    render_ini,
    render_udev_rules,
)
from .model import (
    ALLOWED_MICROSTEPS,
    Axis,
    Driver,
    Machine,
    MachineConfigError,
    Motor,
    Node,
    default_machine_path,
    load_machine,
    parse_machine,
)

__all__ = [
    "ALLOWED_MICROSTEPS",
    "Axis",
    "Driver",
    "Machine",
    "MachineConfigError",
    "Motor",
    "Severity",
    "Node",
    "firmware_header_path",
    "render_udev_rules",
    "Violation",
    "check_machine",
    "default_machine_path",
    "errors",
    "fingerprint",
    "generate_all",
    "load_machine",
    "parse_machine",
    "render_firmware_header",
    "render_ini",
]
