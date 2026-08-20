# FL-11 rev B — KiCad project

**Linked Friend Lights · FL-11 rev B · designed by Fionn Ferreira**
<https://github.com/fionnf/linked-friend-lights-public>

Generated from [`../../docs/hardware/README.md`](../../docs/hardware/README.md).
Open `fl11.kicad_pcb` with KiCad 9 or 10.

## What changed in rev B

The electronics moved off the end of the strip into a **rear bulge at the middle**, so the
USB-C plugs in from the back. The LED row is **continuous and unbroken** — all eleven at
16.66667 mm pitch, nothing interrupting the lit line.

```
   x=0                                                    196        228
   |<------------- LED strip, 11 x SK6812 RGBW ----------->|<- tab ->|
   +-------------------------------------------------------+---+-----+
   | (1)(2)(3)(4)(5)(6)(7)(8)(9)(10)(11)   y = 11.000       | . | pad |
   +----------------+--------------+-----------------------+---+-----+
        y=20        |   BULGE      |
                    |  MCU, power  |   USB-C on the UNDERSIDE
                    |  touch front |   antenna points at the free y=48 edge
              x=72  +--------------+ x=120
                           y=48
```

Deleting the old 56 mm head paid for the bulge almost exactly:

| | rev A | rev B |
|---|---|---|
| Outline | 282 × 20 | 228 × 20 strip + 48 × 28 bulge |
| Board area | 5640 mm² | 5904 mm² (**+4.7 %**) |
| Antenna → nearest LED copper | at a free end | **21.9 mm** (rule: 8 mm) |
| Bottom-side parts | 0 | **1** (J1 only) |

**Cost impact.** One bottom-side part means a second assembly setup — roughly **+$0.63/unit
at qty 100** against the $2.90 of headroom in the §9.2 budget. The outline is no longer a
plain rectangle, so the 6-up panel needs re-nesting; bulges alternating up/down should
recover most of the utilisation, but that has to be laid out and re-quoted.

## Status — read before ordering

**Not yet orderable.** Placed, netlisted, poured, partly routed.

| | |
|---|---|
| Footprints | 67, DRC **0 errors** |
| Nets | 35, every pad assigned |
| Routed | LED chain, buffer→LD1, SENSE end-to-end, tab electrodes, bypass vias, all pours |
| **Not routed** | **56 connections in the bulge** — power path, USB pair, module I/O |

Reproduce: `kicad-cli pcb drc --format json --severity-error --refill-zones fl11.kicad_pcb`

## Deviations from the written design, and why

| Change | Reason |
|---|---|
| **R11 is 100 Ω, was 47 Ω** | §6.6 sized 47 Ω for a 12 mm buffer→LD1 run and argued the trace is electrically short. In rev B that run is **~80 mm**, past the doc's own ~75 mm critical length, so it now needs real series termination: AHCT Zout 15–25 Ω + ~120 Ω trace ≈ 100 Ω. |
| **SENSE runs in a guarded y=18.6 lane**, not the y=1.4 channel | It has to cross the LED data channel to reach the far side, and *every* x between LEDs carries a DOUT→DIN hop. The lane is guarded above and below by GND, and SENSE crosses the pours exactly once, at right angles. It climbs at x=188 — past LD11_DOUT's end at 186, the only place it can cross the data channel with no hop present. |
| **Cross-section mirrored** (GND at y=0 side, 5 V under the LED anodes) | The LED package puts VDD and DIN on the same side, so head-to-tab data flow forces VDD to the y=20 side. Also makes the doc self-consistent: §7.2's caps at y=15.50 only work if 5 V is the bottom band. |
| **H1/H2 in the bulge**, not flanking J1 | An M2.5 screw head does not fit beside a 16-pin USB-C receptacle (courtyard x 0.69–10.20, y 4.63–15.37) on a 20 mm board. |
| **Mouse-bite webs at y=8.73 and 11.27**, 1.8 mm wide | Exactly where SENSE and GND cross the break line. The "centre bridge" needs material under the traces. |
| **LEDs at 90°** | The rotation that gives DIN-left / DOUT-right, so no two hops cross. Verify pad 1 against the LCSC drawing — §6.6 flags a rotated LED row as a scrap panel. |

## Still to do, in §7.9 order

1. Route VBUS → F1 → Q1 → star node → 5 V into the bulge pour, clearing the antenna keep-out.
2. Route D+/D− as a 90 Ω pair through U4 to IO18/IO19 — matched within 5 mm, no vias.
3. Route 3V3, EN, straps, IO9/SW1.
4. Stitching vias; silkscreen for the break block and `CUT -> D1`.
5. Re-nest the panel around the bulge and re-quote.

Do not autoroute.

## Provenance of the module pad map

`U1`'s footprint and pin numbering come from **Espressif's official KiCad library**, not from
me — §6.5 explicitly refused to invent the ESP32-C3-MINI-1 pad map. Cross-check against the
datasheet before ordering.

## Regenerating

```
python3 build_fl11.py fl11.kicad_pcb <Espressif.pretty> c3_padmap.json
python3 route_fl11.py fl11.kicad_pcb
```
Needs KiCad's bundled Python. Zone filling is done by `kicad-cli --refill-zones`, because
`ZONE_FILLER` segfaults without a wxApp. Two other API traps are noted in the scripts:
a footprint must be added to the board *before* `Flip()`, and `SetOutline()` does not take
ownership of the polygon.
