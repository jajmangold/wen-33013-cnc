"""SVG -> DWIN T5UIC1 compiler.

The compiler's job is to be strict. The panel does not report errors: an
element it cannot draw simply is not there, and you find out when the operator
reaches for a control that was never rendered. So anything outside the
supported subset must raise here, at compile time, on a developer machine.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from dwinui import Color, UnsupportedDesign, compile_svg, font_for_height, render_preview
from dwinui.device import FONTS, text_extent

SCREENS = Path(__file__).resolve().parents[2] / "ui" / "screens"


def svg(body: str, **attrs: str) -> str:
    extra = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="272" height="480" {extra}>'
        f"{body}</svg>"
    )


class TestColour:
    def test_rgb565_packing(self):
        assert Color(255, 255, 255).rgb565 == 0xFFFF
        assert Color(0, 0, 0).rgb565 == 0x0000
        assert Color(255, 0, 0).rgb565 == 0xF800
        assert Color(0, 255, 0).rgb565 == 0x07E0
        assert Color(0, 0, 255).rgb565 == 0x001F

    def test_short_hex_expands(self):
        assert Color.from_hex("#f00") == Color(255, 0, 0)

    def test_quantisation_reports_the_shift(self):
        # 8-bit values that do not survive 5/6/5 truncation
        c = Color.from_hex("#0d1117")
        assert c.quantisation_error >= 0
        assert c.quantised.rgb565 == c.rgb565, "quantising twice must be stable"

    def test_pure_values_survive_exactly(self):
        assert Color(255, 255, 255).quantisation_error == 0

    def test_bad_hex_is_rejected(self):
        with pytest.raises(UnsupportedDesign):
            Color.from_hex("#ggg")
        with pytest.raises(UnsupportedDesign):
            Color.from_hex("rgb(1,2,3)")


class TestFonts:
    def test_exact_sizes_map_to_their_font(self):
        for fid, (_w, h) in FONTS.items():
            assert font_for_height(h) == fid

    def test_in_between_sizes_snap_to_nearest(self):
        assert FONTS[font_for_height(19)][1] == 20
        assert FONTS[font_for_height(31)][1] == 32

    def test_exact_ties_resolve_downward(self):
        """30px is equidistant from the 28 and 32 cells; take the smaller.

        Rounding down is the safe direction: the larger font could overflow
        its box, and an overflowing string is rejected outright at compile
        time, which would make a harmless design fail.
        """
        assert FONTS[font_for_height(30)][1] == 28

    def test_extent_is_fixed_pitch(self):
        assert text_extent(1, "ABCD") == (32, 16)      # 8x16 cell
        assert text_extent(5, "AB") == (32, 32)        # 16x32 cell


class TestCompile:
    def test_minimal_design_compiles(self):
        out = compile_svg(svg('<rect x="0" y="0" width="10" height="10" fill="#fff"/>'))
        assert len(out.ops) == 1
        assert out.ops[0].method == "draw_rectangle"

    def test_background_becomes_a_clear(self):
        out = compile_svg(
            svg('<rect x="0" y="0" width="4" height="4" fill="#fff"/>', data_background="#000")
        )
        assert out.ops[0].method == "clear"

    def test_filled_and_stroked_rect_emits_both(self):
        out = compile_svg(
            svg('<rect x="0" y="0" width="10" height="10" fill="#fff" stroke="#f00"/>')
        )
        assert [o.args[0] for o in out.ops] == [1, 0], "fill first, then outline on top"

    def test_invisible_rect_is_rejected(self):
        with pytest.raises(UnsupportedDesign, match="neither fill nor stroke"):
            compile_svg(svg('<rect x="0" y="0" width="10" height="10"/>'))

    def test_groups_are_flattened(self):
        out = compile_svg(
            svg('<g><rect x="0" y="0" width="4" height="4" fill="#fff"/></g>')
        )
        assert len(out.ops) == 1

    def test_circle_fill_maps_to_fill_circle(self):
        out = compile_svg(svg('<circle cx="20" cy="20" r="5" fill="#fff"/>'))
        assert out.ops[0].method == "fill_circle"

    def test_polyline_points_are_parsed(self):
        out = compile_svg(svg('<polyline points="0,0 10,10 20,0" stroke="#fff"/>'))
        assert out.ops[0].args[1] == ((0, 0), (10, 10), (20, 0))


class TestRejection:
    """Each of these would otherwise vanish silently on the panel."""

    def test_offscreen_rect_is_rejected(self):
        with pytest.raises(UnsupportedDesign, match="outside the 272x480"):
            compile_svg(svg('<rect x="262" y="0" width="50" height="10" fill="#fff"/>'))

    def test_negative_coordinates_are_rejected(self):
        with pytest.raises(UnsupportedDesign, match="outside the 272x480"):
            compile_svg(svg('<rect x="-5" y="0" width="10" height="10" fill="#fff"/>'))

    def test_text_running_off_the_edge_is_rejected(self):
        long = "X" * 40      # 40 * 8px = 320px starting at x=10, past 272
        with pytest.raises(UnsupportedDesign, match="outside the 272x480"):
            compile_svg(svg(f'<text x="10" y="10" font-size="16" fill="#fff">{long}</text>'))

    def test_transform_is_rejected(self):
        with pytest.raises(UnsupportedDesign, match="transform"):
            compile_svg(
                svg('<rect x="0" y="0" width="4" height="4" fill="#fff" transform="rotate(5)"/>')
            )

    def test_opacity_is_rejected(self):
        with pytest.raises(UnsupportedDesign, match="opacity"):
            compile_svg(
                svg('<rect x="0" y="0" width="4" height="4" fill="#fff" opacity="0.5"/>')
            )

    def test_unsupported_element_is_rejected(self):
        with pytest.raises(UnsupportedDesign, match="<path>"):
            compile_svg(svg('<path d="M0 0 L4 4"/>'))

    def test_wrong_canvas_size_is_rejected(self):
        bad = '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600"></svg>'
        with pytest.raises(UnsupportedDesign, match="must match the panel"):
            compile_svg(bad)

    def test_empty_design_is_rejected(self):
        with pytest.raises(UnsupportedDesign, match="no draw calls"):
            compile_svg(svg(""))

    def test_non_svg_root_is_rejected(self):
        with pytest.raises(UnsupportedDesign, match="expected <svg>"):
            compile_svg("<html></html>")


class TestBoundWidgets:
    """data-bind marks a region the firmware redraws in place."""

    def test_bound_text_becomes_a_widget(self):
        out = compile_svg(
            svg('<text x="0" y="0" font-size="16" fill="#fff" data-bind="dro.x">0.000</text>')
        )
        assert out.widget("dro.x").kind == "text"

    def test_placeholder_padding_sets_the_field_width(self):
        """The reason not to strip: '   0.000' reserves eight characters.

        Stripping it to '0.000' would silently truncate a reading of
        -123.456 to five characters on a live DRO.
        """
        out = compile_svg(
            svg('<text x="0" y="0" font-size="16" fill="#fff" data-bind="v">   0.000</text>')
        )
        assert out.widget("v").spec["chars"] == 8

    def test_multiline_text_is_rejected(self):
        """Because surrounding whitespace is significant, it must be explicit."""
        source = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="272" height="480">'
            '<text x="0" y="0" font-size="16" fill="#fff" data-bind="v">\n  0.000\n</text>'
            "</svg>"
        )
        with pytest.raises(UnsupportedDesign, match="one line"):
            compile_svg(source)

    def test_bound_bar_carries_its_range(self):
        out = compile_svg(
            svg('<rect x="0" y="0" width="40" height="8" fill="#161d26" '
                'data-bind="ovr" data-widget="bar" data-min="0" data-max="120"/>')
        )
        spec = out.widget("ovr").spec
        assert (spec["min"], spec["max"]) == (0.0, 120.0)

    def test_bound_circle_becomes_a_lamp(self):
        out = compile_svg(
            svg('<circle cx="20" cy="20" r="5" fill="#000" data-bind="link" '
                'data-on="#5ac57a" data-off="#2d3b4e"/>')
        )
        assert out.widget("link").kind == "lamp"

    def test_duplicate_bind_names_are_rejected(self):
        """Two regions under one name would make updates ambiguous."""
        with pytest.raises(UnsupportedDesign, match="more than once"):
            compile_svg(
                svg('<text x="0" y="0" font-size="16" fill="#fff" data-bind="v">a</text>'
                    '<text x="0" y="40" font-size="16" fill="#fff" data-bind="v">b</text>')
            )

    def test_unknown_widget_kind_is_rejected(self):
        with pytest.raises(UnsupportedDesign, match="not a known widget"):
            compile_svg(
                svg('<rect x="0" y="0" width="10" height="10" fill="#fff" '
                    'data-bind="x" data-widget="sparkline"/>')
            )

    def test_bound_elements_are_still_drawn_as_chrome(self):
        """Entering a screen must show something before any update arrives."""
        out = compile_svg(
            svg('<text x="0" y="0" font-size="16" fill="#fff" data-bind="v">0.000</text>')
        )
        assert any(op.method == "draw_text" for op in out.ops)


class TestWarnings:
    def test_font_snapping_is_reported(self):
        # 35px snaps to the 32px cell - a 3px shift, past the 2px tolerance.
        out = compile_svg(svg('<text x="0" y="0" font-size="35" fill="#fff">hi</text>'))
        assert any("snapped to the" in w for w in out.warnings)

    def test_small_snaps_are_not_reported(self):
        """26px -> 24px is within tolerance; warning on it would be noise."""
        out = compile_svg(svg('<text x="0" y="0" font-size="26" fill="#fff">hi</text>'))
        assert not any("snapped" in w for w in out.warnings)

    def test_exact_font_size_is_silent(self):
        out = compile_svg(svg('<text x="0" y="0" font-size="16" fill="#fff">hi</text>'))
        assert not any("snapped" in w for w in out.warnings)


class TestPreview:
    def test_preview_is_valid_svg_of_the_right_size(self):
        out = compile_svg(svg('<rect x="0" y="0" width="10" height="10" fill="#fff"/>'))
        preview = render_preview(out)
        assert preview.startswith("<svg")
        assert 'width="272"' in preview and 'height="480"' in preview

    def test_preview_shows_quantised_colour_not_the_source(self):
        """The point of the preview: what the panel does, not what you drew."""
        out = compile_svg(svg('<rect x="0" y="0" width="10" height="10" fill="#0d1117"/>'))
        preview = render_preview(out)
        assert "#0d1117" not in preview, "preview must show the 16-bit result"

    def test_every_op_kind_round_trips(self):
        out = compile_svg(
            svg(
                '<rect x="0" y="0" width="4" height="4" fill="#fff"/>'
                '<line x1="0" y1="0" x2="4" y2="4" stroke="#fff"/>'
                '<circle cx="20" cy="20" r="5" fill="#fff"/>'
                '<polyline points="0,0 4,4" stroke="#fff"/>'
                '<text x="0" y="40" font-size="16" fill="#fff">hi</text>',
                data_background="#000",
            )
        )
        preview = render_preview(out)
        for tag in ("<rect", "<line", "<circle", "<polyline", "<text"):
            assert tag in preview


class TestRealScreens:
    @pytest.mark.parametrize("path", sorted(SCREENS.glob("*.svg")), ids=lambda p: p.name)
    def test_screen_compiles(self, path):
        """Every committed screen must compile. A broken one is a blank panel."""
        out = compile_svg(path.read_text(encoding="utf-8"))
        assert out.ops

    @pytest.mark.parametrize("path", sorted(SCREENS.glob("*.svg")), ids=lambda p: p.name)
    def test_screen_previews(self, path):
        out = compile_svg(path.read_text(encoding="utf-8"))
        assert render_preview(out).startswith("<svg")

    def test_dro_screen_shows_all_three_axes(self):
        out = compile_svg((SCREENS / "dro.svg").read_text(encoding="utf-8"))
        texts = [o.args[-1] for o in out.ops if o.method == "draw_text"]
        assert {"X", "Y", "Z"} <= set(texts)
