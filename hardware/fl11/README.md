# FL-11 KiCad project

Generated from the design in [`../../docs/hardware/README.md`](../../docs/hardware/README.md).
Open `fl11.kicad_pcb` with KiCad 9 or 10.

## Status — read this before ordering anything

**This is not yet orderable.** The board is placed, netlisted, poured and partly routed.
The head-section nets still need hand routing.

| | |
|---|---|
| Footprints placed | 67, all at the §7 coordinates |
| Nets defined | 35, every pad assigned |
| DRC | **0 errors** |
| Routed | LED chain, buffer→LD1, SENSE end-to-end, tab electrodes, LED bypass vias, all pours |
| **Not routed** | **101 connections in the head** — power path, USB differential pair, module I/O |

`kicad-cli pcb drc --format json --severity-error --refill-zones fl11.kicad_pcb` reproduces
the check. The gerbers in `gerbers/` correspond to this partly-routed state: they are a
verification artifact, not a fab order.

## What remains, in the order §7.9 gives

1. Route VBUS → F1 → Q1 → star node → the 5 V bridge (2.0 mm, y 8.6–10.6), clearing the antenna keep-out.
2. Route D+/D− as a 90 Ω pair through U4 to IO18/IO19 — matched within 5 mm, no vias, no stubs.
3. Route 3V3, EN, straps, IO9/SW1.
4. Add stitching vias and the silkscreen called for in §7.6 (`CUT -> D1`, the break block, LED1 arrow).
5. Panelise 6-up to 282 × 140 mm per §7.8, then re-export.

Do not autoroute. SENSE, the 5 V path and D± all carry constraints an autorouter ignores.

## Deviations from the written design, and why

| Change | Reason |
|---|---|
| **Cross-section mirrored** — GND pour at the y=0 side, 5 V pour at y 12.4–17.0 | The LED package puts VDD and DIN on the same side, so a head→tab data flow forces VDD to the y=20 side. Mirroring keeps the clean daisy chain *and* raises SENSE-to-5V separation from 9.1 mm to ~12 mm. It also makes the doc self-consistent: §7.2 places the bypass caps at y=15.50, which only works if 5 V is the bottom band. |
| **SENSE channel moved to the y=0 edge** (guards 0.40–0.90 and 1.90–2.40, trace at y=1.40) | Follows the mirror above; keeps SENSE as far from the switching rail as the board allows. |
| **H1/H2 moved to x=13.5** from the specified x=4.50 | A real 16-pin USB-C receptacle's courtyard is x 0.69–10.20, y 4.63–15.37. An M2.5 screw head does not fit beside it on a 20 mm board. Moved behind the connector; the axial cable-yank load still lands on the screws, which was the point. |
| **Mouse-bite webs at y=8.73 and 11.27**, widened to 1.8 mm | These are exactly where SENSE and GND cross the break line. The doc's "centre bridge" needs material under the traces. |
| **LEDs at 270°** | The rotation that puts VDD under the 5 V pour and GND under the GND pour. Verify against the LCSC part drawing before ordering — §6.6 flags this as a scrap-panel risk. |

## Provenance of the module pad map

`U1`'s footprint and pin numbering come from Espressif's official KiCad library, not from
me. §6.5 explicitly refused to invent the ESP32-C3-MINI-1 pad map, so the mapping
(IO5→19, IO3→6, IO2→5, IO8→22, IO9→23, IO18→26, IO19→27, IO20→30, IO21→31, EN→8, 3V3→3)
was extracted from `Espressif.kicad_sym`. Cross-check it against the datasheet anyway.

## Regenerating

```
python3 build_fl11.py fl11.kicad_pcb <Espressif.pretty> c3_padmap.json   # place + netlist
python3 route_fl11.py fl11.kicad_pcb                                      # pours + routing
```
Both need KiCad's bundled Python (it carries `pcbnew`). Zone filling is done by
`kicad-cli --refill-zones`, because `ZONE_FILLER` segfaults without a wxApp.
