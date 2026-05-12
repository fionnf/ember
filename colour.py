# ============================================================
#  colour.py  —  Organic colour engine
# ============================================================
import math
import urandom
import utime
from config import (
    BASE_WARM_WHITE, TINT_PALETTE,
    HUE_SHIFT_MIN, HUE_SHIFT_MAX,
    FADE_STEPS, FADE_DELAY_MS,
    BREATHE_SPEED, BREATHE_DEPTH,
    IDLE_DRIFT_INTERVAL_S,
    NUM_LEDS, LED_BRIGHTNESS, NUM_GROUPS,
)
try:
    from config import REVERSE_LEDS
except ImportError:
    REVERSE_LEDS = False

# ── Helpers ──────────────────────────────────────────────────

def _lerp(a, b, t):
    return a + (b - a) * t

def _lerp_colour(c1, c2, t):
    return tuple(int(_lerp(a, b, t)) for a, b in zip(c1, c2))

def _rand_float(lo, hi):
    return lo + (urandom.getrandbits(16) / 65535.0) * (hi - lo)

def _palette_colour(position):
    n = len(TINT_PALETTE)
    scaled = position * (n - 1)
    idx    = int(scaled)
    frac   = scaled - idx
    if idx >= n - 1:
        tint_rgb = TINT_PALETTE[-1]
    else:
        c1, c2   = TINT_PALETTE[idx], TINT_PALETTE[idx + 1]
        tint_rgb = tuple(int(_lerp(a, b, frac)) for a, b in zip(c1, c2))

    sat = position
    r = int(_lerp(BASE_WARM_WHITE[0], tint_rgb[0], sat))
    g = int(_lerp(BASE_WARM_WHITE[1], tint_rgb[1], sat))
    b = int(_lerp(BASE_WARM_WHITE[2], tint_rgb[2], sat))
    w = int(BASE_WARM_WHITE[3] * (1.0 - sat))  # W fades out as colour takes over
    return (r, g, b, w)


# ── ColourEngine ─────────────────────────────────────────────

class ColourEngine:
    """
    NUM_GROUPS independent colour groups across the strip.
    Each group fades to its own palette position and warm-white level.
    """

    def __init__(self):
        n = NUM_GROUPS
        self._n           = n
        self._pos         = [0.0] * n
        self._target_pos  = [0.0] * n
        self._colour      = [BASE_WARM_WHITE] * n
        self._target_col  = [BASE_WARM_WHITE] * n
        self._fade_step   = [0] * n
        self._fading      = [False] * n
        # Warm-white intensity per group (0.6–1.0)
        self._w_level     = [1.0] * n
        self._w_target    = [1.0] * n
        self._w_step      = [0] * n
        self._w_fading    = [False] * n
        # Breathing — stagger starting phases so groups pulse out of sync
        self._breathe_phase = [i * (6.28 / n) for i in range(n)]

        self._powered_on  = True
        self._power_level = 1.0
        self._power_dir   = 0
        self._last_drift  = utime.time()
        self._time_ms     = utime.ticks_ms()

    # ── Public controls ─────────────────────────────────────

    def impulse(self):
        if not self._powered_on:
            return
        for i in range(self._n):
            shift     = _rand_float(HUE_SHIFT_MIN, HUE_SHIFT_MAX)
            direction = 1 if urandom.getrandbits(1) else -1
            new_pos   = max(0.0, min(1.0, self._pos[i] + direction * shift))
            self._start_fade(i, new_pos)
            self._w_target[i] = _rand_float(0.6, 1.0)
            self._w_step[i]   = 0
            self._w_fading[i] = True

    def toggle_power(self):
        self._powered_on = not self._powered_on
        self._power_dir  = 1 if self._powered_on else -1

    def force_colour(self, palette_pos):
        if not self._powered_on:
            return
        for i in range(self._n):
            jitter  = _rand_float(-0.08, 0.08)
            new_pos = max(0.0, min(1.0, palette_pos + jitter))
            self._start_fade(i, new_pos)

    def set_power(self, on):
        if on != self._powered_on:
            self.toggle_power()

    # ── Tick ─────────────────────────────────────────────────

    def tick(self, strip):
        now = utime.ticks_ms()
        dt  = utime.ticks_diff(now, self._time_ms)
        self._time_ms = now

        # Power fade
        if self._power_dir != 0:
            self._power_level += self._power_dir * (dt / 800.0)
            if self._power_level >= 1.0:
                self._power_level = 1.0
                self._power_dir   = 0
            elif self._power_level <= 0.0:
                self._power_level = 0.0
                self._power_dir   = 0
                strip.off()
                return

        if not self._powered_on and self._power_level == 0.0:
            strip.off()
            return

        # Idle drift
        if self._powered_on and utime.time() - self._last_drift > IDLE_DRIFT_INTERVAL_S:
            self._last_drift = utime.time()
            self.impulse()

        leds_per_group = NUM_LEDS // self._n
        strip.set_brightness(LED_BRIGHTNESS)

        for i in range(self._n):
            # Hue fade
            if self._fading[i]:
                t = self._fade_step[i] / FADE_STEPS
                self._colour[i]   = _lerp_colour(self._colour[i], self._target_col[i], t)
                self._fade_step[i] += 1
                if self._fade_step[i] >= FADE_STEPS:
                    self._fading[i]  = False
                    self._colour[i]  = self._target_col[i]
                    self._pos[i]     = self._target_pos[i]

            # W-level fade
            if self._w_fading[i]:
                t = self._w_step[i] / FADE_STEPS
                self._w_level[i] = _lerp(self._w_level[i], self._w_target[i], t)
                self._w_step[i] += 1
                if self._w_step[i] >= FADE_STEPS:
                    self._w_fading[i] = False
                    self._w_level[i]  = self._w_target[i]

            # Breathing
            self._breathe_phase[i] += BREATHE_SPEED * dt
            breath = 1.0 + math.sin(self._breathe_phase[i]) * BREATHE_DEPTH

            scale = breath * self._power_level
            r, g, b, w = self._colour[i]
            r    = min(255, int(r * scale))
            g    = min(255, int(g * scale))
            b    = min(255, int(b * scale))
            w    = min(255, int(w * self._w_level[i] * scale))

            start = i * leds_per_group
            end   = NUM_LEDS if i == self._n - 1 else start + leds_per_group
            for j in range(start, end):
                idx = (NUM_LEDS - 1 - j) if REVERSE_LEDS else j
                strip.set(idx, r, g, b, w)

        strip.show()

    # ── MQTT payload ────────────────────────────────────────

    def get_event_payload(self):
        avg_pos = sum(self._pos) / self._n
        return {"pos": round(avg_pos, 4), "on": self._powered_on}

    # ── Internal ─────────────────────────────────────────────

    def _start_fade(self, group, new_pos):
        self._target_pos[group] = new_pos
        self._target_col[group] = _palette_colour(new_pos)
        self._fade_step[group]  = 0
        self._fading[group]     = True
