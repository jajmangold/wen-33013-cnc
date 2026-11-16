"""Facts about the DWIN T5UIC1 panel (the Ender 3 V2 screen).

These are device limits, not design preferences. The compiler refuses to emit
anything that violates them, because the panel does not report errors - it
simply draws nothing, or draws it in the wrong place, and you are left
guessing from across the shop.
"""

from __future__ import annotations

from dataclasses import dataclass

# Confirmed on the bench, not inferred: the stock CFG boots rotated and
# orientation 1 is the one that reads upright on this glass. The firmware
# applies it before drawing - see firmware/pendant/main.py.
WIDTH = 272
HEIGHT = 480

# T5UIC1 built-in font table: id -> (cell width, cell height) in pixels.
FONTS: dict[int, tuple[int, int]] = {
    0: (6, 12),
    1: (8, 16),
    2: (10, 20),
    3: (12, 24),
    4: (14, 28),
    5: (16, 32),
    6: (20, 40),
    7: (24, 48),
    8: (28, 56),
    9: (32, 64),
}


class UnsupportedDesign(ValueError):
    """The design asks for something the panel cannot do."""


@dataclass(frozen=True)
class Color:
    """An RGB565 colour.

    The panel is 16-bit. A design authored in 24-bit sRGB loses the low bits,
    so we quantise explicitly and can report how far a colour moved.
    """

    r: int
    g: int
    b: int

    @classmethod
    def from_hex(cls, text: str) -> Color:
        t = text.strip().lstrip("#")
        if len(t) == 3:
            t = "".join(c * 2 for c in t)
        if len(t) != 6:
            raise UnsupportedDesign(f"colour {text!r} is not #rgb or #rrggbb")
        try:
            return cls(int(t[0:2], 16), int(t[2:4], 16), int(t[4:6], 16))
        except ValueError:
            raise UnsupportedDesign(f"colour {text!r} is not valid hex") from None

    @property
    def rgb565(self) -> int:
        return ((self.r >> 3) << 11) | ((self.g >> 2) << 5) | (self.b >> 3)

    @property
    def quantised(self) -> Color:
        """What the panel will actually show."""
        v = self.rgb565
        r5, g6, b5 = (v >> 11) & 0x1F, (v >> 5) & 0x3F, v & 0x1F
        return Color((r5 * 255) // 31, (g6 * 255) // 63, (b5 * 255) // 31)

    @property
    def quantisation_error(self) -> int:
        """Largest per-channel shift caused by 16-bit quantisation."""
        q = self.quantised
        return max(abs(self.r - q.r), abs(self.g - q.g), abs(self.b - q.b))

    def to_hex(self) -> str:
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"


def font_for_height(px: float) -> int:
    """Pick the device font whose cell height is closest to `px`.

    The panel has ten fixed fonts and no scaling, so a design asking for 19 px
    text gets the 20 px font. Returning the nearest rather than erroring keeps
    designs portable, and `text_extent` then catches anything that overflows.
    """
    return min(FONTS, key=lambda f: (abs(FONTS[f][1] - px), f))


def text_extent(font: int, text: str) -> tuple[int, int]:
    """Pixel size of `text` in `font`. Fonts are fixed-pitch."""
    if font not in FONTS:
        raise UnsupportedDesign(f"font {font} is not one of {sorted(FONTS)}")
    cw, ch = FONTS[font]
    return cw * len(text), ch


def assert_on_screen(where: str, x0: int, y0: int, x1: int, y1: int) -> None:
    if not (0 <= x0 <= x1 < WIDTH and 0 <= y0 <= y1 < HEIGHT):
        raise UnsupportedDesign(
            f"{where}: ({x0},{y0})-({x1},{y1}) falls outside the "
            f"{WIDTH}x{HEIGHT} panel"
        )
