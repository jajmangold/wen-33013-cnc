"""Is it making a TONE, or just clicking on each edge?

The low sweep found output rising monotonically as frequency fell, with duty
cycle barely mattering. A resonant buzzer does not behave like that - it has
a peak. What does behave like that is a transducer being snapped by each
edge transition with too little energy to ring: at 80 Hz you hear 160
individual clicks per second and read it as a loud deep tone, and by 3 kHz
the clicks have blurred into a weak hiss.

This test settles it. At 5 Hz the edges are 100 ms apart. If you can count
distinct ticks, there is no tone being generated and the element is
underdriven - which is a hardware problem, not a note-choice problem.

Run with:
    python -m mpremote connect port:COM20 run firmware/pendant/demo_clicks.py
"""

import time

import jog_screen as s
from dwin_t5uic1 import T5UIC1Display
from dwin_t5uic1.transport import open_uart

from machine import PWM, Pin

PIN_BEEP = 5


def main():
    panel = T5UIC1Display(open_uart(0, tx=0, rx=1), handshake=True)
    panel.set_orientation(1)
    panel.set_backlight(0xC0)
    s.draw(panel)
    s.update(panel, 'link', True)
    s.update(panel, 'jog.axis', 'CLK')

    pin = Pin(PIN_BEEP, Pin.OUT)
    pin.value(0)

    # 1. Single manual edges, well separated. Nothing resonant can hide here.
    print('TEST 1: ten single edges, 400 ms apart')
    print('  can you hear a distinct tick for each one?')
    s.update(panel, 'jog.step', 'SINGLE  ')
    s.update(panel, 'deadman', '   LISTEN')
    time.sleep_ms(1500)
    for i in range(10):
        s.update(panel, 'jog.value', '%6d' % (i + 1))
        pin.value(1)
        time.sleep_ms(30)
        pin.value(0)
        time.sleep_ms(370)

    time.sleep_ms(1200)

    # 2. Slow square waves, toggled by hand. RP2040 PWM will not go below
    #    ~8 Hz, and doing it manually also removes PWM itself as a variable.
    print('')
    print('TEST 2: 5, 12, 30, 60 Hz - ticks you can count, or a pitch?')
    for freq in (5, 12, 30, 60):
        s.update(panel, 'jog.value', '%5dHz' % freq)
        s.update(panel, 'jog.step', 'SLOW    ')
        print('  %2d Hz' % freq)
        half_ms = int(500 / freq)
        for _ in range(int(2000 / (half_ms * 2))):
            pin.value(1)
            time.sleep_ms(half_ms)
            pin.value(0)
            time.sleep_ms(half_ms)
        time.sleep_ms(800)

    pwm = PWM(Pin(PIN_BEEP))

    # 3. Same note, two very different duties. A real transducer gets
    #    noticeably louder at 50%; an edge-clicker barely changes, because
    #    the number of edges per second is identical.
    print('')
    print('TEST 3: 200 Hz at 3% duty then 50% duty')
    print('  same edge count, very different energy - any difference?')
    for duty, label in ((2000, ' 3%'), (32768, '50%')):
        s.update(panel, 'jog.value', '   %s' % label)
        s.update(panel, 'jog.step', 'DUTY    ')
        print('  %s' % label)
        pwm.freq(200)
        pwm.duty_u16(duty)
        time.sleep_ms(1200)
        pwm.duty_u16(0)
        time.sleep_ms(900)

    pwm.duty_u16(0)
    s.update(panel, 'jog.value', '    done')
    s.update(panel, 'deadman', '  HOLD LB')
    print('')
    print('1: distinct ticks?   2: countable or pitched?   3: 3% vs 50%?')


main()
