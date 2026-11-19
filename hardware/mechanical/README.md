# Mechanical

Printed and machined parts, built from scripts. `build.py` is the source; the
`.FCStd` is a build artifact and is not committed.

| Part | What | Status |
|---|---|---|
| [`x-drive/`](x-drive/) | 2:1 GT2 belt drive, NEMA 23 onto the stock X lead screw | 3 dimensions still ASSUMED |

## Why scripts

Tooth counts, belt pitch and belt width decide `steps_per_mm`, so they are
read from `machine/wen33013.toml` rather than typed into the CAD. Change the
reduction in one place and the pulley, the LinuxCNC INI and the firmware
header all follow. A drawing cannot do that.

The rest - what the screw end actually measures, how thick a web should be -
lives in each part's `params.py`, tagged with where it came from:

| Tag | Means |
|---|---|
| `MEASURED` | calipers on the machine |
| `MANUAL` | the WEN 33013 parts list |
| `STEP` | a third-party conversion model, used only for stock geometry |
| `ASSUMED` | a placeholder. **Do not cut metal against one.** |

## Building

```bash
cd hardware/mechanical/x-drive
FreeCADCmd build.py      # geometry, clash audit
FreeCADCmd verify.py     # numeric audit
FreeCADCmd export.py     # STLs + mesh audit
```

FreeCAD 1.0, no addons needed. On Windows, `FreeCADCmd` is
`"C:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe"`.

Renders need a running FreeCAD **GUI** with the MCP addon, because
FreeCADCmd has no viewport:

```bash
python ../lib/render.py x-drive/wen_x_drive.FCStd ../../docs/renders 9879
```

## Verification

Nothing here is checked by eye. `build.py` fails on any interference between
parts, `verify.py` probes all 40 tooth grooves with `Shape.isInside` and
checks they sit at the computed root and land radii, and `export.py` refuses a
mesh that is not solid, is non-manifold, or self-intersects.

That matters more than it sounds: a boolean that severs a part returns a
perfectly *valid* shape with two solids, and nothing complains until the STL
is already on the bed.
