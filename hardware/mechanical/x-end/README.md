# X end housing

Replaces the stock X-axis bearing seat. Bolts to the **same two M6 holes** in
the table casting and supports the screw on a **preloaded pair of 6000-2RS**
instead of one single-direction thrust bearing. See
[ADR-0010](../../../docs/decisions/0010-x-end-housing-replaces-the-stock-plate.md).

![housing](../../../docs/renders/x-end-housing.png)

```bash
cd hardware/mechanical/x-end
FreeCADCmd build.py
```

## Why

The stock screw is located axially by one 8200 thrust bearing, preloaded by
the handwheel nut. **That preload is the X backlash**, and it is set by how
hard someone did a nut up. A preloaded pair takes both axial directions and
all the radial load together.

## The budget, and why it is the whole design

Origin: `X = 0` at the **table's end face** - the machined face the stock
plate bolts to. Note this is *not* the x-drive origin, which sits on the
stock plate's outer face, 12 mm further out.

Only **38 mm** of Ø10 land is outboard of that face. Everything lives in it:

```
  -16        0                                   25.4        38        51
   |  inner  | lip  brg1  spacer  brg2  clip web |  pulley   | thread  |
   |  spacer |                                   |           | nut ->50
   shoulder  table face                     housing ends   washer sits here
```

That 38 is **derived from three caliper readings**, none of them guesses:

| | |
|---|---|
| stock plate thickness | 12.0 |
| boss standing proud of the plate face | 16.0 |
| free keyed land beyond the stock stack | 10.0 |
| **land outboard of the table face** | **38.0** |

Cross-checked against the whole land measured off a ChArUco frame at
0.044 mm reprojection: **54 mm** shoulder-to-thread, self-calibrated two ways
(the shaft reads Ø10.07 across against a caliper 10.00; the thread reads 13.5
along against 12.99). 54 − 38 = 16 mm of shoulder inside the casting, which
is exactly how deep the stock bearing pocket is. Two routes, one answer.

## The constraint that sets everything

An M8 washer's ~8.4 bore **cannot pass over the Ø10 land**. So the pulley's
outboard face must *reach* the thread at 38, and the nut must still have
thread under it, so that face cannot go much past 41.9. Lip, two bearings,
spacer, circlip, web and the pulley's own width all fit in that window.

**The spacer is what is left over, not a choice.** `params.py` solves it and
refuses to build if it comes out under 3 mm:

```
pulley width   16.0 PROVISIONAL; this housing takes up to 17.6
spacer          4.6, solved
bearings        2.0..10.0 and 14.6..22.6, centres 12.6 apart
pulley         25.9..41.9     nut ends 50.0 of 51.0 -> 1.0 spare
```

So a **hubbed** pulley will not fit - at 21 mm wide the spacer vanishes.
Measure yours; it is the only free variable left on this side.

## One bore, one diameter

The 6000-2RS (10 × 26 × 8) and the stock 8200 thrust bearing (10 × 26 × 11)
share a **26 mm OD**. So the housing is a single Ø26 bore at a single depth,
and the stock thrust bearing stays a drop-in option in the same pocket if the
preloaded pair ever proves not stiff enough.

Retained by a seat at the inboard end (Ø20 × 2) and a DIN 472 circlip at the
outboard. The inboard end cannot be closed by the table face itself, because
the casting has the old bearing pocket there - which is also why the inner
spacer has to bridge 18 mm back to the shoulder.

## Bill of materials

| Qty | Item | Note |
|---|---|---|
| 1 | Housing | `build.py` |
| 2 | 6000-2RS, 10 × 26 × 8 | you have a stack of them |
| 1 | Inner spacer, Ø16 × Ø10.1 × 18 | turned; bridges the casting pocket |
| 1 | Outer spacer, Ø24 × Ø19 × 4.6 | sets the preload span |
| 1 | Circlip, DIN 472, 26 mm bore | |
| 2 | **M6 × 25** socket cap | replaces the stock M6 × 16 |
| 1 | 40T GT2, 10 mm bore, **≤ 17.6 wide** | yours - grub screw into the keyway |
| 1 | M8 nut + washer | reuse the stock ones |

The key comes **out**: it stands 1.5 proud and a plain Ø10 bore will not pass
over it. Grub screw into the empty slot, second at 90°.

## Not done yet

The **motor tower** is not on this part. It carries over from
[`../x-drive`](../x-drive) unchanged in principle - same bolt interface, same
access rules - but its centre distance depends on the tooth counts and belt
width, and those are still unconfirmed. Building it now would be building on
the one thing still unmeasured.

Still needed, and genuinely not in anything measured so far:

1. **Pulley width** - decides the spacer, above.
2. **Motor shaft diameter** - 10 mm bore pulleys need a 10 mm shaft; a
   NEMA 23 is usually 6.35 or 8.
3. **Tooth counts, both pulleys** - they drive `steps_per_mm`, so they go in
   `machine/wen33013.toml`, not here.
