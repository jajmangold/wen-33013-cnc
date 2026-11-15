---
name: regen
description: Regenerate every machine-derived file from machine/wen33013.toml, then prove nothing drifted. Use after ANY edit to the machine description, or when a generated file looks out of date, or when `make verify` reports a stale file.
when_to_use: Run immediately after changing machine/wen33013.toml. Also run when LinuxCNC and the firmware appear to disagree about scale, feeds or limits.
allowed-tools: Bash(make *) Bash(python *) Read Edit
---

## Regenerate machine-derived files

Current state:

```!
make check
make verify
```

### Procedure

1. **Validate first.** If `make check` reported any `[ERROR]`, STOP. Do not
   generate from an invalid machine description - it produces output that
   looks plausible and is wrong. Fix the TOML and start again.

2. `[WARNING]` lines are expected and informative. In particular, "encoder
   resolves N um, coarser than the M um microstep" is normal for our
   belt-mounted encoders and is not a fault.

3. Regenerate:

   ```bash
   make gen
   ```

4. **Run the tests.** Generation is not the proof; the tests are.

   ```bash
   make test
   ```

   `tests/unit/test_emit.py::TestScaleAgreement` is the one that matters: it
   asserts the INI and the firmware header carry the same steps/mm. If that
   fails, the machine would cut at the wrong scale.

5. **Review the diff of generated files** before committing. A change you did
   not expect means the TOML edit did more than you intended.

   ```bash
   git diff --stat
   git diff linuxcnc/ firmware/ pi/provision/99-cnc-nodes.rules
   ```

6. Add a line to `CHANGELOG.md` under `## [Unreleased]` describing the
   *machine* change - not the regeneration.

### Rules

- NEVER hand-edit a file carrying the `DO NOT EDIT` banner.
- If a generated file needs to say something the generator cannot produce,
  change the generator, not the output.
- Commit the TOML change and the regenerated files together. Splitting them
  leaves the repo in a state where `make verify` fails.
