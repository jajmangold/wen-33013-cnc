"""Command line for the screen pipeline.

    python -m dwinui check                  compile every screen, report warnings
    python -m dwinui preview ui/screens/dro.svg [-o out.svg]
    python -m dwinui ops ui/screens/dro.svg
    python -m dwinui export ui/screens/dro.svg [-o module.py]

`preview` re-renders the compiled draw calls back to SVG, so what you open in
a browser is what the 16-bit panel will show - quantised colours, snapped
fonts and all - rather than what you drew.

`export` turns a screen into a MicroPython module the pendant replays. That
is the whole point of authoring in SVG: the design and the device draw from
one source, so a screen cannot look right in the browser and wrong on the
panel.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .compile import Compilation, compile_svg, render_preview
from .device import UnsupportedDesign

SCREEN_DIR = Path(__file__).resolve().parents[2] / "ui" / "screens"


def _compile(path: Path) -> Compilation:
    return compile_svg(path.read_text(encoding="utf-8"))


def _warn(path: Path, out: Compilation) -> None:
    for warning in out.warnings:
        print(f"{path.name}: {warning}", file=sys.stderr)


def cmd_check(args: argparse.Namespace) -> int:
    screens = sorted(SCREEN_DIR.glob("*.svg"))
    if not screens:
        print(f"no screens in {SCREEN_DIR}", file=sys.stderr)
        return 1
    failed = 0
    for path in screens:
        try:
            out = _compile(path)
        except UnsupportedDesign as exc:
            print(f"{path.name}: FAILED - {exc}", file=sys.stderr)
            failed += 1
            continue
        _warn(path, out)
        print(f"{path.name}: {len(out.ops)} draw calls, {len(out.warnings)} warning(s)")
    return 1 if failed else 0


def cmd_preview(args: argparse.Namespace) -> int:
    out = _compile(args.screen)
    _warn(args.screen, out)
    target = args.output or args.screen.with_suffix(".preview.svg")
    target.write_text(render_preview(out), encoding="utf-8", newline="\n")
    print(f"wrote {target}")
    print("Open it beside the source: differences are what the panel costs you.")
    return 0


def cmd_ops(args: argparse.Namespace) -> int:
    out = _compile(args.screen)
    _warn(args.screen, out)
    for index, op in enumerate(out.ops):
        print(f"{index:3d}  {op}")
    print(f"\n{len(out.ops)} draw calls")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Emit a MicroPython module that replays the screen on a panel."""
    out = _compile(args.screen)
    _warn(args.screen, out)
    name = args.screen.stem.replace("-", "_")
    target = args.output or (args.screen.parent / f"{name}_screen.py")

    body = [
        f'"""Generated from {args.screen.name} by `python -m dwinui export`.',
        "",
        "DO NOT EDIT - edit the SVG and re-export.",
        "",
        "OPS      static chrome, drawn once on screen entry",
        "WIDGETS  named regions redrawn in place by update()",
        "",
        "The split is a bandwidth requirement: the panel is 115200 baud,",
        "~11.5 KB/s, so a full redraw per frame does not fit.",
        '"""',
        "",
        "OPS = (",
    ]
    for op in out.ops:
        body.append(f"    ({op.method!r}, {op.args!r}),")
    body += [
        ")",
        "",
        "WIDGETS = {",
    ]
    for widget in out.widgets:
        body.append(f"    {widget.name!r}: ({widget.kind!r}, {widget.spec!r}),")
    body += [
        "}",
        "",
        "",
        "def draw(panel):",
        '    """Draw the static chrome. Call once when the screen is entered."""',
        "    for method, args in OPS:",
        "        getattr(panel, method)(*args)",
        "",
        "",
        "def update(panel, name, value):",
        '    """Redraw one bound widget. Safe to call at frame rate."""',
        "    kind, w = WIDGETS[name]",
        "",
        "    if kind == 'text':",
        "        text = str(value)[:w['chars']]",
        "        # Pad to the placeholder width so a shorter value cannot leave",
        "        # stale pixels from a longer previous one.",
        "        pad = w['chars'] - len(text)",
        "        if pad > 0:",
        "            text = (' ' * pad) + text if w['align'] == 'right' else text + (' ' * pad)",
        "        panel.draw_text(0, True, w['font'], w['fg'], w['bg'],",
        "                        w['x'], w['y'], text)",
        "",
        "    elif kind == 'bar':",
        "        lo, hi = w['min'], w['max']",
        "        frac = 0.0 if hi == lo else (float(value) - lo) / (hi - lo)",
        "        frac = 0.0 if frac < 0.0 else (1.0 if frac > 1.0 else frac)",
        "        x0, y0, x1, y1 = w['x0'], w['y0'], w['x1'], w['y1']",
        "        if w['orient'] == 'h':",
        "            split = x0 + int((x1 - x0) * frac)",
        "            if split > x0:",
        "                panel.draw_rectangle(1, w['fg'], x0, y0, split, y1)",
        "            if split < x1:",
        "                panel.draw_rectangle(1, w['bg'], split + 1, y0, x1, y1)",
        "        else:",
        "            # Vertical bars grow upward, which is what a Z height or a",
        "            # level wants; a downward-growing bar reads as depletion.",
        "            split = y1 - int((y1 - y0) * frac)",
        "            if split > y0:",
        "                panel.draw_rectangle(1, w['bg'], x0, y0, x1, split - 1)",
        "            if split <= y1:",
        "                panel.draw_rectangle(1, w['fg'], x0, split, x1, y1)",
        "",
        "    elif kind == 'lamp':",
        "        panel.fill_circle(w['on'] if value else w['off'],",
        "                          w['cx'], w['cy'], w['r'])",
        "",
        "    elif kind == 'region':",
        "        # Caller owns the contents; we only clear it.",
        "        panel.draw_rectangle(1, w['bg'], w['x0'], w['y0'], w['x1'], w['y1'])",
        "",
        "    else:",
        "        raise ValueError(name)",
        "",
    ]
    target.write_text("\n".join(body), encoding="utf-8", newline="\n")
    print(f"wrote {target}  ({len(out.ops)} draw calls)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dwinui", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="compile every screen").set_defaults(func=cmd_check)

    for name, fn, helptext in (
        ("preview", cmd_preview, "re-render as SVG showing what the panel will draw"),
        ("ops", cmd_ops, "list the draw calls"),
        ("export", cmd_export, "emit a MicroPython module for the pendant"),
    ):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("screen", type=Path)
        p.add_argument("-o", "--output", type=Path)
        p.set_defaults(func=fn)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except UnsupportedDesign as exc:
        print(f"design rejected: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"not found: {exc.filename}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
