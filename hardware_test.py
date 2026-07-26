# ============================================================
#  hardware_test.py  —  Offline wiring test (no WiFi/MQTT)
#
#  Tests:
#    1. LED strip  — cycles through colours to verify wiring
#    2. Touch sensor — prints raw readings and fires events
#
#  Pins: LEDs on GPIO 5, touch sensor on GPIO 12
#  Self-contained — flash this single file, no other project
#  files needed on the Pico.
# ============================================================

import array
import utime
import machine
import rp2
from machine import Pin


# ── Inline SK6812 PIO driver ─────────────────────────────────

@rp2.asm_pio(
    sideset_init=rp2.PIO.OUT_LOW,
    out_shiftdir=rp2.PIO.SHIFT_LEFT,
    autopull=True,
    pull_thresh=32,
)
def _sk6812_pio():
    wrap_target()
    label("bit_loop")
    out(x, 1)               .side(0)  [2]
    jmp(not_x, "zero")      .side(1)  [4]
    jmp("bit_loop")         .side(1)  [3]
    label("zero")
    nop()                   .side(0)  [3]
    wrap()


class SK6812:
    def __init__(self, pin: int, num_leds: int, brightness: float = 1.0):
        self.num_leds  = num_leds
        self.brightness = max(0.0, min(1.0, brightness))
        self._pixels = [(0, 0, 0, 0)] * num_leds
        self._sm = rp2.StateMachine(
            0, _sk6812_pio, freq=10_000_000, sideset_base=Pin(pin)
        )
        self._sm.active(1)

    def set_all(self, r=0, g=0, b=0, w=0):
        self._pixels = [(r, g, b, w)] * self.num_leds

    def show(self):
        # Same packing as sk6812.py: G R B W, MSB first, no pre-shift
        buf = array.array("I", [0] * self.num_leds)
        br = self.brightness
        for i, (r, g, bv, w) in enumerate(self._pixels):
            buf[i] = (int(g*br) << 24) | (int(r*br) << 16) | (int(bv*br) << 8) | int(w*br)
        self._sm.put(buf, 0)

    def off(self):
        self.set_all(0, 0, 0, 0)
        self.show()

# ── Config ───────────────────────────────────────────────────
LED_PIN     = 5
TOUCH_PIN   = 12
NUM_LEDS    = 8
BRIGHTNESS  = 0.5

TOUCH_SAMPLES   = 10      # samples averaged per reading
TOUCH_THRESHOLD = 50      # counts above baseline = "touched"
HOLD_TIME_MS    = 1000    # ms held → "hold" event

# ── LED test ─────────────────────────────────────────────────

def test_leds(strip):
    print("\n[LED] Testing strip — watch for colour sequence")

    steps = [
        ("RED",        (255,   0,   0,   0)),
        ("GREEN",      (  0, 255,   0,   0)),
        ("BLUE",       (  0,   0, 255,   0)),
        ("WHITE (W)",  (  0,   0,   0, 255)),
        ("WARM WHITE", (255, 160,  60, 220)),
        ("OFF",        (  0,   0,   0,   0)),
    ]

    for label, (r, g, b, w) in steps:
        print(f"  {label}")
        strip.set_all(r, g, b, w)
        strip.show()
        utime.sleep_ms(800)

    print("[LED] Done\n")


# ── Touch sensor helpers ──────────────────────────────────────

def _measure_touch(pin_num: int) -> int:
    """Single charge-time measurement on the given GPIO pin."""
    pin = machine.Pin(pin_num, machine.Pin.OUT)
    pin.value(1)
    utime.sleep_us(10)
    pin.init(machine.Pin.IN)
    count = 0
    while pin.value() == 1:
        count += 1
        if count > 10_000:
            break
    return count


def _measure_avg(pin_num: int, samples: int = TOUCH_SAMPLES) -> float:
    total = 0
    for _ in range(samples):
        total += _measure_touch(pin_num)
        utime.sleep_us(500)
    return total / samples


def calibrate_touch(pin_num: int) -> float:
    print("[TOUCH] Calibrating baseline — do NOT touch the sensor...")
    baseline = _measure_avg(pin_num, samples=20)
    print(f"[TOUCH] Baseline = {baseline:.1f}")
    return baseline


# ── Touch test ────────────────────────────────────────────────

def test_touch(strip, baseline: float):
    print("[TOUCH] Touch test running — tap or hold the sensor (Ctrl-C to exit)\n")

    is_touched  = False
    touch_start = 0
    hold_fired  = False

    while True:
        raw   = _measure_touch(TOUCH_PIN)
        delta = raw - baseline
        touched = delta > TOUCH_THRESHOLD

        now = utime.ticks_ms()

        if touched and not is_touched:
            is_touched  = True
            touch_start = now
            hold_fired  = False
            # Visual: blue while held
            strip.set_all(0, 0, 255, 0)
            strip.show()
            print(f"  [+] touch start  raw={raw}  delta={delta:.0f}")

        elif touched and is_touched:
            if (not hold_fired and
                    utime.ticks_diff(now, touch_start) >= HOLD_TIME_MS):
                hold_fired = True
                # Visual: red for hold
                strip.set_all(255, 0, 0, 0)
                strip.show()
                print(f"  [H] HOLD event   raw={raw}  delta={delta:.0f}")

        elif not touched and is_touched:
            is_touched = False
            if not hold_fired:
                # Visual: green flash for tap
                strip.set_all(0, 255, 0, 0)
                strip.show()
                utime.sleep_ms(150)
                strip.off()
                print(f"  [T] TAP event    raw={raw}  delta={delta:.0f}")
            else:
                strip.off()
            print(f"  [-] touch end")

        utime.sleep_ms(10)


# ── Entry point ───────────────────────────────────────────────

def main():
    print("=" * 50)
    print("  Linked Lights — Hardware Test")
    print(f"  LEDs: GPIO {LED_PIN}   Touch: GPIO {TOUCH_PIN}")
    print("=" * 50)

    strip = SK6812(pin=LED_PIN, num_leds=NUM_LEDS, brightness=BRIGHTNESS)

    test_leds(strip)

    baseline = calibrate_touch(TOUCH_PIN)
    test_touch(strip, baseline)


main()
