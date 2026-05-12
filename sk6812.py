# ============================================================
#  sk6812.py  —  Minimal SK6812 RGBW driver using PIO
# ============================================================
# The SK6812 needs a very precise 800 kHz NZR signal.
# We use the Pico's PIO state machine which runs independent
# of the CPU, giving rock-solid timing.

import array
import rp2
from machine import Pin


# PIO program: sends 24/32 bits per LED, MSB-first.
# Timing (at 10 MHz PIO clock, each loop tick = 100 ns):
#   T0H = 3 ticks  (300 ns), T0L = 9 ticks  (900 ns)  → '0'
#   T1H = 7 ticks  (700 ns), T1L = 5 ticks  (500 ns)  → '1'
@rp2.asm_pio(
    sideset_init=rp2.PIO.OUT_LOW,
    out_shiftdir=rp2.PIO.SHIFT_LEFT,
    autopull=True,
    pull_thresh=32,
)
def _sk6812_pio():
    wrap_target()
    label("bit_loop")
    out(x, 1)               .side(0)  [2]   # pull 1 bit; pin LOW  (T0L gap before)
    jmp(not_x, "zero")      .side(1)  [4]   # pin HIGH; if bit==0 → zero
    jmp("bit_loop")         .side(1)  [3]   # bit==1: stay HIGH longer
    label("zero")
    nop()                   .side(0)  [3]   # bit==0: go LOW early
    wrap()


class SK6812:
    """
    Driver for a strip of SK6812 RGBW LEDs.

    Usage:
        strip = SK6812(pin=0, num_leds=8)
        strip.set(0, r=255, g=100, b=0, w=200)
        strip.fill(r=0, g=0, b=0, w=255)
        strip.show()
    """

    def __init__(self, pin: int, num_leds: int, brightness: float = 1.0):
        self.num_leds  = num_leds
        self.brightness = max(0.0, min(1.0, brightness))
        # Pixel buffer: store full 0-255 values; apply brightness at show() time
        # Each pixel: [R, G, B, W]
        self._pixels = [(0, 0, 0, 0)] * num_leds

        self._sm = rp2.StateMachine(
            0,
            _sk6812_pio,
            freq=10_000_000,          # 10 MHz → 100 ns per tick
            sideset_base=Pin(pin),
        )
        self._sm.active(1)

    # ── Public API ──────────────────────────────────────────

    def set(self, index: int, r=0, g=0, b=0, w=0):
        """Set one LED by index.  Values 0-255."""
        if 0 <= index < self.num_leds:
            self._pixels[index] = (r, g, b, w)

    def set_all(self, r=0, g=0, b=0, w=0):
        """Set every LED to the same RGBW value."""
        self._pixels = [(r, g, b, w)] * self.num_leds

    def fill_from_list(self, pixel_list):
        """Set all LEDs from a list of (r,g,b,w) tuples."""
        for i, px in enumerate(pixel_list[:self.num_leds]):
            self._pixels[i] = px

    def set_brightness(self, brightness: float):
        self.brightness = max(0.0, min(1.0, brightness))

    def show(self):
        """Push the pixel buffer to the strip."""
        # SK6812 byte order: G R B W
        buf = array.array("I", [0] * self.num_leds)
        b = self.brightness
        for i, (r, g, bv, w) in enumerate(self._pixels):
            ri = int(r * b)
            gi = int(g * b)
            bi = int(bv * b)
            wi = int(w * b)
            # Pack as 32-bit: G(8) R(8) B(8) W(8)  — sent MSB first
            buf[i] = (gi << 24) | (ri << 16) | (bi << 8) | wi
        # Write 32 bits per LED; PIO autopulls on 32-bit threshold
        self._sm.put(buf, 0)

    def off(self):
        """Turn all LEDs off immediately."""
        self.set_all(0, 0, 0, 0)
        self.show()
