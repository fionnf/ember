# FL-11 rev D — KiCad project

**Linked Friend Lights · FL-11 rev D · designed by Fionn Ferreira**
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

## rev D

Three changes, all from real problems:

**Back to single-sided.** J1 is a *horizontal* receptacle, so the plug enters along the board
plane from the rear edge whichever face it is soldered to. Bottom-mounting it bought
flushness and cost a whole second assembly setup. It is on the top side now: rear entry
unchanged, **the ~$0.63/unit second-setup charge is gone**, and the CPL has zero bottom-side
parts.

**The pad section could not actually snap off.** In rev C it touched the rest of the board on
*two* edges — the bulge at x=120 and the strip along y=20 — and only the first was cut. It now
hangs off the bulge alone: the strip is notched away over y 20–22, so the pad is cantilevered
and can be gripped and bent. Retaining material is two 1.3 mm webs carrying SENSE and GND plus
two 0.4 mm corner ligaments, **≈3.0 mm against rev C's 4.3 mm on two separate edges.** Webs are
1.3 mm rather than narrower because a 0.30 mm trace needs 0.5 mm to each routed edge; below
that the fab flags it.

**The BOM carries real LCSC numbers.** Blank part numbers are what made JLC guess, and its
guess for the 100 k line was C880433 — an **01005** part, Extended, 6 in stock, MOQ 5597. Every
line is now filled from a live stock check, favouring Basic/Preferred with deep stock.

| Line | Part | Why |
|---|---|---|
| 100 nF ×15 | **C1525** | Basic, 16.4 M stock |
| 5k1 ×7 | **C25905** | Basic, 2.24 M stock |
| 100 k ×2 | **C25086** | Preferred, 469 k stock — *not* the 01005 JLC suggested |
| 100 R | **C22369194** | 1.13 M stock, 5 % — tolerance is irrelevant for series damping |
| 22 µF ×4 | **C6119897** | Preferred, 184 k, **$0.02 vs $0.12** for the 25 V Basic part |
| 4M7 | **C49655641** | Extended, **only ~9.8 k stock** — buy in one PO |
| 470 µF | **C47023096** | 7.4 k stock, D8 × 10.5 mm |
| USBLC6 | **C2687116** | 150 k stock |
| AP2112K-3.3 | **C23380830** | 31 k stock |
| Tact | **C18078117** | 20.5 k stock |
| Module | **C2838502** | 26 k stock, **$3.84 — the doc modelled $2.92** |

Two still need you: **F1 (PPTC 1812, 2 A hold / 4 A trip, ≤0.06 Ω)** is not filled — I could not
verify one, so it is blank rather than guessed. And **the LED, C5378724, is unverified for
stock** and is §9.1's number one live risk.

**Two cost corrections, both upward:** the module is ~$0.9/board dearer than modelled, and with
more Extended lines than the doc's assumed five, the fixed charge `8.18 + 1.53 + 3.07 × N`
rises — roughly +$0.30/board at qty 30. Against that, single-sided gives back ~$0.63/unit.

**22 µF derating:** the 10 V part loses roughly half its capacitance at 5 V DC bias, so budget
~10–12 µF effective. That is fine here — C1's 470 µF carries the bulk and C4 only has to cover a
2 ms burst — but it is a real difference from the nameplate value.

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
