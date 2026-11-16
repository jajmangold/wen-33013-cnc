"""Second sweep: BELOW 400 Hz.

The first sweep found 400 Hz loudest with everything above it quieter -
which means the peak sits at or below the lowest frequency sampled. The
range was wrong, not the method.

That response is also a useful clue about what is actually on panel pin 5. A
resonant piezo peaks at 2-4 kHz and is weak low down; something that gets
LOUDER as it goes down is behaving more like a magnetic transducer, or is
being driven through something with a low-pass character.

Run with:
    python -m mpremote connect port:COM20 run firmware/pendant/demo_sweep_low.py
"""

import time

import jog_screen as s
from dwin_t5uic1 import T5UIC1Display
from dwin_t5uic1.transport import open_uart

from machine import PWM, Pin

PIN_BEEP = 5

SWEEP = (80, 100, 130, 160, 200, 250, 300, 350, 400, 450, 500, 600, 800)

TONE_MS = 450
GAP_MS = 550


def main():
    panel = T5UIC1Display(open_uart(0, tx=0, rx=1), handshake=True)
    panel.set_orientation(1)
    panel.set_backlight(0xC0)
    s.draw(panel)
    s.update(panel, 'link', True)
    s.update(panel, 'jog.axis', 'Hz')
    s.update(panel, 'jog.step', 'LOW SWP ')

    pwm = PWM(Pin(PIN_BEEP))
    pwm.duty_u16(0)

    print('80 Hz up to 800 Hz - which is loudest?')
    s.update(panel, 'deadman', '   READY?')
    time.sleep_ms(2500)

    for freq in SWEEP:
        s.update(panel, 'jog.value', '%6d' % freq)
        s.update(panel, 'deadman', '   LISTEN')
        print('%4d Hz' % freq)
        pwm.freq(freq)
        pwm.duty_u16(32768)          # 50%: maximum square-wave output
        time.sleep_ms(TONE_MS)
        pwm.duty_u16(0)
        time.sleep_ms(GAP_MS)

    # Duty at the frequency that won the first sweep. A square wave is
    # loudest at 50%; 10% should be clearly weaker, which confirms the drive
    # is working as expected rather than saturating somewhere.
    print('')
    print('duty at 400 Hz: 10%, 25%, 50%')
    for duty, label in ((6553, '10%'), (16000, '25%'), (32768, '50%')):
        s.update(panel, 'jog.value', '  %s' % label)
        s.update(panel, 'jog.step', 'DUTY    ')
        print('  %s' % label)
        pwm.freq(400)
        pwm.duty_u16(duty)
        time.sleep_ms(450)
        pwm.duty_u16(0)
        time.sleep_ms(650)

    # Duration at 400 Hz. One cycle is 2.5 ms, so 20 ms is only 8 cycles -
    # the floor for audibility is much longer down here than it would be at
    # 2.7 kHz, and the chime set has to respect that.
    print('duration at 400 Hz: 20, 40, 80, 150 ms')
    for ms in (20, 40, 80, 150):
        s.update(panel, 'jog.value', '%5dms' % ms)
        s.update(panel, 'jog.step', '%3d cyc ' % int(ms * 400 / 1000))
        print('  %3d ms  (%d cycles)' % (ms, int(ms * 400 / 1000)))
        pwm.freq(400)
        pwm.duty_u16(32768)
        time.sleep_ms(ms)
        pwm.duty_u16(0)
        time.sleep_ms(700)

    pwm.duty_u16(0)
    s.update(panel, 'jog.value', '    done')
    s.update(panel, 'deadman', '  HOLD LB')
    print('')
    print('loudest frequency? shortest audible tone?')


main()
