"""Update behaviour of exported screens.

The T5UIC1 has **no back buffer**. Its `update()` opcode (0x3D) is documented
as a legacy no-op - drawing commands go straight to the glass. So every
redraw is visible, and redrawing something that did not change is not merely
wasted bandwidth, it is visible flicker.

These tests pin the two behaviours that follow from that:

  - an unchanged value must draw nothing at all
  - a bar must repaint only the band that moved, not its whole length
"""

from __future__ import annotations

import pytest
from dwinui.__main__ import main as dwinui_main


class FakePanel:
    """Records draw calls instead of making them."""

    def __init__(self):
        self.calls: list[tuple] = []

    def __getattr__(self, name):
        def record(*args):
            self.calls.append((name, args))
        return record


@pytest.fixture
def screen(tmp_path):
    """Export a screen with one text field and one horizontal bar."""
    src = tmp_path / "s.svg"
    src.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="272" height="480" '
        'data-background="#000">'
        '<text x="0" y="0" font-size="16" fill="#fff" data-bind="v">   0.000</text>'
        '<rect x="0" y="40" width="200" height="10" fill="#161d26" '
        'data-bind="bar" data-widget="bar" data-min="0" data-max="100"/>'
        "</svg>",
        encoding="utf-8",
    )
    out = tmp_path / "s_screen.py"
    assert dwinui_main(["export", str(src), "-o", str(out)]) == 0
    namespace: dict = {}
    exec(compile(out.read_text(encoding="utf-8"), str(out), "exec"), namespace)  # noqa: S102
    return namespace


class TestUnchangedValues:
    def test_repeating_a_value_draws_nothing(self, screen):
        panel = FakePanel()
        screen["draw"](panel)
        screen["update"](panel, "v", "  1.000")
        before = len(panel.calls)
        assert screen["update"](panel, "v", "  1.000") is False
        assert len(panel.calls) == before, "an unchanged value repainted; that is flicker"

    def test_a_changed_value_does_draw(self, screen):
        panel = FakePanel()
        screen["draw"](panel)
        screen["update"](panel, "v", "  1.000")
        before = len(panel.calls)
        assert screen["update"](panel, "v", "  2.000") is True
        assert len(panel.calls) > before

    def test_force_repaints_anyway(self, screen):
        """Needed after anything else has drawn over the widget."""
        panel = FakePanel()
        screen["draw"](panel)
        screen["update"](panel, "v", "  1.000")
        before = len(panel.calls)
        assert screen["update"](panel, "v", "  1.000", True) is True
        assert len(panel.calls) > before

    def test_draw_resets_the_cache(self, screen):
        """Re-entering a screen redraws chrome, so cached values are stale."""
        panel = FakePanel()
        screen["draw"](panel)
        screen["update"](panel, "v", "  1.000")
        screen["draw"](panel)
        before = len(panel.calls)
        assert screen["update"](panel, "v", "  1.000") is True, (
            "after re-drawing chrome the widget must repaint, or it shows "
            "the chrome placeholder while believing it shows a value"
        )
        assert len(panel.calls) > before


class TestBarIsIncremental:
    def test_first_paint_draws_both_halves(self, screen):
        panel = FakePanel()
        screen["draw"](panel)
        panel.calls.clear()
        screen["update"](panel, "bar", 50)
        assert len(panel.calls) == 2, "first paint should lay down fill and track"

    def test_a_step_repaints_only_the_changed_band(self, screen):
        panel = FakePanel()
        screen["draw"](panel)
        screen["update"](panel, "bar", 50)
        panel.calls.clear()
        screen["update"](panel, "bar", 55)
        assert len(panel.calls) == 1, "a moving bar must not repaint its whole length"

    def test_growing_and_shrinking_use_different_colours(self, screen):
        panel = FakePanel()
        screen["draw"](panel)
        screen["update"](panel, "bar", 50)
        panel.calls.clear()
        screen["update"](panel, "bar", 60)
        grow_colour = panel.calls[0][1][1]
        panel.calls.clear()
        screen["update"](panel, "bar", 40)
        shrink_colour = panel.calls[0][1][1]
        assert grow_colour != shrink_colour, (
            "growing paints fill, shrinking paints track; same colour means "
            "the bar can only ever grow"
        )

    def test_sub_pixel_changes_draw_nothing(self, screen):
        """A 200px bar over 0-100 has ~0.5 units per pixel.

        Without this, a noisy feed-override reading would strobe the bar at
        frame rate while never visibly moving.
        """
        panel = FakePanel()
        screen["draw"](panel)
        screen["update"](panel, "bar", 50.0)
        panel.calls.clear()
        assert screen["update"](panel, "bar", 50.1) is False
        assert panel.calls == []
