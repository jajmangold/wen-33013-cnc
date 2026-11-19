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

## Measuring the machine

Dimensions taken off an uncalibrated photograph got the X bracket wrong
twice - once by 25 mm, and once by deleting a boss that was really there.
So photos now carry their own scale.

```bash
pip install -e ".[measure]"
python lib/charuco.py board docs/charuco_board.png   # print at 100%
python lib/charuco.py rectify photo.jpg out.png      # square-on, metric
python lib/charuco.py probe   photo.jpg x1 y1 x2 y2  # distance in mm
```

Print the board **at 100%, no fit-to-page** - it carries a 100 mm bar so you
can check with a rule - and tape it flat on the surface being measured. The
board is 110 x 40 mm, which fits the X end plate with the boss free to cover
the middle; ChArUco reads whatever corners it can see, so occlusion is fine.

`rectify` warps the photo into a square-on view where one pixel is a known
fraction of a millimetre, and overlays a 10 mm grid. Anything **coplanar
with the board** can then be measured straight off it. Features standing
proud - a boss face, a pulley - are in a different plane and still need
their own board or a caliper.

Every run prints a reprojection error. Under ~0.05 mm the mapping is sound;
a large one means the board was not flat and the millimetres are a lie.
Tested against a synthetic oblique view in `tests/unit/test_charuco.py`,
where a 92 mm span measures true to 12 um.

`opencv-contrib-python` is a **dev-only** extra. Nothing on the Pi imports
it and the runtime stays dependency-free.
