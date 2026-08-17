#!/usr/bin/env python3
"""
Sunrise gradient shape.

The dawn is meant to open on near-pure red, hold there, and only turn white
late. That is entirely a property of where SUNRISE_STOPS sit — they are evenly
spaced by index, so adding or moving one silently reshapes the whole fade. This
pins the shape rather than the exact numbers, so the stops stay tunable but the
character cannot drift back to "orange almost immediately".

Run from the repo root:   python3 tests/test_sunrise.py
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "stubs"))
sys.path.insert(0, ROOT)

import colour

FAILS = []

def check(cond, msg):
    if not cond:
        FAILS.append(msg)

def run():
    c = colour.sunrise_colour

    # Endpoints are contractual: main.py calls set_sunrise(1.0) to land the
    # alarm, and set_sunrise(1.0 - progress) to run a sunset backwards.
    check(c(0.0)[3] == 0, "dawn must start with the white LED fully off")
    check(c(1.0) == (255, 190, 110, 190), "dawn must still land on warm white")

    # Opens on red: green only a rounding error against a full red channel.
    r, g, b, w = c(0.0)
    check(r == 255, f"red channel should be full at t=0, got {r}")
    check(g <= 10, f"t=0 should be near-pure red, got green {g}")
    check(b == 0, f"t=0 should have no blue, got {b}")

    # Holds red: no white at all through the first half.
    for t in (0.1, 0.2, 0.3, 0.4, 0.5):
        check(c(t)[3] == 0, f"white LED must still be dark at t={t}, got {c(t)[3]}")
        check(c(t)[2] == 0, f"no blue before the white creeps in, at t={t}")

    # Whitens late, and only in the last stretch.
    first_white = next(i / 1000 for i in range(1001) if c(i / 1000)[3] > 0)
    check(first_white >= 0.55,
          f"white should not appear before t=0.55, appears at {first_white}")
    check(c(0.75)[3] < c(1.0)[3] * 0.5,
          "three-quarters through, white should still be well under half")

    # Monotonic on every channel — a dawn never steps backwards, and the
    # sunset path replays this same curve in reverse.
    prev = c(0.0)
    for i in range(1, 201):
        cur = c(i / 200)
        for ch, name in enumerate("RGBW"):
            check(cur[ch] >= prev[ch],
                  f"{name} went backwards at t={i/200:.3f}: {prev[ch]} → {cur[ch]}")
        prev = cur

    # Red is never given up, so the landing is warm white rather than cold.
    for i in range(201):
        check(c(i / 200)[0] == 255, f"red must stay full at t={i/200:.3f}")

    # Clamped outside 0–1 (main.py can hand it 1.0 - progress at the edges).
    check(c(-0.5) == c(0.0) and c(1.5) == c(1.0), "out-of-range t must clamp")

    if FAILS:
        print(f"FAIL — {len(FAILS)} problem(s):")
        for f in FAILS:
            print(f"  · {f}")
        return 1
    print(f"PASS — sunrise opens at {c(0.0)}, white first lights at t={first_white:.2f}, "
          f"lands on {c(1.0)}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
