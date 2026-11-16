"""Compile a restricted SVG into T5UIC1 draw calls.

Why SVG: the screen layout is a design problem, and designing it in a text
editor as a list of coordinates is how you end up with a pendant nobody wants
to look at. An SVG can be opened in a browser, nudged, and diffed.

The subset is deliberately small - rect, line, circle, polyline, text - because
that is what the panel draws natively. Anything outside the subset raises
rather than being silently dropped, since a silently dropped element is a
control that is not on the screen when you reach for it.

Output is a list of `Op`s, each mapping onto one `T5UIC1Display` method, so the
pendant can replay them without carrying an SVG parser.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

from .device import (
    HEIGHT,
    WIDTH,
    Color,
    UnsupportedDesign,
    assert_on_screen,
    font_for_height,
    text_extent,
)

SVG_NS = "{http://www.w3.org/2000/svg}"

SUPPORTED_TAGS = {"svg", "rect", "line", "circle", "polyline", "text", "g", "title", "desc"}

# Attributes that change rendering in ways the panel cannot reproduce.
REJECTED_ATTRS = {
    "opacity", "fill-opacity", "stroke-opacity", "transform",
    "stroke-dasharray", "filter", "clip-path", "mask",
}


@dataclass(frozen=True)
class Op:
    """One panel draw call. `method` names a T5UIC1Display method."""

    method: str
    args: tuple[Any, ...]

    def __str__(self) -> str:
        return f"{self.method}{self.args}"


@dataclass(frozen=True)
class Widget:
    """A named region the firmware redraws in place.

    The panel is a 115200 baud serial device - about 11.5 KB/s. Redrawing a
    whole screen at 10 Hz does not fit in that, so static chrome is drawn once
    at screen entry and only these small bound regions are updated per frame.
    That is a bandwidth requirement, not an optimisation.
    """

    name: str
    kind: str                      # text | bar | lamp | region
    spec: dict[str, Any]


@dataclass
class Compilation:
    ops: list[Op] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    widgets: list[Widget] = field(default_factory=list)

    def widget(self, name: str) -> Widget:
        for w in self.widgets:
            if w.name == name:
                return w
        raise KeyError(name)


def _num(el: ET.Element, attr: str, default: float | None = None) -> float:
    raw = el.get(attr)
    if raw is None:
        if default is None:
            raise UnsupportedDesign(f"<{_tag(el)}> is missing required attribute {attr!r}")
        return default
    try:
        return float(str(raw).strip().removesuffix("px"))
    except ValueError:
        raise UnsupportedDesign(f"<{_tag(el)}> {attr}={raw!r} is not a number") from None


def _tag(el: ET.Element) -> str:
    return el.tag.removeprefix(SVG_NS)


def _colour(el: ET.Element, attr: str, default: str | None) -> Color | None:
    raw = el.get(attr, default)
    if raw is None or raw == "none":
        return None
    return Color.from_hex(raw)


def _check_attrs(el: ET.Element) -> None:
    for attr in el.attrib:
        if attr in REJECTED_ATTRS:
            raise UnsupportedDesign(
                f"<{_tag(el)}> uses {attr!r}, which the T5UIC1 cannot render. "
                f"Express the intent with solid shapes instead."
            )


def _note_quantisation(colour: Color, where: str, out: Compilation) -> None:
    if colour.quantisation_error > 8:
        out.warnings.append(
            f"{where}: {colour.to_hex()} shifts to "
            f"{colour.quantised.to_hex()} on a 16-bit panel"
        )


def _compile_rect(el: ET.Element, out: Compilation) -> None:
    x, y = int(_num(el, "x", 0)), int(_num(el, "y", 0))
    w, h = int(_num(el, "width")), int(_num(el, "height"))
    x1, y1 = x + w - 1, y + h - 1
    assert_on_screen("<rect>", x, y, x1, y1)

    fill = _colour(el, "fill", None)
    stroke = _colour(el, "stroke", None)
    if fill is None and stroke is None:
        raise UnsupportedDesign("<rect> has neither fill nor stroke; it would be invisible")
    if fill is not None:
        _note_quantisation(fill, "<rect> fill", out)
        out.ops.append(Op("draw_rectangle", (1, fill.rgb565, x, y, x1, y1)))
    if stroke is not None:
        _note_quantisation(stroke, "<rect> stroke", out)
        out.ops.append(Op("draw_rectangle", (0, stroke.rgb565, x, y, x1, y1)))

    name = _bind_name(el)
    if name is None:
        return

    kind = el.get("data-widget", "region")
    if kind == "bar":
        track = _colour(el, "data-track", "#161d26")
        value_colour = _colour(el, "data-fill", "#5ac57a")
        assert track is not None and value_colour is not None
        _add_widget(
            out, name, "bar",
            {
                "x0": x, "y0": y, "x1": x1, "y1": y1,
                "fg": value_colour.rgb565,
                "bg": track.rgb565,
                "min": _num(el, "data-min", 0.0),
                "max": _num(el, "data-max", 100.0),
                "orient": el.get("data-orient", "h"),
                "centre": el.get("data-centre", "0") == "1",
            },
        )
    elif kind == "region":
        # The firmware owns everything inside: envelope map, spindle tick.
        # We only guarantee the bounds and what to clear it to.
        clear_to = _colour(el, "data-clear", "#0d1117")
        assert clear_to is not None
        _add_widget(
            out, name, "region",
            {"x0": x, "y0": y, "x1": x1, "y1": y1, "bg": clear_to.rgb565},
        )
    else:
        raise UnsupportedDesign(
            f"<rect data-widget={kind!r}> is not a known widget "
            f"(bar, region)"
        )


def _compile_line(el: ET.Element, out: Compilation) -> None:
    x0, y0 = int(_num(el, "x1")), int(_num(el, "y1"))
    x1, y1 = int(_num(el, "x2")), int(_num(el, "y2"))
    assert_on_screen("<line>", min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
    stroke = _colour(el, "stroke", None)
    if stroke is None:
        raise UnsupportedDesign("<line> needs a stroke colour")
    _note_quantisation(stroke, "<line>", out)
    out.ops.append(Op("draw_line", (stroke.rgb565, x0, y0, x1, y1)))


def _compile_circle(el: ET.Element, out: Compilation) -> None:
    cx, cy, r = int(_num(el, "cx")), int(_num(el, "cy")), int(_num(el, "r"))
    assert_on_screen("<circle>", cx - r, cy - r, cx + r, cy + r)
    fill = _colour(el, "fill", None)
    stroke = _colour(el, "stroke", None)
    if fill is not None:
        _note_quantisation(fill, "<circle> fill", out)
        out.ops.append(Op("fill_circle", (fill.rgb565, cx, cy, r)))
    if stroke is not None:
        _note_quantisation(stroke, "<circle> stroke", out)
        out.ops.append(Op("draw_circle", (stroke.rgb565, cx, cy, r)))
    if fill is None and stroke is None:
        raise UnsupportedDesign("<circle> has neither fill nor stroke")

    name = _bind_name(el)
    if name is not None:
        on = _colour(el, "data-on", "#5ac57a")
        off = _colour(el, "data-off", "#2d3b4e")
        assert on is not None and off is not None
        _add_widget(
            out, name, "lamp",
            {"cx": cx, "cy": cy, "r": r, "on": on.rgb565, "off": off.rgb565},
        )


def _compile_polyline(el: ET.Element, out: Compilation) -> None:
    raw = el.get("points", "").replace(",", " ").split()
    if len(raw) < 4 or len(raw) % 2:
        raise UnsupportedDesign("<polyline> needs an even list of at least two points")
    pts = [(int(float(raw[i])), int(float(raw[i + 1]))) for i in range(0, len(raw), 2)]
    for px, py in pts:
        assert_on_screen("<polyline>", px, py, px, py)
    stroke = _colour(el, "stroke", None)
    if stroke is None:
        raise UnsupportedDesign("<polyline> needs a stroke colour")
    _note_quantisation(stroke, "<polyline>", out)
    out.ops.append(Op("draw_polyline", (stroke.rgb565, tuple(pts))))


def _bind_name(el: ET.Element) -> str | None:
    name = el.get("data-bind")
    if name is None:
        return None
    name = name.strip()
    if not name:
        raise UnsupportedDesign(f"<{_tag(el)}> has an empty data-bind")
    return name


def _add_widget(out: Compilation, name: str, kind: str, spec: dict) -> None:
    if any(w.name == name for w in out.widgets):
        raise UnsupportedDesign(
            f"data-bind={name!r} is used more than once; a bound name must "
            f"identify exactly one region or updates would be ambiguous"
        )
    out.widgets.append(Widget(name=name, kind=kind, spec=spec))


def _compile_text(el: ET.Element, out: Compilation) -> None:
    x, y = int(_num(el, "x")), int(_num(el, "y"))
    # Use the content VERBATIM. Leading and trailing spaces are not noise:
    # for a bound field the placeholder's width IS the field width, so
    # "   0.000" reserves eight characters and stripping it to "0.000" would
    # silently truncate a DRO reading of -123.456 to five.
    body = el.text or ""
    if "\n" in body:
        raise UnsupportedDesign(
            "<text> spans multiple lines; keep the content on one line - "
            "surrounding whitespace is significant because it sets the "
            "field width of a bound widget"
        )
    if not body.strip():
        # A blank BOUND field is legitimate: it reserves space for a value
        # that arrives later, like an alarm's third advice line. A blank
        # unbound one is invisible chrome and almost certainly a mistake.
        if _bind_name(el) is None:
            raise UnsupportedDesign(
                "<text> is empty; add data-bind if the intent is to reserve "
                "space for a value supplied at runtime"
            )
        if not body:
            raise UnsupportedDesign(
                "bound <text> has no content at all; use spaces to declare "
                "how wide the field is"
            )

    size = _num(el, "font-size", 16)
    font = font_for_height(size)
    w, h = text_extent(font, body)
    assert_on_screen(f"<text {body!r}>", x, y, x + w - 1, y + h - 1)

    fill = _colour(el, "fill", "#ffffff")
    assert fill is not None
    _note_quantisation(fill, "<text>", out)
    bg = _colour(el, "data-bg", None)
    show_bg = bg is not None

    from .device import FONTS
    if abs(FONTS[font][1] - size) > 2:
        out.warnings.append(
            f"<text {body!r}>: font-size {size:g}px snapped to the "
            f"{FONTS[font][1]}px device font"
        )

    bg_rgb = (bg or Color(0, 0, 0)).rgb565
    out.ops.append(
        Op("draw_text", (0, show_bg, font, fill.rgb565, bg_rgb, x, y, body))
    )

    name = _bind_name(el)
    if name is not None:
        # The placeholder's length IS the field width. An update shorter than
        # the placeholder is padded, so stale pixels from a longer previous
        # value are overwritten rather than left on the glass.
        _add_widget(
            out,
            name,
            "text",
            {
                "x": x,
                "y": y,
                "font": font,
                "fg": fill.rgb565,
                "bg": bg_rgb,
                "chars": len(body),
                "align": el.get("data-align", "right"),
            },
        )


COMPILERS = {
    "rect": _compile_rect,
    "line": _compile_line,
    "circle": _compile_circle,
    "polyline": _compile_polyline,
    "text": _compile_text,
}


def _walk(el: ET.Element, out: Compilation) -> None:
    for child in el:
        tag = _tag(child)
        if tag not in SUPPORTED_TAGS:
            raise UnsupportedDesign(
                f"<{tag}> is not in the supported subset "
                f"({', '.join(sorted(COMPILERS))}). It would not reach the panel."
            )
        _check_attrs(child)
        if tag == "g":
            _walk(child, out)
        elif tag in COMPILERS:
            COMPILERS[tag](child, out)


def compile_svg(source: str) -> Compilation:
    """Compile SVG text into panel draw calls."""
    try:
        root = ET.fromstring(source)
    except ET.ParseError as exc:
        raise UnsupportedDesign(f"not parseable as XML: {exc}") from None

    if _tag(root) != "svg":
        raise UnsupportedDesign(f"root element is <{_tag(root)}>, expected <svg>")

    for attr, expected in (("width", WIDTH), ("height", HEIGHT)):
        raw = root.get(attr)
        if raw is not None and int(float(str(raw).removesuffix("px"))) != expected:
            raise UnsupportedDesign(
                f"<svg {attr}={raw}> must match the panel's {expected}px"
            )

    out = Compilation()
    bg = root.get("data-background")
    if bg:
        colour = Color.from_hex(bg)
        _note_quantisation(colour, "background", out)
        out.ops.append(Op("clear", (colour.rgb565,)))

    _walk(root, out)
    if not out.ops:
        raise UnsupportedDesign("design produced no draw calls")
    return out


def render_preview(compilation: Compilation) -> str:
    """Re-render the compiled ops back to SVG.

    This is the fidelity check: it shows what the panel will draw, in
    quantised colours, rather than what the designer drew. Diff it against the
    source to see exactly what the 16-bit panel costs you.
    """
    from .device import FONTS

    def hexof(v: int) -> str:
        r5, g6, b5 = (v >> 11) & 0x1F, (v >> 5) & 0x3F, v & 0x1F
        return f"#{(r5 * 255) // 31:02x}{(g6 * 255) // 63:02x}{(b5 * 255) // 31:02x}"

    body: list[str] = []
    for op in compilation.ops:
        a = op.args
        if op.method == "clear":
            body.append(
                f'<rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" fill="{hexof(a[0])}"/>'
            )
        elif op.method == "draw_rectangle":
            mode, colour, x0, y0, x1, y1 = a
            paint = (
                f'fill="{hexof(colour)}"'
                if mode == 1
                else f'fill="none" stroke="{hexof(colour)}"'
            )
            body.append(
                f'<rect x="{x0}" y="{y0}" width="{x1 - x0 + 1}" height="{y1 - y0 + 1}" {paint}/>'
            )
        elif op.method == "draw_line":
            colour, x0, y0, x1, y1 = a
            body.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" stroke="{hexof(colour)}"/>')
        elif op.method in ("draw_circle", "fill_circle"):
            colour, cx, cy, r = a
            paint = (
                f'fill="{hexof(colour)}"'
                if op.method == "fill_circle"
                else f'fill="none" stroke="{hexof(colour)}"'
            )
            body.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" {paint}/>')
        elif op.method == "draw_polyline":
            colour, pts = a
            points = " ".join(f"{x},{y}" for x, y in pts)
            body.append(f'<polyline points="{points}" fill="none" stroke="{hexof(colour)}"/>')
        elif op.method == "draw_text":
            _, _show_bg, font, colour, _bgc, x, y, text = a
            cw, ch = FONTS[font]
            body.append(
                f'<text x="{x}" y="{y + ch - 3}" fill="{hexof(colour)}" '
                f'font-family="monospace" font-size="{ch}" '
                f'textLength="{cw * len(text)}" lengthAdjust="spacingAndGlyphs">'
                f"{text}</text>"
            )
    inner = "\n  ".join(body)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}">\n  {inner}\n</svg>\n'
    )
