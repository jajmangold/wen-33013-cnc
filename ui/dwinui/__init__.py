"""dwinui - design DWIN T5UIC1 screens as SVG, compile to native draw calls.

    compile_svg(text)   -> Compilation   ops + warnings
    render_preview(c)   -> str           what the panel will actually show

The compiler is strict on purpose. An unsupported element raises rather than
being dropped, because a dropped element is a control that is not on the
screen when the operator reaches for it.
"""

from .compile import Compilation, Op, compile_svg, render_preview
from .device import FONTS, HEIGHT, WIDTH, Color, UnsupportedDesign, font_for_height, text_extent

__all__ = [
    "FONTS",
    "HEIGHT",
    "WIDTH",
    "Color",
    "Compilation",
    "Op",
    "UnsupportedDesign",
    "compile_svg",
    "font_for_height",
    "render_preview",
    "text_extent",
]
