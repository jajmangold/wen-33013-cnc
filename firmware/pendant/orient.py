"""Sweep the four panel orientations so a human can pick the right one.

The T5UIC1 takes 0/1/2/3 for 0/90/180/270 degrees. Which one reads correctly
depends on how the glass is mounted in its bezel, which no datasheet tells
you - so show all four, big, and let the operator say.

Run with: python -m mpremote connect port:COM20 run firmware/pendant/orient.py
"""

import time

from dwin_t5uic1 import T5UIC1Display, rgb565
from dwin_t5uic1.transport import open_uart

BG = (rgb565(0, 0, 160), rgb565(0, 128, 0), rgb565(160, 0, 0), rgb565(128, 0, 128))
WHITE = rgb565(255, 255, 255)

panel = T5UIC1Display(open_uart(0, tx=0, rx=1), handshake=False)
panel.set_backlight(0xC0)

for direction in (0, 1, 2, 3):
    panel.set_orientation(direction)
    time.sleep_ms(120)
    panel.clear(BG[direction])

    # A big digit, plus a word that only reads correctly one way up, plus a
    # marker at the top-left of THIS orientation's frame.
    panel.draw_text(False, True, panel.FONT_32X64, WHITE, BG[direction],
                    30, 40, str(direction))
    panel.draw_text(False, True, panel.FONT_16X32, WHITE, BG[direction],
                    30, 120, "TOP LEFT")
    panel.draw_rectangle(1, WHITE, 0, 0, 20, 20)

    print("showing orientation", direction, "- white square marks its top-left")
    time.sleep(4)

print("")
print("Which number was upright AND had the white square top-left?")
panel.set_orientation(0)
panel.clear(rgb565(0, 0, 0))
panel.draw_text(False, True, panel.FONT_8X16, WHITE, rgb565(0, 0, 0),
                10, 10, "sweep done")
