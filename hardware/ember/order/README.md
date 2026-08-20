# Ordering EM-15 from JLCPCB

Everything in this folder is what you upload. Nothing else.

| File | Where it goes |
|---|---|
| `ember-gerbers.zip` | PCB tab — "Add gerber file" |
| `ember-bom.csv` | Assembly — BOM file |
| `ember-cpl.csv` | Assembly — CPL / pick-and-place file |

The annotated BOM with sourcing notes lives at `../ember-bom.csv`; the one in here is
trimmed to the four columns JLC's parser wants.

## Settings

**PCB tab** — dimensions should auto-read **187.1 × 52.1 mm**; check it.

- Layers 2 · Thickness **1.6 mm** · Copper **1 oz**
- Surface finish **HASL with lead** (cheapest, and its ~217 °C reflow is kinder to the
  LED lenses than lead-free's 245–250 °C)
- Solder mask **white** if it is within ~$0.15/board, else green. The board is the
  reflector inside the diffuser; white buys 10–20 % more light out.
- Silkscreen **black**
- Via covering: **tented**
- **PCB Qty 5** for a first run. Single boards, not panelised — panelising only pays
  from ~30 up.
- **Confirm Production File: YES.** Worth the day it costs on a first article.

**Assembly tab**

- **Economic PCBA**, **Top side only** (there is nothing on the bottom)
- Tooling holes: **Added by JLCPCB**
- **Confirm Parts Placement: YES**

## The two screens where boards get killed

**Parts review.** Resolve every "part not found" and never accept a suggested
alternative silently — that is exactly how a 0402 pad gets an 01005 part. Two lines
matter more than the rest:

- **LD1–LD15 must be C5378724**, a 4-channel RGBW in GRBW order, warm white. A
  3-channel RGB part fits the same footprint and is silently wrong.
- **U2 must be C7484** (SN74AHCT1G125). C7468 is the AHC version, two digits apart,
  and it fixes nothing — 3.3 V in, 3.3 V out, and the LEDs stay out of spec.

**Placement preview.** Check **all fifteen LED rotations** are identical. LED rotation is
the most common JLC PCBA error, because the reel convention often differs from the
footprint's. Zoom LD1 and LD15 and confirm DIN faces the previous LED's DOUT. Also check
J1's overhang at the board edge, and **Q1's source toward the input, drain toward the
load** — a reversed P-FET conducts through its body diode permanently and deletes the
soft-start silently.

## Order separately from LCSC, same week

Spares you will want: 20 LEDs, and 3 each of the module, the AHCT buffer, the LDO and
the FET. Also a **JST-PH 3-pin cable** for J4 and a TTP223 touch module.

## Known risks on this order

- **The firmware is not ported.** `NUM_LEDS` is still 10, `sk6812.py` still imports
  `rp2` (the C3 has no PIO) and `touch.py` still does charge-time timing rather than
  reading a TTP223. The boards will arrive before the software that drives them.
- **Stage 0 was skipped.** `machine.bitstream`, the GRBW order and a full OTA cycle on
  the C3 are unproven. That is the risk this order is buying information about.
- **C7429690 is a JST-PH clone.** Check its drawing against the land pattern.
