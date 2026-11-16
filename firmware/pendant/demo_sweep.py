"""Find where this buzzer is actually loud.

A passive buzzer is a mechanical resonator, not a speaker: its output varies
enormously with frequency and peaks at its resonance, usually somewhere
between 2 and 4 kHz. Choosing notes for musical reasons without checking this
produces a chime set where half the sounds are inaudible - which is exactly
what happened.

So: sweep, listen, and put the palette where the hardware is efficient.

Run with:
    python -m mpremote connect port:COM20 run firmware/pendant/demo_sweep.py
"""

import time

import jog_screen as s
from dwin_t5uic1 import T5UIC1Display
from dwin_t5uic1.transport import open_uart

from machine import PWM, Pin

PIN_BEEP = 5

# Spread across the plausible range for a small passive buzzer. Each is held
# long enough to judge loudness rather than just hear a click.
SWEEP = (400, 600, 800, 1000, 1200, 1500, 2000, 2400,
         2700, 3000, 3500, 4000, 4500, 5000)

TONE_MS = 400
GAP_MS = 500


def main():
    panel = T5UIC1Display(open_uart(0, tx=0, rx=1), handshake=True)
    panel.set_orientation(1)
    panel.set_backlight(0xC0)
    s.draw(panel)
    s.update(panel, 'link', True)
    s.update(panel, 'jog.axis', 'Hz')
    s.update(panel, 'jog.step', 'LOUDEST?')

    pwm = PWM(Pin(PIN_BEEP))
    pwm.duty_u16(0)

    print('listen for which are LOUDEST - the frequency is on the panel')
    print('')
    s.update(panel, 'deadman', '   READY?')
    time.sleep_ms(2500)

    for freq in SWEEP:
        s.update(panel, 'jog.value', '%6d' % freq)
        s.update(panel, 'deadman', '   LISTEN')
        print('%5d Hz' % freq)
        pwm.freq(freq)
        pwm.duty_u16(32768)          # 50% - maximum square-wave output
        time.sleep_ms(TONE_MS)
        pwm.duty_u16(0)
        time.sleep_ms(GAP_MS)

    # Duty comparison at a mid frequency, to see whether 25% was costing us
    # anything audible.
    print('')
    print('duty test at 2700 Hz: 25%, then 50%')
    s.update(panel, 'jog.step', 'DUTY 25 ')
    for duty in (16000, 32768):
        s.update(panel, 'jog.value', '%6d' % duty)
        s.update(panel, 'jog.step', 'DUTY %2d%%' % (duty * 100 // 65535))
        pwm.freq(2700)
        pwm.duty_u16(duty)
        time.sleep_ms(500)
        pwm.duty_u16(0)
        time.sleep_ms(700)

    # Duration test: is a 6 ms tick audible at all?
    print('duration test at 2700 Hz: 6, 15, 30, 60 ms')
    for ms in (6, 15, 30, 60):
        s.update(panel, 'jog.value', '%5dms' % ms)
        s.update(panel, 'jog.step', 'LENGTH  ')
        print('  %d ms' % ms)
        pwm.freq(2700)
        pwm.duty_u16(32768)
        time.sleep_ms(ms)
        pwm.duty_u16(0)
        time.sleep_ms(700)

    pwm.duty_u16(0)
    s.update(panel, 'jog.value', '    done')
    s.update(panel, 'deadman', '  HOLD LB')
    print('')
    print('which frequencies were loudest?')


main()
