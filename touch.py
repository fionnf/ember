# ============================================================
#  touch.py  —  Capacitive touch detection for Pico
# ============================================================
# Technique: charge-time measurement.
#   1. Drive the pin HIGH briefly (charges the pad + your finger's capacitance)
#   2. Switch to INPUT and count how long it takes to discharge through a
#      pull-down resistor.  A touched pad takes longer → higher count.
#
# Wiring per sensor:
#   GPIO pin ──┬── 1 MΩ resistor ── GND
#              └── touch pad (bare copper, foil, or wire)
#
# No external ADC needed — pure GPIO timing on the Pico.

import machine
import utime
from config import TOUCH_THRESHOLD, HOLD_TIME_MS


class TouchSensor:
    """
    Single capacitive touch sensor on one GPIO pin.

    Events produced by update():
      "tap"       — brief touch then release
      "hold"      — finger held for HOLD_TIME_MS or longer
      None        — no new event this tick
    """

    def __init__(self, pin: int, samples: int = 10):
        self._samples = samples
        # One reusable Pin object. Constructing a Pin per measurement meant
        # an allocation on every main-loop iteration (~1000/s) — pure GC churn
        # in the hottest path in the firmware.
        self._pin = machine.Pin(pin, machine.Pin.OUT)
        # Baseline calibrated at startup
        self._baseline = self._measure_raw_avg()
        self._is_touched = False
        self._touch_start = 0
        self._hold_fired = False

    # ── Calibration ─────────────────────────────────────────

    def calibrate(self):
        """Re-measure baseline (call when you know nobody is touching)."""
        self._baseline = self._measure_raw_avg()

    # ── Internal measurement ─────────────────────────────────

    def _measure_raw(self) -> int:
        """
        One charge-time measurement.
        Returns a count proportional to capacitance.
        """
        pin = self._pin
        pin.init(machine.Pin.OUT)
        pin.value(1)
        utime.sleep_us(10)           # charge
        pin.init(machine.Pin.IN)     # release to float
        count = 0
        # Count loops until pin goes LOW (discharges through pull-down)
        while pin.value() == 1:
            count += 1
            if count > 10_000:       # safety cap
                break
        return count

    def _measure_raw_avg(self) -> float:
        """Average several samples to reduce noise."""
        total = 0
        for _ in range(self._samples):
            total += self._measure_raw()
            utime.sleep_us(500)
        return total / self._samples

    def _is_currently_touched(self) -> bool:
        val = self._measure_raw()
        return (val - self._baseline) > TOUCH_THRESHOLD

    # ── Event polling ────────────────────────────────────────

    def update(self):
        """
        Call this every loop iteration.
        Returns: "tap", "hold", or None.
        """
        touched = self._is_currently_touched()
        now = utime.ticks_ms()

        if touched and not self._is_touched:
            # Finger just landed
            self._is_touched  = True
            self._touch_start = now
            self._hold_fired  = False

        elif touched and self._is_touched:
            # Finger still held — check for hold event
            if (not self._hold_fired and
                    utime.ticks_diff(now, self._touch_start) >= HOLD_TIME_MS):
                self._hold_fired = True
                return "hold"

        elif not touched and self._is_touched:
            # Finger lifted
            self._is_touched = False
            if not self._hold_fired:
                return "tap"

        return None


class TouchManager:
    """
    Manages multiple touch sensors and merges their events.
    Returns the first event seen across any sensor per update() call.
    """

    def __init__(self, pin_list: list):
        self.sensors = [TouchSensor(p) for p in pin_list]

    def calibrate_all(self):
        for s in self.sensors:
            s.calibrate()

    def update(self):
        """Returns "tap", "hold", or None."""
        for s in self.sensors:
            event = s.update()
            if event:
                return event
        return None
