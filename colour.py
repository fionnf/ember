# ============================================================
#  colour.py  —  Organic colour engine
# ============================================================
# All colours are warm white by default, with occasional tint
# shifts driven by touch impulses or autonomous idle drift.
# Everything is expressed as RGBW tuples (0-255 each).

import math
import urandom
import utime
from config import (
    BASE_WARM_WHITE, TINT_PALETTE,
    HUE_SHIFT_MIN, HUE_SHIFT_MAX,
    FADE_STEPS, FADE_DELAY_MS,
    BREATHE_SPEED, BREATHE_DEPTH,
    IDLE_DRIFT_INTERVAL_S,
    NUM_LEDS, LED_BRIGHTNESS,
)

# ── Helpers ──────────────────────────────────────────────────

def _lerp(a, b, t):
    """Linear interpolate between two values."""
    return a + (b - a) * t

def _lerp_colour(c1, c2, t):
    """Interpolate between two (R,G,B,W) tuples."""
    return tuple(int(_lerp(a, b, t)) for a, b in zip(c1, c2))

def _palette_colour(position: float) -> tuple:
    """
    Sample the TINT_PALETTE at a float position 0.0–1.0.
    Returns an (R, G, B, W) tuple blended with BASE_WARM_WHITE.
    position=0 → pure warm white; position=1 → fully saturated tint.
    """
    n = len(TINT_PALETTE)
    # Map position to palette index with smooth interpolation
    scaled  = position * (n - 1)
    idx     = int(scaled)
    frac    = scaled - idx
    if idx >= n - 1:
        tint_rgb = TINT_PALETTE[-1]
    else:
        c1, c2   = TINT_PALETTE[idx], TINT_PALETTE[idx + 1]
        tint_rgb = tuple(int(_lerp(a, b, frac)) for a, b in zip(c1, c2))

    # Blend tint into warm-white base
    # W channel decreases as colour saturation increases
    saturation = position * 0.6        # max 60% tint saturation feels organic
    r = int(_lerp(BASE_WARM_WHITE[0], tint_rgb[0], saturation))
    g = int(_lerp(BASE_WARM_WHITE[1], tint_rgb[1], saturation))
    b = int(_lerp(BASE_WARM_WHITE[2], tint_rgb[2], saturation))
    w = int(BASE_WARM_WHITE[3] * (1.0 - saturation * 0.5))
    return (r, g, b, w)


# ── ColourEngine class ───────────────────────────────────────

class ColourEngine:
    """
    Maintains current colour state and drives organic transitions.

    Typical loop usage:
        engine.tick(strip)    # call every ~16 ms
        engine.impulse()      # call when a touch event fires
        engine.toggle_power() # call on long-press
    """

    def __init__(self):
        self._palette_pos  = 0.0         # 0.0 = warmest white, 1.0 = most tinted
        self._target_pos   = 0.0
        self._current_colour  = BASE_WARM_WHITE
        self._target_colour   = BASE_WARM_WHITE
        self._fade_step    = 0
        self._fading       = False
        self._powered_on   = True
        self._breathe_phase = 0.0
        self._last_drift   = utime.time()
        self._time_ms      = utime.ticks_ms()

    # ── Public controls ─────────────────────────────────────

    def impulse(self):
        """
        Fired by a touch event.  Picks a new nearby colour and starts fading.
        """
        if not self._powered_on:
            return
        shift = _rand_float(HUE_SHIFT_MIN, HUE_SHIFT_MAX)
        # Randomly go left or right along the palette
        direction = 1 if urandom.getrandbits(1) else -1
        new_pos   = self._palette_pos + direction * shift
        new_pos   = max(0.0, min(1.0, new_pos))
        self._start_fade(new_pos)

    def toggle_power(self):
        """Long-press handler: turn off or turn on."""
        self._powered_on = not self._powered_on
        if self._powered_on:
            self._start_fade(self._palette_pos)
        # Off state: strip cleared in tick()

    def force_colour(self, palette_pos: float):
        """
        Externally set palette position (called when MQTT event arrives).
        Mirrors what impulse() would have picked on the remote board.
        """
        if not self._powered_on:
            return
        self._start_fade(palette_pos)

    def set_power(self, on: bool):
        """Sync power state from remote board."""
        if on != self._powered_on:
            self.toggle_power()

    # ── Tick ─────────────────────────────────────────────────

    def tick(self, strip):
        """
        Must be called every frame (ideally every FADE_DELAY_MS ms).
        Updates animations and pushes to the strip.
        """
        now = utime.ticks_ms()
        dt  = utime.ticks_diff(now, self._time_ms)
        self._time_ms = now

        if not self._powered_on:
            strip.off()
            return

        # ── Advance fade ──
        if self._fading:
            t = self._fade_step / FADE_STEPS
            self._current_colour = _lerp_colour(
                self._current_colour, self._target_colour, t
            )
            self._fade_step += 1
            if self._fade_step >= FADE_STEPS:
                self._fading         = False
                self._current_colour = self._target_colour
                self._palette_pos    = self._target_pos

        # ── Breathing brightness ──
        self._breathe_phase += BREATHE_SPEED * dt
        breath = 1.0 + math.sin(self._breathe_phase) * BREATHE_DEPTH

        # ── Autonomous idle drift ──
        if utime.time() - self._last_drift > IDLE_DRIFT_INTERVAL_S:
            self._last_drift = utime.time()
            self.impulse()

        # ── Apply to strip ──
        r, g, b, w = self._current_colour
        r = min(255, int(r * breath))
        g = min(255, int(g * breath))
        b = min(255, int(b * breath))
        w = min(255, int(w * breath))
        strip.set_brightness(LED_BRIGHTNESS)
        strip.set_all(r, g, b, w)
        strip.show()

    # ── State export/import for MQTT ────────────────────────

    def get_event_payload(self) -> dict:
        """Return a dict to publish over MQTT after a local impulse."""
        return {
            "pos": round(self._target_pos, 4),
            "on":  self._powered_on,
        }

    # ── Internal ─────────────────────────────────────────────

    def _start_fade(self, new_pos: float):
        self._target_pos    = new_pos
        self._target_colour = _palette_colour(new_pos)
        self._fade_step     = 0
        self._fading        = True


# ── Utility ──────────────────────────────────────────────────

def _rand_float(lo: float, hi: float) -> float:
    """Random float in [lo, hi]."""
    r = urandom.getrandbits(16) / 65535.0
    return lo + r * (hi - lo)
