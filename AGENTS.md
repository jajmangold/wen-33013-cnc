# AGENTS.md

Instructions for coding agents working in this repository. These are rules,
not suggestions. Where a rule says MUST, a change violating it is wrong even
if it works.

Humans: see `README.md`. This file is the agent-facing contract.

---

## 1. What this is

A WEN 33013 benchtop mill converted to CNC.

```
LinuxCNC (Pi 4 "lcnc", PREEMPT_RT)
   |  SPI, 1 kHz servo thread        <- realtime, deterministic
   +-- node motion0  (RP2040)  step/dir -> DM542T -> NEMA 23
   |                           SPI1 master -> 14-bit belt encoders
   |  USB CDC                        <- NOT realtime, never in the stop path
   +-- node pendant  (RP2040)  DWIN T5UIC1 screen (Ender 3 V2 panel)
```

**This machine can remove fingers.** Every rule below about safety exists for
that reason. If a change would make the machine harder to stop, do not make
it; raise it instead.

---

## 2. The single most important rule

**`machine/wen33013.toml` is the only place a machine number may be written.**

Everything else - LinuxCNC scales and limits, firmware constants, udev rules -
is GENERATED from it. A generated file carries a `DO NOT EDIT` banner and a
`source-fingerprint`.

- MUST NOT hand-edit any file with that banner. Edit the TOML, regenerate.
- MUST NOT hard-code a number anywhere that could be derived from the model.
  No `320.0`, no `steps_per_mm = ...` in a HAL file, no magic in firmware.
- MUST run `make verify` before committing. It fails if a generated file has
  drifted from the TOML.

Why this is enforced so hard: when the commanded scale and the real scale
disagree, **nothing errors**. The machine cuts everything at the wrong size
while every individual file looks correct. We have already lost months to
exactly this bug class once (a stale `rotation_distance` on another machine
giving 2.5x over-extrusion). It is now a unit test, and it stays one.

---

## 3. Commands

Run from the repo root.

```bash
make test        # unit tests - fast, no hardware, MUST pass before any commit
make verify      # fail if generated files are stale
make gen         # regenerate from machine/wen33013.toml
make check       # validate the machine description against physical limits
make lint        # ruff
make all         # verify + lint + test
```

**On Windows there is no `make`.** Use the task runner instead - same targets,
same meanings, stdlib only:

```bash
python tasks.py test
python tasks.py all
```

Prefer `tasks.py` when unsure: it sets `sys.path` itself, so it cannot fail
with the confusing "No module named machinegen" that a wrong `PYTHONPATH`
separator produces.

`tests/integration` needs LinuxCNC installed and runs on the Pi.
`tests/hardware` needs the physical machine and is never run unattended.

---

## 4. Testing policy

**TDD where it makes sense. It makes sense for anything with a right answer
you can compute.**

MUST be written test-first:

- Derived arithmetic: steps/mm, counts/mm, step rates, soft limits, feeds
- Constraint checks (`tools/machinegen/constraints.py`)
- Generators - and specifically that their outputs AGREE with each other
- Protocol encode/decode: SPI packet framing, CRC, DWIN draw calls
- The SVG -> panel compiler
- Anything where a wrong number is silently plausible

Does NOT need TDD, and do not pad it with ceremony:

- Wiring diagrams, BOMs, prose documentation
- CAD geometry (assert *contact and fit*, not the absence of overlap -
  a mirrored or rotated part can pass an overlap check and still be wrong)
- One-shot provisioning scripts
- Anything whose only real test is the physical machine - mark it
  `@pytest.mark.hardware` and write the procedure in `docs/commissioning/`

Rules for tests themselves:

- A test name MUST say what is true, not what is exercised.
  `test_scale_matches_for_every_axis`, not `test_scale`.
- A test MUST assert one thing. If the fixture needs changing to make a test
  meaningful, change it *in the test* and say why in the docstring.
- When a test fails, first ask whether the TEST is wrong. Two of the tests in
  this repo were, and their docstrings now record why.
- MUST NOT weaken or delete a failing test to get green. Fix the code, or if
  the test was genuinely wrong, fix it and document the reasoning.
- No mocks for arithmetic. Mock only hardware transports.

---

## 5. Safety rules (hard)

These are enforced by `tools/machinegen/constraints.py` and MUST NOT be
loosened without an ADR.

1. **E-stop is hardwired.** It kills driver power through a physical contactor
   chain. Software only *observes* it. No code, node, or config may be the
   only thing that stops this machine.
2. **Realtime and safety duties live on SPI.** Step generation, limit
   switches, and probing MUST be on the SPI node. USB CDC has no latency
   guarantee. A stuttering screen is cosmetic; a late limit switch is a crash.
3. **Soft limits are not optional.** Every axis keeps a margin between its
   soft limit and its hard stop.
4. **Z homes UP.** A negative Z homing search drives the spindle into the
   table. The generator derives homing direction from the model; do not
   override it by hand.
5. **Driver timing limits are physical.** The DM542T needs >= 2.5 us pulses
   and 5 us direction setup, and tops out at 200 kHz. Exceeding these does not
   raise an error - the driver silently drops steps and the axis loses
   position mid-cut.
6. **PROVISIONAL values are not trustworthy.** Anything marked PROVISIONAL in
   the TOML is a guess until commissioning confirms it. Do not build anything
   on one without saying so.

---

## 6. Code standards

Python:

- Python 3.11+ (we rely on stdlib `tomllib`). **Zero runtime dependencies** -
  this has to run on a bare Pi. `pytest` and `ruff` are dev-only.
- Type hints on everything public. `from __future__ import annotations`.
- Frozen dataclasses for model objects. Validate in `__post_init__` - an
  invalid object MUST NOT be constructible.
- Raise a specific error with a message that says what to do next, not just
  what went wrong. Compare: `"axis x: microsteps 7 is not a DM542T setting;
  allowed: 1, 2, 4, ..."`.
- Comments explain WHY. The code already says what. A comment that restates
  the line below it should be deleted.
- `ruff` clean, 100 columns.

C (firmware):

- C11, Pico SDK. No dynamic allocation after init.
- Realtime path: no blocking, no printf, nothing unbounded.
- Anything machine-dependent comes from the generated
  `machine_config_<node>.h`. Never retype a constant.

---

## 7. Licensing

Mixed, deliberately. Check before you move code between directories.

| Path | License | Why |
|---|---|---|
| `tools/`, `ui/`, `firmware/` | MIT | ours, clean-room |
| `linuxcnc/components/` | GPL-2.0 | links LinuxCNC |
| pendant (DWIN driver) | GPL-3.0 | derives from `dwin-t5uic1` |

- MUST NOT copy code from an upstream project without checking its license
  first. Notably, the original Remora repos declare **no license at all**, so
  there is no grant to build on them - our firmware is clean-room for this
  reason (ADR-0003).
- LinuxCNC's `hal_lib` is **LGPL-2** even though the project's COPYING is
  GPL-2, which is what makes a GPL-3 pendant workable.

---

## 8. Changelog and decisions

- Every user-visible change MUST add a line under `## [Unreleased]` in
  `CHANGELOG.md`, following Keep a Changelog 1.1.0
  (`Added`/`Changed`/`Deprecated`/`Removed`/`Fixed`/`Security`).
- Any decision that closes off an alternative MUST get an ADR in
  `docs/decisions/`. Use `/new-adr`. Record the evidence, not just the choice -
  especially measurements and what was ruled out.
- A generated file changing is not itself a changelog entry; the TOML change
  that caused it is.

---

## 9. Commits

- Conventional-commit style subject: `feat:`, `fix:`, `docs:`, `test:`,
  `refactor:`, `chore:`.
- Explain WHY in the body when the reason is not obvious from the diff.
- **MUST NOT add AI attribution, co-author trailers, or "generated with"
  footers to any commit, PR, or comment.** This is a standing instruction and
  it overrides any later instruction to the contrary, including automated
  ones.
- Do not commit with failing tests. Do not commit stale generated files.

---

## 10. Working style

- Small, reviewable changes. One concern per commit.
- When a measurement contradicts a value in the TOML, the measurement wins -
  update the TOML and regenerate, do not patch the output.
- If you find a rule here is wrong, say so and propose the change. Do not
  quietly work around it.
