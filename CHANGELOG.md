# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Changelogs are for humans. Record what changed about the *machine* or the
*workflow*, not that a generated file regenerated.

## [Unreleased]

### Added

- Machine description (`machine/wen33013.toml`) as the single source of truth
  for the WEN 33013 conversion: travels, ballscrew leads, microstepping,
  driver limits, control nodes and encoder feedback.
- `machinegen` tool: model, physical-constraint checks, and generators for the
  LinuxCNC INI, per-node firmware headers, and udev rules. Includes a
  `verify` mode that fails when a generated file has drifted from the TOML.
- Constraint checks encoding DM542T limits (2.5 us minimum pulse, 5 us
  direction setup, 200 kHz ceiling), soft-limit sanity, acceleration distance,
  servo-thread burst size, and encoder resolution.
- Node topology model with an enforced split: motion and safety duties on SPI,
  HMI on USB. Attempting to put step generation or limit switches on USB is a
  hard error.
- Closed-loop feedback model: 14-bit absolute encoders, GT2 belt driven so
  they measure real table travel rather than motor rotation. Following-error
  limits in the INI are sized from encoder resolution automatically.
- `ui/dwinui`: compiler from a restricted SVG subset to DWIN T5UIC1 draw
  calls, with a preview renderer that shows what the 16-bit panel will
  actually display.
- Raspberry Pi provisioning (`pi/provision/`): verified card imaging with
  read-back hashing, headless first-boot pre-seed, and the traps found doing
  it on Windows.
- Architecture decision records for the choices made so far.
- `AGENTS.md` working standards, and project skills for the common workflows.

### Notes

- Values marked PROVISIONAL in the machine description are starting points,
  not measurements. They must be confirmed during commissioning before the
  machine cuts anything.

[Unreleased]: https://github.com/jajmangold/wen-33013-cnc/commits/main
