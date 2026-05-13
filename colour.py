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
    NUM_LEDS, LED_BRIGHTNESS,
    NUM_GROUPS, GROUP_MIN_LEDS, GROUP_MAX_LEDS,
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

def _random_partition(total, n, mn, mx):
    """
    Split `total` LEDs into `n` groups, each between mn and mx LEDs.
    Returns a list of n integers that sum to total.
    """
    mn = max(1, mn)
    mx = min(mx, total - (n - 1) * mn)  # ensure others can have at least mn
    sizes = []
    remaining = total
    for i in range(n):
        left = n - i
        lo = max(mn, remaining - left * mx)
        hi = min(mx, remaining - (left - 1) * mn)
        if lo > hi:
            lo = hi = remaining - (left - 1) * mn
        size = int(_rand_float(lo, hi + 1))
        size = max(mn, min(mx, size))
        sizes.append(size)
        remaining -= size
    # Distribute any rounding remainder into the last group
    sizes[-1] += remaining
    return sizes

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
        # LED counts per group — re-randomised on every impulse
        self._group_sizes   = _random_partition(NUM_LEDS, n, GROUP_MIN_LEDS, GROUP_MAX_LEDS)

        self._powered_on  = True
        self._power_level = 1.0
        self._power_dir   = 0
        self._last_drift  = utime.time()
        self._time_ms     = utime.ticks_ms()

    # ── Public controls ─────────────────────────────────────

    def impulse(self):
        if not self._powered_on:
            return
        # Re-partition the strip into new random group sizes
        self._group_sizes = _random_partition(NUM_LEDS, self._n, GROUP_MIN_LEDS, GROUP_MAX_LEDS)
        for i in range(self._n):
            # Jump to a fully random palette position — no sequential order
            new_pos = _rand_float(0.0, 1.0)
            self._start_fade(i, new_pos)
            self._w_target[i] = _rand_float(0.6, 1.0)
            self._w_step[i]   = 0
            self._w_fading[i] = True

    def toggle_power(self):
        self._powered_on = not self._powered_on
        self._power_dir  = 1 if self._powered_on else -1

    def force_colour(self, groups):
        """Apply exact group state received from remote board."""
        if not self._powered_on:
            return
        for i, g in enumerate(groups[:self._n]):
            self._group_sizes[i] = g["size"]
            self._start_fade(i, g["pos"])
            self._w_target[i] = g["w"]
            self._w_step[i]   = 0
            self._w_fading[i] = True

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

        strip.set_brightness(LED_BRIGHTNESS)
        cursor = 0

        for i in range(self._n):
            # Hue fade
            if self._fading[i]:
                t = self._fade_step[i] / FADE_STEPS
                self._colour[i]    = _lerp_colour(self._colour[i], self._target_col[i], t)
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
            r = min(255, int(r * scale))
            g = min(255, int(g * scale))
            b = min(255, int(b * scale))
            w = min(255, int(w * self._w_level[i] * scale))

            group_end = cursor + self._group_sizes[i]
            for j in range(cursor, group_end):
                idx = (NUM_LEDS - 1 - j) if REVERSE_LEDS else j
                strip.set(idx, r, g, b, w)
            cursor = group_end

        strip.show()

    # ── MQTT payload ────────────────────────────────────────

    def get_event_payload(self):
        groups = [
            {"pos": round(self._target_pos[i], 4),
             "w":   round(self._w_target[i], 3),
             "size": self._group_sizes[i]}
            for i in range(self._n)
        ]
        return {"groups": groups, "on": self._powered_on}

    # ── Internal ─────────────────────────────────────────────

    def _start_fade(self, group, new_pos):
        self._target_pos[group] = new_pos
        self._target_col[group] = _palette_colour(new_pos)
        self._fade_step[group]  = 0
        self._fading[group]     = True
