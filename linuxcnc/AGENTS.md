# AGENTS.md - LinuxCNC configuration

Root `AGENTS.md` applies. This adds the rules for the host side.

## Generated vs hand-written

| Path | Status |
|---|---|
| `configs/wen33013/wen33013.ini` | **GENERATED** - never edit |
| `hal/*.hal` | hand-written glue |
| `components/` | hand-written HAL components, **GPL-2.0** |

The INI carries a `DO NOT EDIT` banner and a `source-fingerprint`. If it needs
to say something new, change the generator in `tools/machinegen/emit.py`.

## The rule for HAL files

**No numbers in HAL files.** Not scales, not limits, not velocities.

Every machine-dependent value comes from the INI via `[SECTION]NAME`
substitution, and the INI is generated from the machine model. A number typed
into a HAL file is a second source of truth, and the whole architecture exists
to prevent exactly that. If you find one, it is a bug - move it to
`machine/wen33013.toml`.

HAL files may contain: pin names, `net` statements, component loading,
thread assignment, and `[SECTION]NAME` references.

## Licensing

`components/` links against LinuxCNC and is therefore **GPL-2.0**, with its
own LICENSE file. The rest of the repo is MIT. Do not move code between them
without reading root `AGENTS.md` section 7.

Note LinuxCNC's `hal_lib` is LGPL-2 even though the project COPYING is GPL-2 -
that is what makes a GPL-3 pendant workable alongside this.

## Safety

- Soft limits come from the model and are never relaxed to "get a job to fit".
  If the travel is genuinely larger, measure it and update the TOML.
- E-stop handling in HAL **observes** the hardwired chain (ADR-0007). It is
  not the stop mechanism, and nothing here may be written as though it were.
- `estop.hal` must fault the machine when the chain opens. Test this by
  actually pressing the button, not by forcing the pin.

## Testing

- `tests/integration` runs on the Pi with LinuxCNC installed and asserts the
  config loads - `halrun -f` on the HAL files, and a config-load check.
  Mark them `@pytest.mark.integration`.
- A config that loads is not a config that is correct. Scale, direction and
  limits are proven by `/commission-axis` against a physical indicator, not
  by anything that can run in CI.
