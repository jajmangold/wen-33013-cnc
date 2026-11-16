"""Render the JOG screen with plausible live data.

Demonstration only - there is no LinuxCNC behind it yet. It exists to show
the screen working on real glass, including the one thing the compiler cannot
draw for us: the envelope map, which is a `region` widget whose contents the
firmware owns.

Run with:
    python -m mpremote connect port:COM20 run firmware/pendant/demo_jog.py
"""

import math
import time

from dwin_t5uic1 import T5UIC1Display, rgb565
from dwin_t5uic1.transport import open_uart

import jog_screen as s

# Machine envelope, from machine/wen33013.toml.
TRAVEL_X = 300.0
TRAVEL_Y = 130.0
TRAVEL_Z = 177.8

BG = rgb565(13, 17, 23)
GRID = rgb565(34, 44, 56)
PATH = rgb565(77, 208, 225)
TOOL = rgb565(230, 237, 243)
HALO = rgb565(90, 197, 122)


class EnvelopeMap:
    """XY plan view, drawn INCREMENTALLY.

    The panel has no back buffer, so clearing this region and repainting it
    every frame shows the blank region for as long as the repaint takes -
    which is the flicker. Instead the grid is laid down once and each frame
    only touches a small box around the tool: erase where it was, repair the
    grid and trail inside that box, draw it where it is now.

    Aspect ratio is preserved deliberately. A stretched plan view of a
    300x130 table would misrepresent how much Y headroom is left, which is
    the whole reason the map is here.
    """

    DOT_R = 4
    ERASE_R = 5          # DOT_R + 1, so antialiasing-free edges are covered

    def __init__(self, panel):
        _kind, w = s.WIDGETS['map.xy']
        self.panel = panel
        self.x0, self.y0 = w['x0'], w['y0']
        self.x1, self.y1 = w['x1'], w['y1']
        self.bg = w['bg']
        self.scale = min((self.x1 - self.x0) / TRAVEL_X,
                         (self.y1 - self.y0) / TRAVEL_Y)
        self.grid_x = [self.to_px(TRAVEL_X * f, 0)[0] for f in (0.25, 0.5, 0.75)]
        self.grid_y = [self.to_px(0, TRAVEL_Y * f)[1] for f in (0.25, 0.5, 0.75)]
        self.last = None

    def to_px(self, mx, my):
        # Machine +Y is up, screen +Y is down. Getting this wrong makes the
        # dot travel opposite to the table, which is worse than no map.
        return (self.x0 + int(mx * self.scale),
                self.y1 - int(my * self.scale))

    def draw_static(self):
        """Grid and background: once, on screen entry."""
        self.panel.draw_rectangle(1, self.bg, self.x0, self.y0, self.x1, self.y1)
        for gx in self.grid_x:
            self.panel.draw_line(GRID, gx, self.y0, gx, self.y1)
        for gy in self.grid_y:
            self.panel.draw_line(GRID, self.x0, gy, self.x1, gy)

    def _repair(self, cx, cy):
        """Erase the old dot, then put back what it was covering."""
        bx0 = max(self.x0, cx - self.ERASE_R)
        by0 = max(self.y0, cy - self.ERASE_R)
        bx1 = min(self.x1, cx + self.ERASE_R)
        by1 = min(self.y1, cy + self.ERASE_R)
        self.panel.draw_rectangle(1, self.bg, bx0, by0, bx1, by1)
        for gx in self.grid_x:
            if bx0 <= gx <= bx1:
                self.panel.draw_line(GRID, gx, by0, gx, by1)
        for gy in self.grid_y:
            if by0 <= gy <= by1:
                self.panel.draw_line(GRID, bx0, gy, bx1, gy)

    def move_to(self, x_mm, y_mm):
        px, py = self.to_px(x_mm, y_mm)
        if self.last == (px, py):
            return                      # sub-pixel move: drawing it would strobe
        if self.last is not None:
            ox, oy = self.last
            self._repair(ox, oy)
            # The trail persists: it is a breadcrumb of where the table has
            # been, which is useful, and never clearing it means never
            # flickering it.
            self.panel.draw_line(PATH, ox, oy, px, py)
        self.panel.fill_circle(HALO, px, py, self.DOT_R)
        self.panel.fill_circle(TOOL, px, py, 2)
        self.last = (px, py)


def main():
    panel = T5UIC1Display(open_uart(0, tx=0, rx=1), handshake=True)
    panel.set_orientation(1)
    panel.set_backlight(0xC0)
    s.draw(panel)

    s.update(panel, 'link', True)
    s.update(panel, 'jog.axis', 'X')
    s.update(panel, 'jog.step', '0.010 mm')
    for name in ('lim.xmin', 'lim.xmax', 'lim.ymin',
                 'lim.ymax', 'lim.zmin', 'lim.zmax'):
        s.update(panel, name, False)

    envelope = EnvelopeMap(panel)
    envelope.draw_static()

    held = False
    for frame in range(140):
        t = frame / 12.0
        # A lazy arc around the table, so the map has something to show.
        x = 150.0 + 110.0 * math.sin(t * 0.7)
        y = 65.0 + 45.0 * math.sin(t * 1.1)
        z = 90.0 + 70.0 * math.sin(t * 0.4)

        # Deadman blinks to make the point that nothing moves without it.
        held = (frame // 10) % 2 == 0
        s.update(panel, 'deadman', '  HOLD LB' if not held else '   JOGGING')

        s.update(panel, 'jog.value', '%8.3f' % x)
        s.update(panel, 'jog.rate', '%3d mm/s' % int(abs(math.cos(t * 0.7)) * 42))
        s.update(panel, 'map.z', z)
        s.update(panel, 'jog.headroom', '%6.1f mm' % min(x - 2.0, 298.0 - x))

        envelope.move_to(x, y)
        time.sleep_ms(45)

    s.update(panel, 'deadman', '  HOLD LB')
    print('jog demo done')


main()
