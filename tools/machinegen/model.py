"""Machine model: the single source of truth, parsed and validated.

Everything downstream - LinuxCNC INI, firmware constants, documentation - is
derived from a `Machine`. Nothing downstream may hard-code a value that could
be computed here. That rule exists because the alternative has already cost us
months once: on the Mega Zero, a stale `rotation_distance` disagreed with the
real extruder and silently scaled every print by 2.5x.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

# DM542T DIP-selectable microstep table (SW5-SW8).
ALLOWED_MICROSTEPS: tuple[int, ...] = (
    1, 2, 4, 5, 8, 10, 16, 20, 25, 32, 40, 50, 64, 100, 125, 128,
)

AXIS_ORDER: tuple[str, ...] = ("x", "y", "z")


class MachineConfigError(ValueError):
    """The machine description is structurally invalid.

    Raised at load time. A config that raises this must never reach a
    generator, because a partially-valid machine produces plausible-looking
    output that is wrong.
    """


def _require_positive(value: float, field: str, context: str) -> None:
    if value <= 0:
        raise MachineConfigError(f"{context}: {field} must be > 0, got {value!r}")


@dataclass(frozen=True)
class Driver:
    """Electrical and timing limits of the step/dir driver.

    These are physical facts about the hardware, not tuning knobs.
    """

    model: str
    min_pulse_us: float
    min_dir_setup_us: float
    max_step_rate_hz: float
    current_min_a: float
    current_max_a: float
    current_a: float

    def __post_init__(self) -> None:
        ctx = f"driver {self.model}"
        _require_positive(self.min_pulse_us, "min_pulse_us", ctx)
        _require_positive(self.min_dir_setup_us, "min_dir_setup_us", ctx)
        _require_positive(self.max_step_rate_hz, "max_step_rate_hz", ctx)
        if not self.current_min_a <= self.current_a <= self.current_max_a:
            raise MachineConfigError(
                f"{ctx}: current_a {self.current_a}A outside drive range "
                f"{self.current_min_a}-{self.current_max_a}A"
            )


@dataclass(frozen=True)
class Motor:
    model: str
    steps_per_rev: int
    holding_torque_nm: float
    rated_current_a: float

    def __post_init__(self) -> None:
        ctx = f"motor {self.model}"
        if self.steps_per_rev <= 0:
            raise MachineConfigError(f"{ctx}: steps_per_rev must be > 0")


DRIVE_KINDS: tuple[str, ...] = ("direct", "belt")


@dataclass(frozen=True)
class Drive:
    """What sits between the motor shaft and the screw.

    "direct" - a coupling. One motor turn is one screw turn.
    "belt"   - a GT2 reduction. One motor turn is motor_teeth/screw_teeth of a
        screw turn, so `reduction` MULTIPLIES steps_per_mm and divides rapids.

    This exists because the reduction is invisible to every other file. A
    missing 2:1 does not raise anywhere - it just cuts everything at half
    size, which is the whole reason AGENTS.md section 2 is written the way
    it is.
    """

    kind: str = "direct"
    motor_teeth: int | None = None
    screw_teeth: int | None = None
    belt_pitch_mm: float | None = None
    belt_width_mm: float | None = None

    def __post_init__(self) -> None:
        ctx = "drive"
        if self.kind not in DRIVE_KINDS:
            raise MachineConfigError(
                f"{ctx}: kind must be one of {', '.join(DRIVE_KINDS)}, got {self.kind!r}"
            )
        if self.kind == "belt":
            if not self.motor_teeth or not self.screw_teeth:
                raise MachineConfigError(
                    f"{ctx}: a belt drive needs motor_teeth and screw_teeth - "
                    f"the reduction between them multiplies steps_per_mm"
                )
            for label, teeth in (("motor_teeth", self.motor_teeth),
                                 ("screw_teeth", self.screw_teeth)):
                if teeth <= 0:
                    raise MachineConfigError(f"{ctx}: {label} must be > 0, got {teeth}")
        elif self.motor_teeth or self.screw_teeth or self.belt_pitch_mm:
            raise MachineConfigError(
                f"{ctx}: a direct drive must not declare belt teeth or pitch - "
                f"either set kind = \"belt\" or remove them"
            )

    @property
    def reduction(self) -> float:
        """Screw turns per motor turn, inverted: > 1 means torque multiplied."""
        if self.kind != "belt":
            return 1.0
        assert self.motor_teeth and self.screw_teeth  # guaranteed by __post_init__
        return self.screw_teeth / self.motor_teeth


ENCODER_INTERFACES: tuple[str, ...] = ("spi1", "pio")
ENCODER_MOUNTS: tuple[str, ...] = ("motor", "belt")


@dataclass(frozen=True)
class Encoder:
    """Absolute magnetic encoder providing position feedback.

    Two mountings, and the difference is not cosmetic:

    "motor" - on the motor shaft. Sees what the motor did, which is NOT what
        the table did. Blind to backlash, coupling slip and screw windup.
    "belt"  - on a pulley driven by a GT2 belt off the axis. Measures real
        table travel, so it sees every error between motor and table. Its
        resolution comes from the PULLEY CIRCUMFERENCE, not the screw lead,
        which usually makes it coarser than a microstep - fine, because its
        job is catching lost motion, not resolving individual microsteps.

    The interface is never "spi0": on the RP2040 SPI0 is the SLAVE link
    carrying the Pi's step commands. Encoders hang off SPI1 as master, or PIO.
    """

    bits: int
    interface: str
    cs: int
    mount: str = "motor"
    pulley_teeth: int | None = None
    belt_pitch_mm: float | None = None
    model: str = ""

    def __post_init__(self) -> None:
        ctx = f"encoder {self.model or '?'}"
        if not 8 <= self.bits <= 20:
            raise MachineConfigError(f"{ctx}: bits must be 8..20, got {self.bits}")
        if self.interface not in ENCODER_INTERFACES:
            raise MachineConfigError(
                f"{ctx}: interface must be one of {', '.join(ENCODER_INTERFACES)}, "
                f"got {self.interface!r} (spi0 is the link to the Pi)"
            )
        if self.cs < 0:
            raise MachineConfigError(f"{ctx}: cs must be >= 0")
        if self.mount not in ENCODER_MOUNTS:
            raise MachineConfigError(
                f"{ctx}: mount must be one of {', '.join(ENCODER_MOUNTS)}, got {self.mount!r}"
            )
        if self.mount == "belt":
            if not self.pulley_teeth or not self.belt_pitch_mm:
                raise MachineConfigError(
                    f"{ctx}: a belt-mounted encoder needs pulley_teeth and belt_pitch_mm "
                    f"- its resolution depends on pulley circumference, not the screw"
                )
            if self.pulley_teeth <= 0 or self.belt_pitch_mm <= 0:
                raise MachineConfigError(f"{ctx}: pulley_teeth and belt_pitch_mm must be > 0")

    @property
    def counts_per_rev(self) -> int:
        return 2**self.bits

    @property
    def pulley_circumference_mm(self) -> float | None:
        if self.mount != "belt":
            return None
        assert self.pulley_teeth is not None and self.belt_pitch_mm is not None
        return self.pulley_teeth * self.belt_pitch_mm

    def travel_per_rev_mm(self, screw_pitch_mm: float) -> float:
        """Axis travel for one encoder revolution."""
        if self.mount == "motor":
            return screw_pitch_mm
        circumference = self.pulley_circumference_mm
        assert circumference is not None
        return circumference


@dataclass(frozen=True)
class Axis:
    """One linear axis.

    `steps_per_mm` is derived, never stored. It is the number that must agree
    between the LinuxCNC INI and the firmware; see tests/unit/test_emit.py.
    """

    name: str
    travel_mm: float
    screw_pitch_mm: float
    microsteps: int
    max_velocity_mm_s: float
    max_accel_mm_s2: float
    home_direction: int
    soft_limit_margin_mm: float
    invert_direction: bool
    motor_steps_per_rev: int
    drive: Drive = Drive()
    encoder: Encoder | None = None

    def __post_init__(self) -> None:
        ctx = f"axis {self.name}"
        _require_positive(self.travel_mm, "travel_mm", ctx)
        _require_positive(self.screw_pitch_mm, "screw_pitch_mm", ctx)
        _require_positive(self.max_velocity_mm_s, "max_velocity_mm_s", ctx)
        _require_positive(self.max_accel_mm_s2, "max_accel_mm_s2", ctx)
        if self.microsteps not in ALLOWED_MICROSTEPS:
            raise MachineConfigError(
                f"{ctx}: microsteps {self.microsteps} is not a DM542T setting; "
                f"allowed: {', '.join(map(str, ALLOWED_MICROSTEPS))}"
            )
        if self.home_direction not in (-1, 1):
            raise MachineConfigError(
                f"{ctx}: home_direction must be -1 or 1, got {self.home_direction!r}"
            )
        if self.soft_limit_margin_mm < 0:
            raise MachineConfigError(f"{ctx}: soft_limit_margin_mm must be >= 0")
        if self.travel_mm <= 2 * self.soft_limit_margin_mm:
            raise MachineConfigError(
                f"{ctx}: soft limit margins ({self.soft_limit_margin_mm}mm each end) "
                f"consume the entire {self.travel_mm}mm travel"
            )

    @property
    def steps_per_rev(self) -> int:
        """Full microsteps per motor revolution."""
        return self.motor_steps_per_rev * self.microsteps

    @property
    def steps_per_mm(self) -> float:
        """THE derived number. Everything scales from this."""
        return self.steps_per_rev * self.drive.reduction / self.screw_pitch_mm

    @property
    def travel_per_motor_rev_mm(self) -> float:
        """How far the table moves for one turn of the MOTOR."""
        return self.screw_pitch_mm / self.drive.reduction

    @property
    def max_step_rate_hz(self) -> float:
        """Step rate demanded at max velocity."""
        return self.max_velocity_mm_s * self.steps_per_mm

    @property
    def soft_min_mm(self) -> float:
        return self.soft_limit_margin_mm

    @property
    def soft_max_mm(self) -> float:
        return self.travel_mm - self.soft_limit_margin_mm

    @property
    def resolution_mm(self) -> float:
        """Distance moved by one microstep."""
        return 1.0 / self.steps_per_mm

    @property
    def counts_per_mm(self) -> float | None:
        """Encoder counts per mm, or None on an open-loop axis."""
        if self.encoder is None:
            return None
        return self.encoder.counts_per_rev / self.encoder.travel_per_rev_mm(self.screw_pitch_mm)

    @property
    def encoder_resolution_mm(self) -> float | None:
        cpm = self.counts_per_mm
        return None if cpm is None else 1.0 / cpm

    @property
    def is_closed_loop(self) -> bool:
        return self.encoder is not None


TRANSPORTS: tuple[str, ...] = ("spi", "usb")
ROLES: tuple[str, ...] = ("motion", "io", "hmi")

# Roles that may ONLY live on a deterministic link. See ADR-0007.
REALTIME_ROLES: frozenset[str] = frozenset({"motion", "io"})


@dataclass(frozen=True)
class Node:
    """One RP2040 on the control bus.

    Transport decides what a node is allowed to do, not the other way round.
    A USB CDC link has no latency guarantee - it is fine for a screen, and
    never acceptable for step generation or for anything that must stop the
    machine.
    """

    name: str
    transport: str
    role: str
    axes: tuple[str, ...] = ()
    spi_cs: int | None = None
    usb_serial: str = ""
    safety_inputs: bool = False

    def __post_init__(self) -> None:
        ctx = f"node {self.name}"
        if self.transport not in TRANSPORTS:
            raise MachineConfigError(
                f"{ctx}: transport must be one of {', '.join(TRANSPORTS)}, "
                f"got {self.transport!r}"
            )
        if self.role not in ROLES:
            raise MachineConfigError(
                f"{ctx}: role must be one of {', '.join(ROLES)}, got {self.role!r}"
            )
        if self.transport == "spi" and self.spi_cs is None:
            raise MachineConfigError(f"{ctx}: an SPI node needs spi_cs")
        if self.transport == "usb" and self.spi_cs is not None:
            raise MachineConfigError(f"{ctx}: a USB node must not declare spi_cs")
        if self.axes and self.role != "motion":
            raise MachineConfigError(
                f"{ctx}: role {self.role!r} must not own axes {list(self.axes)}"
            )
        if self.role == "motion" and not self.axes:
            raise MachineConfigError(f"{ctx}: a motion node must own at least one axis")

    @property
    def is_realtime(self) -> bool:
        return self.role in REALTIME_ROLES


@dataclass(frozen=True)
class Spindle:
    min_rpm: int
    max_rpm: int
    control: str


@dataclass(frozen=True)
class Control:
    host: str
    servo_period_ns: int
    transport: str
    spi_clock_hz: int

    @property
    def servo_period_s(self) -> float:
        return self.servo_period_ns / 1e9

    @property
    def servo_rate_hz(self) -> float:
        return 1e9 / self.servo_period_ns


@dataclass(frozen=True)
class Machine:
    name: str
    base_machine: str
    description: str
    control: Control
    driver: Driver
    motor: Motor
    axes: dict[str, Axis]
    spindle: Spindle
    nodes: dict[str, Node]

    def node(self, name: str) -> Node:
        try:
            return self.nodes[name]
        except KeyError:
            raise MachineConfigError(f"no such node: {name!r}") from None

    @property
    def motion_nodes(self) -> list[Node]:
        return [n for n in self.nodes.values() if n.role == "motion"]

    @property
    def usb_nodes(self) -> list[Node]:
        return [n for n in self.nodes.values() if n.transport == "usb"]

    def node_owning(self, axis_name: str) -> Node | None:
        for node in self.nodes.values():
            if axis_name in node.axes:
                return node
        return None

    def axis(self, name: str) -> Axis:
        try:
            return self.axes[name]
        except KeyError:
            raise MachineConfigError(f"no such axis: {name!r}") from None

    @property
    def ordered_axes(self) -> list[Axis]:
        """Axes in canonical X, Y, Z order - joint numbering depends on this."""
        return [self.axes[n] for n in AXIS_ORDER if n in self.axes]


def _section(data: dict, key: str) -> dict:
    if key not in data:
        raise MachineConfigError(f"missing required section [{key}]")
    return data[key]


def parse_machine(data: dict) -> Machine:
    """Build a Machine from an already-parsed TOML mapping."""
    machine = _section(data, "machine")
    control = _section(data, "control")
    driver = _section(data, "driver")
    motor = _section(data, "motor")
    spindle = _section(data, "spindle")
    axes_raw = _section(data, "axis")
    nodes_raw = _section(data, "node")

    if not axes_raw:
        raise MachineConfigError("no axes defined")

    motor_obj = Motor(
        model=motor["model"],
        steps_per_rev=motor["steps_per_rev"],
        holding_torque_nm=motor.get("holding_torque_nm", 0.0),
        rated_current_a=motor.get("rated_current_a", 0.0),
    )

    axes = {
        name: Axis(
            name=name,
            travel_mm=a["travel_mm"],
            screw_pitch_mm=a["screw_pitch_mm"],
            microsteps=a["microsteps"],
            max_velocity_mm_s=a["max_velocity_mm_s"],
            max_accel_mm_s2=a["max_accel_mm_s2"],
            home_direction=a["home_direction"],
            soft_limit_margin_mm=a["soft_limit_margin_mm"],
            invert_direction=a["invert_direction"],
            motor_steps_per_rev=motor_obj.steps_per_rev,
            drive=(
                Drive(
                    kind=a["drive"].get("kind", "direct"),
                    motor_teeth=a["drive"].get("motor_teeth"),
                    screw_teeth=a["drive"].get("screw_teeth"),
                    belt_pitch_mm=a["drive"].get("belt_pitch_mm"),
                    belt_width_mm=a["drive"].get("belt_width_mm"),
                )
                if "drive" in a
                else Drive()
            ),
            encoder=(
                Encoder(
                    bits=a["encoder"]["bits"],
                    interface=a["encoder"]["interface"],
                    cs=a["encoder"]["cs"],
                    mount=a["encoder"].get("mount", "motor"),
                    pulley_teeth=a["encoder"].get("pulley_teeth"),
                    belt_pitch_mm=a["encoder"].get("belt_pitch_mm"),
                    model=a["encoder"].get("model", ""),
                )
                if "encoder" in a
                else None
            ),
        )
        for name, a in axes_raw.items()
    }

    unknown = set(axes) - set(AXIS_ORDER)
    if unknown:
        raise MachineConfigError(
            f"unknown axis name(s): {', '.join(sorted(unknown))}; "
            f"expected a subset of {', '.join(AXIS_ORDER)}"
        )

    return Machine(
        name=machine["name"],
        base_machine=machine["base_machine"],
        description=machine["description"],
        control=Control(
            host=control["host"],
            servo_period_ns=control["servo_period_ns"],
            transport=control["transport"],
            spi_clock_hz=control["spi_clock_hz"],
        ),
        driver=Driver(
            model=driver["model"],
            min_pulse_us=driver["min_pulse_us"],
            min_dir_setup_us=driver["min_dir_setup_us"],
            max_step_rate_hz=driver["max_step_rate_hz"],
            current_min_a=driver["current_min_a"],
            current_max_a=driver["current_max_a"],
            current_a=driver["current_a"],
        ),
        motor=motor_obj,
        axes=axes,
        spindle=Spindle(
            min_rpm=spindle["min_rpm"],
            max_rpm=spindle["max_rpm"],
            control=spindle["control"],
        ),
        nodes={
            name: Node(
                name=name,
                transport=n["transport"],
                role=n["role"],
                axes=tuple(n.get("axes", ())),
                spi_cs=n.get("spi_cs"),
                usb_serial=n.get("usb_serial", ""),
                safety_inputs=n.get("safety_inputs", False),
            )
            for name, n in nodes_raw.items()
        },
    )


def load_machine(path: str | Path) -> Machine:
    """Load and validate the machine description."""
    path = Path(path)
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except FileNotFoundError:
        raise MachineConfigError(f"machine description not found: {path}") from None
    except tomllib.TOMLDecodeError as exc:
        raise MachineConfigError(f"{path}: invalid TOML: {exc}") from None
    try:
        return parse_machine(data)
    except KeyError as exc:
        raise MachineConfigError(f"{path}: missing required key {exc}") from None


def default_machine_path() -> Path:
    """Path to the repo's machine description."""
    return Path(__file__).resolve().parents[2] / "machine" / "wen33013.toml"
