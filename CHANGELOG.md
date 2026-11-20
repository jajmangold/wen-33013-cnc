# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Changelogs are for humans. Record what changed about the *machine* or the
*workflow*, not that a generated file regenerated.

## [Unreleased]

### Fixed

- **The bore clears the boss instead of registering on it.** Nothing here
  needs locating tightly: pulley planes are set by the pulleys on their own
  shafts, centre distance is adjustable through the motor's +-8 mm slots,
  and lateral offset only changes the direction of belt pull. Ø42 over a
  Ø35 boss, 3.5 clear all round. A close register bought precision nothing
  consumes while adding the one failure mode that stops a part going on.
- **The side walls fouled the boss**, found by the assertion written for the
  bore. The boss stands 16 proud and pokes 8 past the backplate into the
  U-channel, where the walls sat at |Y| 20 - only 2.5 from a Ø35 boss, less
  than the loosened bore now lets it sit off-centre. Walls moved to 22.5.
- Opening the bore made it break out of the backplate's bottom edge, turning
  a closed ring into a horseshoe; the backplate now reaches far enough down
  to keep it closed.

- **The boss is Ø35 and stands 16 proud; the register bore is back.** It was
  briefly removed on a misreading of a head-on photo, in which the casting
  appeared to sit behind the gauge's fingers; a side-on shot showed it
  plainly protruding, with the steel retainer on its face and the pulley hard
  up against it. The bore is Ø35.15 in the 8 mm backplate, so the plate bears
  on the casting's face while the bore engages 8 mm of the boss.
- `build.py` now asserts the register FITS rather than merely missing: the
  real Ø35 boss must pass through the bore and a Ø35.5 one must not. An
  oversized bore locates nothing, and a clash test alone cannot tell.
- `LAND_START_X` is no longer a guess. The pulley seats on the boss face, so
  it is the boss protrusion - confirmed in the side-on photo, where scaling
  off the pulley's known 28.4 flange OD put its width at 21.4 against the
  modelled 21.8.
- `render.py` saved nothing before closing documents it had recoloured, so
  FreeCAD raised a save prompt that blocked the GUI thread. Every later call
  then timed out and the instance looked hung when it was waiting on a
  dialog nobody could see.
- **The X bracket's register bore was 25 mm out of position.** It was placed
  from a third-party STEP model that put the bolt line 26.3 above the screw;
  the screw actually runs on the end plate's centreline, which makes it 1.0.
  Found by printing the bracket and offering it up. The plate is 115 wide,
  not 120, and its Ø10 holes are clearance for M5s that thread into the table.
- Plate dimensions are now recorded as measured - from the plate's edges -
  rather than as centres derived from a model, so correcting one is one edit.

### Added

- **Photogrammetry for machine dimensions** (`hardware/mechanical/lib/charuco.py`).
  Tape a printed ChArUco board on the surface, photograph it, and the tool
  recovers the homography and rectifies the picture into a square-on metric
  view where a pixel is a known fraction of a millimetre. It reports a
  reprojection error, so a bad photo says so rather than returning a
  confident wrong number. Against a synthetic oblique view a 92 mm span
  measures true to 12 um. `opencv-contrib-python` is a dev-only extra.
- `gauge.py`: a 12 cm3 flat gauge to print, hold against the plate and
  photograph. It carries the bolt pattern, a scribed line where the plate's
  top edge should fall, and a fan of fingers reaching to known radii, so the
  bolt pattern, the plate height and the boss OD can all be read off one
  picture rather than measured again.

### Fixed

- **The bracket no longer depends on the one dimension nobody could
  measure.** How far the bolt line sits above the screw axis had four
  answers spanning 25 mm. The Ø35 boss already locates the bracket to
  0.15 mm through the register bore and the bolts were only ever clamping,
  so their holes are now vertical slots spanning 1 to 23 above the screw -
  the bolts land wherever the truth is. `build.py` asserts the slots cover
  every candidate rather than trusting the arithmetic. The X bracket can be
  printed without resolving the measurement.
- The source fingerprint hashed raw bytes, so the same machine description
  fingerprinted differently on Windows (CRLF working copy) and Linux (LF in
  git). Every generated file then looked stale on whichever machine had not
  written it - `verify` failed on CI while passing locally, with nothing in
  the diff to explain why. Line endings are normalised before hashing.

## [0.1.0] - 2026-11-19

### Added

- **A fit coupon for the X bracket** (`stl/FitPlate.stl`, 18 cm3 against the
  bracket's 140). It is the bracket's own first 4 mm, built as an
  intersection with a thin slab, so it cannot drift from the part it checks.
- **X-axis belt drive** (`hardware/mechanical/x-drive/`): a NEMA 23 driving
  the stock X lead screw through a 2:1 GT2 belt, bolted to the mill's existing
  bearing-seat plate with no drilling or modification. A 40T pulley takes the
  place of the dial and handwheel on the screw's keyed stub and is held by the
  stock M8 nut; the bracket registers on the bearing boss rather than on its
  two M5s, which share one line and so cannot resist the motor's overhang.
- Mechanical parts are built from scripts (`build.py`), not saved documents.
  Geometry is audited numerically - interference between parts fails the
  build, all 40 tooth grooves are probed against their computed root and land
  radii, and an STL that is not solid, is non-manifold or self-intersects is
  refused.
- `Drive` in the machine model: a belt reduction between motor and screw now
  multiplies `steps_per_mm`. The CAD reads its tooth counts from the TOML, so
  the reduction cannot drift between the model and the metal.
- Measured reference dimensions for the stock X lead screw end and the X-axis
  end plate, with the WEN parts list corroborating each one.
- CI: `verify`, `lint` and `test` on every push and pull request, and a
  changelog gate so AGENTS.md section 8 is enforced rather than merely stated.
- `freecad-part` skill for building, verifying, rendering and exporting a
  mechanical part.

### Changed

- **X is on the stock lead screw, not a 1605 ballscrew.** The screw end was
  measured and is unmistakably stock. `screw_pitch_mm` for X is now a
  PROVISIONAL 2.0 and is the most dangerous unmeasured number in the project:
  every X scale and feed derives from it. See ADR-0009.
- X microstepping 32x -> 16x and max velocity 41.67 -> 10 mm/s. The 2:1
  reduction on a 2 mm lead demanded 266,688 Hz at the old figures, past the
  DM542T's 200 kHz ceiling; the constraint checker refused to generate, which
  is what it is for. X is now 3200 steps/mm at 32 kHz, and the ceiling is the
  motor (600 rpm) rather than the driver.

### Fixed

- **The bolt line sits 15.7 mm above the screw axis**, measured two
  independent ways that agree to 0.6 mm: top edge to the TOP of the Ø35
  boss (19.40 + 17.5 = 36.90 below the top edge) and top edge to the BOTTOM
  of its lobe (54.99 − 17.5 = 37.49). `params.py` computes both and refuses
  to load if they disagree by more than 1.5 mm. Four earlier attempts at
  this one dimension spanned 25 mm and every one inferred it from something
  else rather than measuring it.
- **The screw is not central and the plate is 45.42 tall.** It sits 37.2
  down a 45.42 plate, 8.2 above the bottom edge, with the boss lobe hanging
  about 9 mm past that edge. An earlier revision had the plate 73.8 tall on
  the assumption the screw was centred, and sized the backplate from it.
  The backplate now stops just past the lobe instead of hanging in free air.
- Slots kept, at 16 mm travel, even though the offset is now known. They
  cost nothing, and the register bore does the locating regardless.
- The pulley's tooth-profile audit probed a plane the assembled part no longer
  occupied, so every groove read as empty material. Probe coordinates now come
  from `params.py` instead of being written as literals.

### Added

- **A 1:1 paper template** of the X bracket's mounting face
  (`template.py` + `lib/template_sheet.py`). The outline is sliced from the
  FitPlate solid rather than drawn again, so it cannot drift from the part;
  the sheet carries a 100 mm bar to prove the print was not fitted to the
  page. Cheaper than plastic and faster than a print.
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

- Pendant node brought up on a Waveshare RP2040-Zero: MicroPython 1.29.0
  flashed, `dwin_t5uic1` driver deployed, and the protocol stack self-tested
  against a loopback transport (frames encode correctly; no panel attached
  yet). Its USB serial is recorded, so the generated udev rule now pins the
  device instead of warning.
- Panel orientation recorded explicitly: the stock CFG boots rotated, giving a
  272x480 portrait frame, while our screens are landscape. The firmware must
  call `set_orientation(0)` at startup, and a test now asserts the TOML and
  `ui/dwinui` agree about which way up the panel is.
- `hardware/electrical/pendant-wiring.md` with the RP2040-Zero pin mapping.

- `dwinui` command line: `check`, `preview`, `ops` and `export`. `export`
  turns a screen into a MicroPython module the pendant replays, so the browser
  preview and the panel are driven from one SVG.
- Pendant firmware skeleton (`firmware/pendant/main.py`) and a
  `/deploy-pendant` skill.

### Fixed

- **The renderer could silently revert a build.** It saved every open
  document before closing it, so a stale copy left open in the FreeCAD GUI
  overwrote a newer build on disk - a part vanished from the model twice
  before the cause was found. It now renders a throwaway copy, and redirects
  the save of any already-open document to a scratch file so closing still
  cannot raise the prompt that blocks the GUI thread.
- **Pendant beeper could be silently dead after a restart.** A MicroPython
  program killed mid-tone leaves its PWM slice configured, and the next
  program inherited that state - a buzzer that made no sound, with no error,
  looking exactly like a broken wire. `Chimes` now resets the pin before
  claiming it. Reproduced deliberately and verified to recover.
- **VNC on the Pi.** `raspi-config nonint do_vnc 0` reports success while
  driving a RealVNC service the image does not have. The image is X11 under
  lightdm, not Wayland/labwc as assumed; `x11vnc` on the live `:0` display
  fixes it and shows the same desktop AXIS will run on.

- **Homing order.** The generator emitted `HOME_SEQUENCE` in XYZ order, which
  homes the table before Z retracts - with a tool in the spindle and a vise on
  the table, the first homing run of the day would crash the cutter. Z now
  takes sequence 0, asserted in both the helper and the rendered INI, and a
  constraint check refuses any config where another axis homes at or before Z.

- Pendant panel verified on hardware: wiring correct, two-way comms, and the
  generated DRO screen rendering on the glass.

- Realtime latency measured on the Pi: 231 us worst case under load
  (`performance` governor), 23% of the 1 kHz servo period. Recorded with the
  conditions in `docs/commissioning/latency.md`.
- `pi/provision/cpu-governor.service` pins the CPU governor to `performance`.

- Pendant UI system: user stories, input model and design system in
  `docs/ui/README.md`, and five screens - DRO, JOG, RUN, DIAG and ALARM.
- `data-bind` widgets in the SVG compiler. A screen now compiles to static
  chrome plus named regions the firmware redraws in place, which is what
  makes a live UI fit in the panel's 11.5 KB/s.
- Xbox controller as the primary jog input, read natively by LinuxCNC's
  `hal_input`. Its deadman, watchdog and deadzone are in the machine
  description and asserted by tests (ADR-0008).

- Pendant chimes (`firmware/pendant/chimes.py`): a non-blocking sequencer
  and 14 cues, each written to scan like the words it stands for, with a
  policy that keeps anything merely confirming a visible action silent by
  default.
- Knob, button and beeper verified on hardware, including that the stock
  knob is 4 quadrature counts per detent.

- Pendant board moved onto the Pi. `mpremote` installed there in a venv at
  `/opt/cnc-tools`, udev rule installed, and `/dev/cnc/pendant` verified
  driving the board end to end.

### Fixed

- **The plate is 117 wide and its bolt holes are symmetric**, from a traced
  model of the plate calibrated against two features whose true size was
  already known. Scaling it by the 72 mm bolt pitch and by the 45.42 mm
  plate height agree to 1.4%, and hole-below-top falls out at 21.0-21.3
  against 21.5 measured on the machine - an independent check that the
  trace is sound. Holes sit 22.7 from the left edge and 22.2 from the right,
  so an earlier guess that they were off-centre was wrong. Affects the
  reference model and the photo gauge only; the backplate is 96 wide and
  fits either way.
- **udev rules used the wrong case for USB serials.** The generator emitted
  the serial as written in the TOML, which is conventionally uppercase
  because that is how MicroPython prints `machine.unique_id()`. udev matches
  case-sensitively against a descriptor that is lowercase, so the rule never
  fired - no error, no symlink, and the device left on a bare `/dev/ttyACM*`
  whose number depends on enumeration order. Now lowercased, with a test.

- Pendant `main.py`: draws the DRO chrome and stands by showing NO HOST with
  a heartbeat, so a powered board is never indistinguishable from a dead one.
  It shows dashes rather than zeros - a pendant displaying plausible numbers
  that nothing is measuring is worse than one showing none.

### Changed

- **Panel orientation is portrait, not landscape.** Measured on the bench by
  sweeping all four orientations: 1 reads upright, giving a 272x480 frame.
  `ui/dwinui`, the DRO screen and the pendant firmware were all built around
  480x272 landscape and have been flipped. The cross-check test between the
  TOML and the compiler caught every place that disagreed.

### Notes

- Values marked PROVISIONAL in the machine description are starting points,
  not measurements. They must be confirmed during commissioning before the
  machine cuts anything.

[Unreleased]: https://github.com/jajmangold/wen-33013-cnc/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/jajmangold/wen-33013-cnc/releases/tag/v0.1.0
