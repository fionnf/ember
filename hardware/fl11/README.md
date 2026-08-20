# FL-11 rev C — KiCad project

**Linked Friend Lights · FL-11 rev C · designed by Fionn Ferreira**
<https://github.com/fionnf/linked-friend-lights-public>

Generated from [`../../docs/hardware/README.md`](../../docs/hardware/README.md).
Open `fl11.kicad_pcb` with KiCad 9 or 10.

## What changed

**rev B** moved the electronics off the end of the strip into a rear bulge at the middle, so
the USB-C plugs in from the back. **rev C** moved the touch terminals there too: the pad is
now a snap-off section *beside* the bulge, not a tab at the far end.

```
   x=0                                              187
   |<---------- 11 x SK6812 RGBW, unbroken --------->|
   +--------------------------------------------------+
   | (1)(2)(3)(4)(5)(6)(7)(8)(9)(10)(11)  y = 11.000  |
   +----------------+--------------+---+--------------+
        y=20        |  ELECTRONICS |sn |  TOUCH PAD   |
                    |  MCU, power  |ap |  PAD_S       |
                    |  USB-C under |   |  PAD_G       |
              x=72  +--------------+---+--------------+ x=145
                         y=48    x=120 (break + J2/J3)
```

Every wire now leaves the lamp from one place. The board also got **smaller**:

| | rev A | rev B | rev C |
|---|---|---|---|
| Outline | 282 × 20 | 228 × 20 + 48 × 28 | **187 × 20 + 48 × 28 + 25 × 28** |
| Area | 5640 mm² | 5904 mm² | **5784 mm²** (+2.6 % vs A, −2.0 % vs B) |
| SENSE run | 195 mm | ~70 mm | **~13 mm** |
| SENSE crosses the LED data channel | no | yes, once | **no** |

**The real win is SENSE.** §7.5 calls touch "the least-certain subsystem in this design". In
rev A and B the sense line was a long high-impedance run down a strip carrying a 0.89 A
switching rail. In rev C it never leaves the bulge, sits inside the bulge's GND pour — which
*is* the guard — and never crosses the LED data channel. The guarded y=18.6 lane rev B needed
is gone entirely, and so is the awkward climb at x=188.

Deleting the end tab also removed the 31 mm tab, the gap, and the strip's break slot.

**Cost.** Still one bottom-side part (J1), so the second-setup charge stands at roughly
**+$0.63/unit at qty 100**. The outline is a T with a notch, so the 6-up panel still needs
re-nesting and re-quoting.

## Status — read before ordering

**Not yet orderable.** Placed, netlisted, poured, partly routed.

| | |
|---|---|
| Footprints | 67, DRC **0 errors** |
| Nets | 35, every pad assigned |
| Routed | LED chain, buffer→LD1, SENSE end-to-end, tab electrodes, bypass vias, all pours |
| **Not routed** | **51 connections in the bulge** — power path, USB pair, module I/O |

Reproduce: `kicad-cli pcb drc --format json --severity-error --refill-zones fl11.kicad_pcb`

## Deviations from the written design, and why

| Change | Reason |
|---|---|
| **R11 is 100 Ω, was 47 Ω** | §6.6 sized 47 Ω for a 12 mm buffer→LD1 run and argued the trace is electrically short. In rev B that run is **~80 mm**, past the doc's own ~75 mm critical length, so it now needs real series termination: AHCT Zout 15–25 Ω + ~120 Ω trace ≈ 100 Ω. |
| **Touch pad beside the bulge, end tab deleted** | rev C. Puts the wire terminals with the rest of the wiring and cuts SENSE from ~70 mm to ~13 mm. It no longer crosses the LED data channel — which mattered, because *every* x between LEDs carries a DOUT→DIN hop, so rev B had to climb at x=188, past LD11_DOUT's end, as the only legal crossing point. |
| **Touch pad electrodes 17 × 12 mm** (204 mm² each), was 25 × 8 | Same area as §7.5 specifies, reproportioned for a pad section that is tall rather than long. Equal areas are still correct: `C ∝ s(A−s)/A` maximises at `s = A/2`. |
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
