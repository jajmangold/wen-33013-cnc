"""Physical and safety constraints on the machine description.

These checks encode facts about hardware that cannot be negotiated: the
DM542T's timing limits, the travel of the WEN 33013's table, what the servo
thread can actually deliver. A machine description that fails an ERROR check
must not be used to generate anything.

Rule of thumb for adding a check here: if violating it would damage hardware,
produce silently wrong motion, or crash an axis into a hard stop, it is an
ERROR. If it would merely perform badly, it is a WARNING.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .model import Machine


class Severity(Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"


@dataclass(frozen=True)
class Violation:
    severity: Severity
    where: str
    message: str
    detail: str = ""

    def __str__(self) -> str:
        head = f"[{self.severity.value}] {self.where}: {self.message}"
        return f"{head}\n    {self.detail}" if self.detail else head


def _check_step_rate(machine: Machine) -> list[Violation]:
    """Demanded step rate must stay inside the driver's ceiling.

    Exceeding it does not fail loudly - the driver simply drops pulses, so the
    axis loses position while everything still looks fine. That is the worst
    possible failure mode, hence ERROR.
    """
    out: list[Violation] = []
    ceiling = machine.driver.max_step_rate_hz
    for axis in machine.ordered_axes:
        rate = axis.max_step_rate_hz
        if rate > ceiling:
            out.append(
                Violation(
                    Severity.ERROR,
                    f"axis.{axis.name}",
                    f"max velocity needs {rate:,.0f} Hz, "
                    f"{machine.driver.model} tops out at {ceiling:,.0f} Hz",
                    f"Reduce max_velocity_mm_s below "
                    f"{ceiling / axis.steps_per_mm:.2f} mm/s, or reduce microsteps.",
                )
            )
        elif rate > 0.8 * ceiling:
            out.append(
                Violation(
                    Severity.WARNING,
                    f"axis.{axis.name}",
                    f"max velocity uses {rate / ceiling:.0%} of the driver's step ceiling",
                    "Little headroom for accel overshoot or future speed increases.",
                )
            )
    return out


def _check_pulse_width(machine: Machine) -> list[Violation]:
    """A 50% duty pulse at max step rate must still satisfy min_pulse_us."""
    out: list[Violation] = []
    min_pulse_s = machine.driver.min_pulse_us / 1e6
    for axis in machine.ordered_axes:
        rate = axis.max_step_rate_hz
        if rate <= 0:
            continue
        half_period_s = 1.0 / rate / 2.0
        if half_period_s < min_pulse_s:
            out.append(
                Violation(
                    Severity.ERROR,
                    f"axis.{axis.name}",
                    f"at {rate:,.0f} Hz a 50% duty pulse is "
                    f"{half_period_s * 1e6:.2f} us, below the "
                    f"{machine.driver.min_pulse_us} us minimum",
                    "The driver will miss steps. Lower max_velocity_mm_s or microsteps.",
                )
            )
    return out


def _check_soft_limits(machine: Machine) -> list[Violation]:
    out: list[Violation] = []
    for axis in machine.ordered_axes:
        if axis.soft_max_mm <= axis.soft_min_mm:
            out.append(
                Violation(
                    Severity.ERROR,
                    f"axis.{axis.name}",
                    "soft limits leave no usable travel",
                    f"soft range {axis.soft_min_mm}..{axis.soft_max_mm} mm "
                    f"of {axis.travel_mm} mm travel",
                )
            )
        if axis.soft_limit_margin_mm == 0:
            out.append(
                Violation(
                    Severity.WARNING,
                    f"axis.{axis.name}",
                    "no soft limit margin",
                    "Nothing stands between a soft limit and the hard stop.",
                )
            )
    return out


def _check_accel_distance(machine: Machine) -> list[Violation]:
    """Reaching max velocity must not consume more than half the travel."""
    out: list[Violation] = []
    for axis in machine.ordered_axes:
        dist = axis.max_velocity_mm_s**2 / (2 * axis.max_accel_mm_s2)
        usable = axis.soft_max_mm - axis.soft_min_mm
        if dist > usable / 2:
            out.append(
                Violation(
                    Severity.WARNING,
                    f"axis.{axis.name}",
                    f"needs {dist:.1f} mm to reach max velocity, "
                    f"over half its {usable:.1f} mm usable travel",
                    "The axis will never reach max_velocity_mm_s in practice.",
                )
            )
    return out


def _check_servo_thread(machine: Machine) -> list[Violation]:
    """The stepgen must be able to emit a whole servo period's steps.

    Fractional steps per cycle are fine (the accumulator carries them), but a
    very high count per cycle means the PIO burst dominates the period.
    """
    out: list[Violation] = []
    rate_hz = machine.control.servo_rate_hz
    for axis in machine.ordered_axes:
        per_cycle = axis.max_step_rate_hz / rate_hz
        if per_cycle > 255:
            out.append(
                Violation(
                    Severity.ERROR,
                    f"axis.{axis.name}",
                    f"{per_cycle:.0f} steps per servo cycle exceeds the "
                    f"255-step burst the protocol encodes",
                    "Raise the servo rate or lower max_velocity_mm_s.",
                )
            )
    return out


def _check_resolution(machine: Machine) -> list[Violation]:
    out: list[Violation] = []
    for axis in machine.ordered_axes:
        if axis.resolution_mm > 0.01:
            out.append(
                Violation(
                    Severity.WARNING,
                    f"axis.{axis.name}",
                    f"one microstep is {axis.resolution_mm * 1000:.1f} um",
                    "Coarse for a mill; consider more microsteps if step rate allows.",
                )
            )
    return out


def _check_node_topology(machine: Machine) -> list[Violation]:
    """Which RP2040 is allowed to do what.

    The governing rule: USB CDC has no bounded latency. A screen stuttering
    for 50 ms is a cosmetic annoyance; a step pulse or a limit switch late by
    50 ms is a crash. So realtime and safety duties are confined to the SPI
    link, and this is enforced rather than documented.
    """
    out: list[Violation] = []

    for node in machine.nodes.values():
        if node.is_realtime and node.transport != "spi":
            out.append(
                Violation(
                    Severity.ERROR,
                    f"node.{node.name}",
                    f"role {node.role!r} cannot run over {node.transport}",
                    "USB CDC gives no latency guarantee. Realtime roles must be SPI.",
                )
            )
        if node.safety_inputs and node.transport != "spi":
            out.append(
                Violation(
                    Severity.ERROR,
                    f"node.{node.name}",
                    "safety inputs cannot run over a non-deterministic link",
                    "Limits and probe must be SPI. E-stop must additionally be "
                    "hardwired and not depend on software at all.",
                )
            )
        if node.transport == "usb" and node.usb_serial.strip().upper() in ("", "TBD"):
            out.append(
                Violation(
                    Severity.WARNING,
                    f"node.{node.name}",
                    "no USB serial recorded yet",
                    "Without one, /dev/serial/by-id is unstable and nodes swap "
                    "identity on reboot. Record it during commissioning.",
                )
            )

    seen_cs: dict[int, str] = {}
    for node in machine.nodes.values():
        if node.spi_cs is None:
            continue
        if node.spi_cs in seen_cs:
            out.append(
                Violation(
                    Severity.ERROR,
                    f"node.{node.name}",
                    f"SPI CS {node.spi_cs} already used by node "
                    f"{seen_cs[node.spi_cs]!r}",
                )
            )
        seen_cs[node.spi_cs] = node.name

    for axis in machine.ordered_axes:
        owners = [n.name for n in machine.nodes.values() if axis.name in n.axes]
        if not owners:
            out.append(
                Violation(
                    Severity.ERROR,
                    f"axis.{axis.name}",
                    "no node owns this axis",
                    "Every axis must be assigned to exactly one motion node.",
                )
            )
        elif len(owners) > 1:
            out.append(
                Violation(
                    Severity.ERROR,
                    f"axis.{axis.name}",
                    f"claimed by multiple nodes: {', '.join(sorted(owners))}",
                )
            )

    for node in machine.nodes.values():
        unknown = set(node.axes) - set(machine.axes)
        if unknown:
            out.append(
                Violation(
                    Severity.ERROR,
                    f"node.{node.name}",
                    f"owns undefined axis/axes: {', '.join(sorted(unknown))}",
                )
            )

    return out


def _check_encoders(machine: Machine) -> list[Violation]:
    """Feedback sanity.

    A belt-driven encoder is deliberately coarser than a microstep - that is
    the expected trade for measuring the table instead of the motor - so a
    coarser resolution is a note, not a fault. What IS a fault is two encoders
    sharing a chip select, because they will silently return each other's
    readings.
    """
    out: list[Violation] = []

    seen: dict[tuple[str, int], str] = {}
    for axis in machine.ordered_axes:
        enc = axis.encoder
        if enc is None:
            out.append(
                Violation(
                    Severity.WARNING,
                    f"axis.{axis.name}",
                    "open loop - no encoder",
                    "Lost steps will go undetected until the part is measured.",
                )
            )
            continue

        key = (enc.interface, enc.cs)
        if key in seen:
            out.append(
                Violation(
                    Severity.ERROR,
                    f"axis.{axis.name}",
                    f"encoder on {enc.interface} CS {enc.cs} collides with "
                    f"axis.{seen[key]}",
                    "Both would answer at once and return each other's position.",
                )
            )
        seen[key] = axis.name

        enc_res = axis.encoder_resolution_mm
        assert enc_res is not None
        if enc_res > axis.resolution_mm:
            out.append(
                Violation(
                    Severity.WARNING,
                    f"axis.{axis.name}",
                    f"encoder resolves {enc_res * 1000:.2f} um, coarser than the "
                    f"{axis.resolution_mm * 1000:.2f} um microstep",
                    "Expected for a belt-mounted encoder. It detects lost motion "
                    "rather than resolving single microsteps; size FERROR above it.",
                )
            )
        if enc_res > 0.02:
            out.append(
                Violation(
                    Severity.ERROR,
                    f"axis.{axis.name}",
                    f"encoder resolution {enc_res * 1000:.0f} um is too coarse to "
                    f"be useful feedback on a mill",
                    "Use a smaller pulley or a higher-count encoder.",
                )
            )
    return out


CHECKS = (
    _check_node_topology,
    _check_encoders,
    _check_step_rate,
    _check_pulse_width,
    _check_soft_limits,
    _check_accel_distance,
    _check_servo_thread,
    _check_resolution,
)


def check_machine(machine: Machine) -> list[Violation]:
    """Run every constraint. Returns all violations, errors first."""
    found: list[Violation] = []
    for check in CHECKS:
        found.extend(check(machine))
    return sorted(found, key=lambda v: 0 if v.severity is Severity.ERROR else 1)


def errors(violations: list[Violation]) -> list[Violation]:
    return [v for v in violations if v.severity is Severity.ERROR]
