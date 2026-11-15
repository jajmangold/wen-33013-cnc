# AGENTS.md - pendant screens

Root `AGENTS.md` applies. This covers the DWIN T5UIC1 panel (the Ender 3 V2
screen) and the SVG that drives it.

## How this works

Screens are authored as **SVG** in `ui/screens/`, compiled by `ui/dwinui/`
into T5UIC1 draw calls. The SVG is the source: open it in a browser to iterate
on layout, and use `render_preview()` to see what the 16-bit panel will
actually show after colour quantisation.

The driver primitives this targets: `clear`, `draw_rectangle`, `draw_line`,
`draw_circle` / `fill_circle`, `draw_polyline`, `draw_text`, `draw_bitmap`.

## Panel facts (not negotiable)

- **480 x 272**, RGB565.
- Ten fixed-pitch fonts, cell heights 12/16/20/24/28/32/40/48/56/64. There is
  no scaling. A design asking for 19 px gets the 20 px font.
- No alpha, no gradients, no transforms, no rotation.

## The supported SVG subset

`rect`, `line`, `circle`, `polyline`, `text`, `g` (flattened), plus
`data-background` on the root for a full-screen clear.

Everything else **raises**. This is deliberate: an element the panel cannot
draw is simply absent, and the way you discover it is an operator reaching for
a control that was never rendered. Compile-time failure on a dev machine is
cheaper.

Do not "fix" a rejection by loosening the compiler. Redesign with primitives
the panel has, or add the primitive properly with tests.

## Writing a screen

- Keep text inside the panel: an overflowing string is a compile error, which
  is correct - truncated text on a DRO is worse than no text.
- Prefer exact font cell heights (16, 20, 24, 32) to avoid snap warnings.
- Pick colours that survive RGB565. The compiler warns when a colour shifts by
  more than 8 per channel; take the warning seriously on anything conveying
  state, since a status green that quantises toward grey is a safety problem,
  not an aesthetic one.
- Status indicators should differ in **shape or position**, not only colour.
  The operator is across the shop looking at a small panel.

## Testing

Every screen in `ui/screens/` is automatically compiled and previewed by
`tests/unit/test_dwinui.py`. Adding an SVG adds its test coverage - a screen
that does not compile is a blank panel.

TDD applies fully to the compiler: it is pure logic with right answers.

## Licensing

`ui/` is MIT. The DWIN **driver** (`jajmangold/dwin-t5uic1`) is GPL-3.0 and
stays a separate dependency - do not vendor it into this directory, or this
directory becomes GPL-3.0.
