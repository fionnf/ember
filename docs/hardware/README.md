# EM-15 — integrated lamp board

**Ember · EM-15 rev C · designed by Fionn Ferreira**
<https://github.com/fionnf/linked-friend-lights-public>

> **rev C supersedes the geometry below.** The electronics moved off the end of the strip
> into a rear bulge at the middle so the USB-C plugs in from the back; the LED row stayed
> continuous. The board is now a 228 × 20 mm strip with a 48 × 28 mm bulge, not 282 × 20.
> Everything else — the schematic, the BOM, the power budget, the bring-up plan — is
> unchanged, with two exceptions noted in [`../../hardware/fl11/README.md`](../../hardware/fl11/README.md):
> `R11` becomes 100 Ω, and SENSE runs in a guarded y=18.6 lane. The built KiCad project
> is in `hardware/fl11/`.

This is the hardware design for a single PCB that replaces the discrete build (Pico W + separate SK6812 strip + a foil touch pad on a wire). One piece of FR4 carries the MCU, the radio, eleven SK6812 RGBW LEDs at standard 60 LED/m pitch, power input and protection, and a capacitive touch pad on a break-away tab. It is designed to be ordered from JLCPCB as a panel, assembled turnkey with no hand-soldering and no per-unit calibration, and to run the existing MicroPython firmware with a six-line `config.py` change and one rewritten driver file.

The optimisation target is **total landed cost per assembled board at qty 100**, subject to a hard floor: it has to work on the first batch. A board that needs rework, per-unit tuning, or a revision spin is not cheap at any BOM price. Everything below states what a choice cost and what would break if it were deleted.

**Where it lands: $7.60 landed per assembled board at qty 100, $17.10 for a complete boxed lamp** including a 2.4 A supply and a self-printed enclosure. That is inside the $20 target with $2.90 of room, and the honest electronics-only floor with these features is about $5.60.

---

## 1. Assumptions, and the decisions still open

### Assumptions this design is built on

| Assumption | Consequence if wrong |
|---|---|
| Volume is 10–100 units, friends scale, possible small sale later | The whole cost model is setup-dominated. At qty 500 the fixed costs vanish and different trades open up (injection moulding, 4 layers, a bare RP2040) |
| Turnkey assembly, strong preference for JLCPCB library parts, no hand-soldering | This is what eliminated the Pico W carrier — JLCPCB does not stock the Pico W, so it is consigned or self-reflowed, and self-reflowing 100 castellated modules *is* hand-soldering |
| Pre-certified radio module, not a bare MCU + antenna | Correct, and I did challenge it — see §4. A bare RP2040 + RM2 layout stacked four independent first-article killers and RM2 is not a JLC library part either, so the radio ends up consigned anyway |
| Keep the 10× SK6812 RGBW linear light engine | Kept, at 11 LEDs. RGBW (four channels, GRBW order) is load-bearing: `colour.py`'s entire model is W-channel-dominant (`BASE_WARM_WHITE = (0,0,0,200)`) |
| MicroPython + existing OTA/config keeps working | Drove the pin map (`LED_PIN` stays 5) and the driver strategy (identical class API, capability-detected back end, one file serves both hardware generations) |

### Open decisions — yours, not mine

| # | Decision | My recommendation | What it costs |
|---|---|---|---|
| 1 | **MCU family.** ESP32-C3-MINI-1 vs a Pico W carrier | **ESP32-C3**, gated on Stage 0 passing before any PCB is ordered | Pico W is **+$5.20/unit, +$520 over 100**, and reintroduces the consignment/self-reflow problem. The C3 costs one rewritten file (~40 lines), testable for $15 on a dev board before you spend anything |
| 2 | **Enclosure: printed in-house or bought in?** | In-house if you can commit the machine time; otherwise the $20 target fails and should be moved | Three printed parts (base, 184 mm spine, top cap), ~55–70 g and **~6.5 machine-hours per lamp → ~650 printer-hours for 100 units**, roughly a month of continuous single-machine printing, plus 5–10 % print failures. Outsourced MJF/SLS is $6–9/unit → complete lamp $22–25, **over target** |
| 3 | **Board width 20.0 mm.** Narrowed from 24.0 to fit the diffuser tube with a spine (see §7.3) | 20.0 mm board in a 30 mm OD tube | Free, in fact −$0.15/board of PCB area. The alternative is a 35 mm OD tube (+$1.20) with a 24 mm board |
| 4 | **Ship a 5 V / 2.4 A supply in the box?** | **Yes** | $3.50. If you don't, `MAX_CHANNEL_SUM` must drop from 680 to ~450 so the lamp survives a legacy 500 mA host — visibly dimmer, and a product decision rather than an implementation detail |
| 5 | **White vs green soldermask** | **White**, unless JLC quotes more than $0.15/board | +$0.10/board. The board is the reflector inside a diffuser tube; 10–20 % more light out is the cheapest optical gain available |
| 6 | **Leaded (Sn63Pb37) vs lead-free reflow** | **Leaded** at friends scale | Leaded is JLC's cheaper option **and** its ~217 °C peak is materially kinder to the SK6812 lens and phosphor than 245–250 °C. It is **not RoHS**. Selling into the EU/UK means lead-free (+~$0.30/board) and revalidation |
| 7 | **Certification, if "possible small sale later" becomes real** | Have this conversation before you commit | The module carries FCC/IC/CE/UKCA modular approval, so no intentional-radiator campaign. A commercial sale still needs FCC Part 15B ($1.5–3k) and a CE/RED DoC ($1–3k). **That bill exceeds the entire BOM cost of your first 300 units** |
| 8 | **`GROUP_MAX_LEDS`: 8 or 9?** | **Keep 8.** See §8.2 — I ran the actual partition algorithm 200 000 times | Raising it to 9 to make the constant "honest" makes `(9,1,1)` the single most common partition, once every nine taps. That is a visible aesthetic regression for a cosmetic correctness gain |
| 9 | **Touch pull-down value and overlay thickness** | Fit **4.7 MΩ**, print the cap's touch face at **1.0 mm**, and settle both from Stage 1 measurement | Both are no-respin knobs. Touch is the least-certain subsystem in this design and §7.5 says so plainly rather than quoting modelled numbers as facts |

---

## 2. Architecture

```
                        EM-15  —  282.0 × 20.0 × 1.6 mm, 2 layer, single-sided SMT

 x=0                       56                                              239           250   282
 |<--------- HEAD --------->|<------------- LIT ZONE 183.33 --------------->|<-- gap -->|<-TAB->|
 +--------------------------+------------------------------------------------+---.---+--------+
 | [USB-C]  470uF  Q1  LDO  | (1) (2) (3) (4) (5) (6) (7) (8) (9) (10) (11)  |   .   | SENSE  |
 |          F1   ESD  [C3]  |      16.6667 mm pitch, all on y = 11.0         |   .   | ------ |
 |               [AHCT] [R] |                                                |   .   |  GND   |
 +--------------------------+------------------------------------------------+---.---+--------+
                                                                  break line ----'  (x = 250)


 USB-C 16P sink --+-- VBUS --[PPTC 2A/4A]--+-- AO3401A P-FET --+-- +5V (~4.94 V)
   CC1 -[5k1]-GND |                    S <-|  soft-start,      |
   CC2 -[5k1]-GND |     R 100k G->GND      |  drain to load    |
   D+/D- ---------+-[USBLC6-2SC6]-> IO19/IO18   C 100n G->S    |
                  |                                            |
                  +-- USBLC6 VBUS pin = ESD clamp              |
                                                               |
   +5V --+-- AP2112K-3.3 (EN -> VIN) -- +3V3 --+-- ESP32-C3-MINI-1-N4
         |                                     +-- 22uF + 100nF local at the module
         |
         +--[LK1 cuttable link / DNP S1A]-- LED_5V --+-- 470 uF + 22 uF
                                                     +-- 74AHCT1G125 Vcc  (OE_n -> GND)
                                                     +-- LD1..LD11 V_DD, 11 x 100 nF

   IO5 --+-[5k1]-GND  ->  AHCT in -> out -[47R]-> LD1.DIN -> ... -> LD11.DOUT -> TP7
   IO3 --+-[5k1]------->  SENSE (guarded, 195 mm) ==bridge== SENSE PAD  (tab)
         +-[4M7]-GND                              ==bridge== GND RETURN PAD (tab)
   IO2 -[5k1]-3V3   IO8 -[5k1]-3V3   IO9 -[5k1]-3V3 + tact SW to GND
   No reset button, by design.
```

Three things about this diagram are worth stating up front because they are the load-bearing choices:

**The 74AHCT1G125 is not optional.** SK6812 `V_IH = 0.7 × V_DD = 3.46 V` at a 4.94 V rail. An ESP32-C3 GPIO delivers 3.1–3.3 V. That is unconditionally out of spec and it is the intermittent field failure no firmware update can reach.

**The touch pad is a split pair, not a single pad.** SENSE and a GND return electrode sit side by side under the same overlay, so the finger's displacement current has a local return that does not depend on the power supply being earthed. This is a correction; see §7.5.

**The break-away tab is an internal routed slot in a plain rectangular outline.** The board profile is a 282 × 20 rectangle. The tab costs zero panel area and zero nesting effort, which is a real advantage over a profiled tab.

---

## 3. Governing constants

These numbers are referenced everywhere else in this document and in the firmware. They live here so there is exactly one place to change them. An earlier draft of this design carried the touch pull-down at three different values in three sections; that is how boards get built wrong.

| Constant | Value | Set by |
|---|---|---|
| Board outline | 282.0 × 20.0 × 1.6 mm | §7.1 |
| LED count / pitch | 11 / 16.66667 mm | §7.2 |
| LED row centreline | y = 11.000 mm | §7.2 |
| LED1 centre / LED11 centre | x = 64.000 / x = 230.667 mm | §7.2 |
| Lit zone | x 55.67 → 239.00 (183.33 mm) | §7.2 |
| Break slot centre | x = 250.000 mm | §7.6 |
| Touch pull-down `R_TPD` | **4.7 MΩ** (0402, land also accepts 10 MΩ) | §7.5 |
| Touch series `R_TS` | 5.1 kΩ | §7.5 |
| Touch overlay thickness | 1.0 mm nominal, 0.8–2.0 mm allowed | §7.5 |
| `MAX_CHANNEL_SUM` | 680 of 1020 | §5.4 |
| Unclamped worst-case input current | 1.24 A | §5.3 |
| Input path / copper sized for | 1.6 A | §5.5 |
| Panel | 6-up, 282 × 140 mm, routed slots + mouse bites | §7.8 |

---

## 4. Design decisions

| Decision | Why | What it cost |
|---|---|---|
| **ESP32-C3-MINI-1-N4**, not a Pico W carrier, not a bare RP2040 + RM2 | It collapses MCU, 4 MB flash, crystal, radio, RF layout, regulatory approval and USB-serial into one reflowed, JLC-placeable, pre-certified part. Every assembly-yield risk that sinks a bare-QFN layout and the supply risk that dents a Pico W carrier simply do not exist. Its one liability — `import rp2` dies — is bounded to one file, OTA-recoverable, and **retirable for $15 before a single PCB is ordered.** A risk you can pre-test is worth several dollars a unit under a first-batch gate | −$5.20/unit versus the Pico W. Costs a ~40-line rewrite of `sk6812.py`, plus a night on a dev board |
| **74AHCT1G125 level shifter on DIN** | `V_IH = 3.46 V` required, 3.3 V available. AHCT at 5 V has *TTL* thresholds: `V_IH(min) = 2.0 V` → +1.3 V input margin, `V_OH(min) = 4.4 V` at −8 mA → +0.94 V output margin. Both margins are rail-independent because the buffer and the LEDs share the same rail | **$0.11 + one 100 nF.** The cheapest insurance on the board. Rejected alternatives are priced in §6.5 |
| **AP2112K-3.3 LDO**, not AMS1117, not a buck | Dropout is the argument. Worst realistic case (5 V charger at −10 %, long cheap cable, full white) puts 4.13 V at the LDO input. AMS1117 needs ~0.8 V at 350 mA and brownouts. A buck saves 0.13 W and costs an inductor, two feedback resistors and a 1.5 MHz switching node 10 mm from a certified antenna | $0.06. Three BOM lines and 40 mm² cheaper than a buck |
| **LEDs run directly off the protected 5 V rail** | Putting 0.9 A through a regulator to gain nothing is a 1.5 W thermal problem | Free |
| **AO3401A P-FET, source on the INPUT side** | Reverse blocking and soft-start are mutually exclusive with one P-FET, and **inrush is the failure that ships**. Source-on-load lets the body diode charge 470 µF straight from VBUS the instant the connector mates — no soft-start at all, the source hiccups, and the user learns "it only turns on if I re-plug it". Reverse polarity is physically unreachable through USB-C | $0.04. Reverse protection for the DNP aux pads is restored by a DNP series Schottky the bench user must fit anyway |
| **11 LEDs, 16.66667 mm pitch** | 11 is the only count that hits both the 167 mm length and the 60 LED/m pitch. 10 LEDs spans 150 mm; forcing 167 mm across 10 gives an 18.56 mm pitch that no longer matches a strip | +1 LED placement (~$0.08) and +$0.02 of bypass cap |
| **Break-away tab as an internal routed slot** | V-score cannot make an interior or partial cut — the blade must traverse the whole panel edge to edge. This is geometry, not preference. An internal slot also keeps the outline a plain rectangle, so the tab costs zero panel area | Zero. Internal slots are part of the profiling operation and carry no surcharge |
| **Plain plated through-hole pads at the break, no connector** | Castellated half-holes at a break line are not manufacturable (the plating tears when you snap it). A JST-PH adds a connector, a housing, a crimp op and ~$0.35 to *every* unit to serve a minority configuration. The drills are already in the drill file | Zero. In the default configuration they are unused copper that doubles as the SENSE/GND test points |
| **Split SENSE/GND touch pad** | The usual single-pad self-capacitance sensor assumes the finger's return is mains earth. This lamp ships with a 2-prong Class II adapter and floats. A local GND return electrode under the same fingertip makes ΔC independent of what the board's ground is referenced to | Zero — it reuses guard-ring copper and an existing net. It halves the peak ΔC and removes a 57–80 % supply-dependent loss, which is a good trade |
| **Routed slots + mouse bites between boards in the panel, not V-score** | The module's antenna must sit near a board edge, and a V-score blade cutting 1/3 depth from each face with ±0.15 mm positional tolerance has no clearance to a module can set back under ~1 mm. Routed separation removes the blade entirely | ~$0.05/board of routing time. It also returns the 0.5 mm V-score copper setback to the touch guard rail |
| **Single-sided assembly, 2 layers, 1.6 mm, HASL** | A pre-certified module means there is no antenna to lay out, so 2 layers is sufficient. Everything fits on the LED face. 1.6 mm is standard, free, and load-bearing for stiffness over 282 mm | Saves ~$0.55/board of second-side setup and the $8.18 second setup fee |
| **No reset button** | Verified against the code, correcting a claim that gets repeated: `boot.py:84-85` increments `bootfail.txt` on any non-`PWRON_RESET` boot, **but `main.py:139-166 mark_stable()` writes it back to "0" after 60 s of running.** One reset press is harmless. The real hazard is narrow — three resets inside 60 s each, i.e. an impatient user — but it is real, and recovery by unplug/replug is what `boot.py` actually wants | −$0.04 and one BOM line. TP10 on `EN` replaces it |
| **PPTC 2 A hold / 4 A trip, not 1.5 A** | Hold current derates ~25 % at 50 °C, so a 1.5 A part holds ~1.15 A against a 1.24 A unclamped worst case — a nuisance trip, not protection | $0.06. Kept because it protects the *user's charger or laptop port*, not the board |

---

## 5. Power budget — computed for eleven LEDs

Every figure here is recomputed for 11. None is a ten-LED number reused.

### 5.1 Per LED and per string

The four channels are **not** interleaved inside the SK6812 die — all four sink simultaneously, so currents add. Do not budget on an average.

| | per LED | × 11 |
|---|---|---|
| Absolute worst (4 ch × 20 mA + 1 mA IC) | 81 mA | **891 mA** (4.46 W) |
| Typical real parts, full white (4 × 16 + 1) | 65 mA | 715 mA |
| At `LED_BRIGHTNESS = 0.6`, full white | 49 mA | 539 mA |
| **With the firmware clamp at 0.667** | 54.5 mA | **598 mA** |
| App default `BASE_WARM_WHITE (0,0,0,200)` @ 0.6 | 10.4 mA | **114 mA** |
| All off (IC quiescent) | 1 mA | 11 mA |

### 5.2 MCU rail

| | mA @ 3.3 V |
|---|---|
| C3 @ 160 MHz running MicroPython, modem-sleep, associated | 30–45 |
| Wi-Fi RX active | ~85 |
| **Wi-Fi TX burst, 802.11b @ 20 dBm, ≤ 2 ms** | **~350** |
| Design continuous | **100** |
| Design peak | **350** |

The 350 mA TX burst is *higher* than the CYW43439's ~290 mA. That is a real, if small, cost of the C3 decision, and it is why the LDO choice is a dropout argument rather than a price argument.

### 5.3 Totals at the 5 V input

| Scenario | LEDs | MCU | Total | Power |
|---|---|---|---|---|
| Idle, LEDs off, TX burst | 11 mA | 350 mA | 361 mA | 1.8 W |
| Normal use (warm white @ 0.6, Wi-Fi idle) | 114 mA | 60 mA | **174 mA** | 0.87 W |
| Clamped worst case | 598 mA | 350 mA | **948 mA** | 4.7 W |
| **Unclamped worst case** (100 % RGBW @ brightness 1.0) | 891 mA | 350 mA | **1.24 A** | **6.2 W** |

**Design rule: size the input path, fuse and copper for 1.6 A** — the unclamped case with 30 % headroom, so that removing the clamp in a future OTA cannot damage hardware. `colour.py:239` clamps brightness to [0,1] and MQTT can command 1.0 with full RGBW at any moment.

### 5.4 The clamp, and why it exists

`MAX_CHANNEL_SUM = 680` caps the per-LED sum of R+G+B+W after brightness and **independently of** `LED_BRIGHTNESS`, so a user setting brightness 1.0 over MQTT cannot exceed it.

It is doing double duty. Electrical input per LED at the clamp is 5 V × 54.5 mA = 0.27 W, of which ~30 % leaves as light → **0.19 W of heat per LED, 2.1 W for the string.**

| Source | Clamped | Unclamped full white |
|---|---|---|
| LED string (heat) | 2.1 W | 3.1 W |
| LDO ((5−3.3) × 0.10) | 0.17 W | 0.17 W |
| P-FET | 0.05 W | 0.09 W |
| PPTC | 0.05 W | 0.08 W |
| **Board total** | **2.37 W** | **3.44 W** |

With generous pour on both layers, ≥60 mm² per LED per layer and ≥4 thermal vias per LED, θ_JA is about **140 °C/W** (versus 250–350 °C/W with pad-sized copper only):

- Clamped, in a 39 °C enclosure interior: ΔT_j = 0.27 × 140 = 38 °C → **T_j ≈ 77 °C.** Under the 85 °C comfort line.
- Unclamped sustained full white, 45 °C interior: ΔT_j = 57 °C → **T_j ≈ 102 °C.** Phosphor lumen-maintenance and colour-point degradation territory.

The clamp lives in the LED driver's write path, which *is* OTA-able, so the value can be revised after the first thermal measurement. **The hardware is sized for the unclamped case regardless.**

**Enclosure requirement, and it is a hard one: ≥180 cm² of external surface with at least passive venting.** A 30 mm OD × 220 mm tube gives 210 cm² and qualifies (ΔT ≈ 14 °C clamped, ≈ 20 °C unclamped). A small sealed diffuser at 100 cm² would double the interior rise and push T_j past 110 °C even clamped.

### 5.5 Copper and IR drop

IPC-2221 external, ΔT = 10 °C, k = 0.048, 1 oz:

```
dT^0.44 = 2.754 ;  k*dT^0.44 = 0.1322
I = 1.6 A -> (1.6/0.1322)^1.379 = 12.10^1.379 = 31.1 mil^2
width = 31.1 / 1.378 = 22.6 mil = 0.57 mm minimum
```

**Specified: 7.8 mm 5 V pour and 3.4 mm GND pour along the row** — 6–14× the minimum, free, and doubling as the LED heatsink.

**IR drop to LED11**, which is the 167 mm question everyone asks. Sheet resistance 1 oz = 0.494 mΩ/sq. Bulk cap to LED11 ≈ 200 mm. With a 7.8 mm pour: 200/7.8 = 25.6 squares → 12.7 mΩ per rail, 25.4 mΩ out and back. The load is distributed (LED1 carries eleven LEDs' current, LED11 carries one), so end-of-line drop is `I_total × R / 2`:

```
0.891 A x 0.0254 ohm / 2 = 11 mV
```

**LED11 sees 4.93 V.** Even a bare 1 mm trace would give 88 mV. The 167 mm length is a complete non-issue for IR drop — no injection points, no second feed.

### 5.6 Bulk capacitance

Largest realistic load step is off → full white, 0 → 0.891 A, against an upstream source loop response of ~200 µs:

```
dV = I*dt/C = 0.891 x 200us / 470uF = 0.379 V  -> rail dips to 4.56 V
```

Harmless: SK6812 tolerates 4.5–5.5 V and the LDO still has over a volt of headroom. Scaling from ten LEDs to eleven moves the droop from 0.345 V to 0.379 V — **no part change**, which is worth stating so nobody re-derives it.

**Not 1000 µF.** That figure is folklore for 30–60 LED strips on flying leads; here it would make the inrush problem twice as bad for no benefit.

Paralleled with **22 µF 0805 X5R** for high-frequency ESR — at 5 V DC bias an X5R 22 µF derates to about 11 µF effective, which is exactly what the LED rail wants. This is why a separate 10 µF line was deleted.

**11 × 100 nF 0402 X7R, one per SK6812 V_DD pin, with a via straight to the plane.** Non-negotiable. Each SK6812 switches four constant-current sinks at its internal PWM rate, and an unbypassed neighbour's di/dt is the *actual* cause of "random flicker" that gets endlessly misdiagnosed as a data-timing problem.

### 5.7 Inrush soft-start arithmetic

```
tau = R_G * C_G = 100k * 100nF = 10 ms
I_inrush ~= C_bulk * V_in / tau = 470uF x 5 V / 10 ms = 235 mA   (under the USB 500 mA default)
Conduction loss at 0.95 A = 0.95^2 x 0.060 = 54 mW, drop 57 mV
V_GS steady state = -5 V, well inside the +/-12 V rating. No gate Zener.
```

**Be honest about this figure: 235 mA is an estimate, not a guarantee.** The gate ramp is exponential in V_GS while I_D is quadratic in (V_GS − V_th), so the real peak is realistically 200–400 mA and depends on the AO3401A transfer characteristic. **Stage 1 must scope VBUS and drain current over at least 20 hot-plug cycles.** Two drop-in fixes if it comes in too high, neither needing a respin:

1. `C_G` → 470 nF (τ = 47 ms, inrush ≈ 50 mA). One BOM value change.
2. Fit `C21`, a DNP 100 nF from GATE to DRAIN — a Miller cap gives *deterministic* dV/dt: 35 µA / 100 nF = 350 V/s → 165 mA. The footprint is laid down for free.

Uncontrolled, charging 470 µF through 0.2 Ω of cable is a theoretical 25 A peak. In practice the source hiccups and you get "the lamp doesn't turn on unless I unplug and re-plug it" — a support burden worth far more than $0.03.

---

## 6. Schematic, block by block

Designators, then the netlist per block. Verified against `config.py`, `main.py`, `colour.py`, `sk6812.py`, `touch.py`, `boot.py` and `hardware_test.py` in this repo.

### 6.0 Designator index

| Ref | Part | Package | Qty |
|---|---|---|---|
| U1 | ESP32-C3-MINI-1-N4 | module, 53-pad | 1 |
| U2 | SN74AHCT1G125DBVR | SOT-23-5 | 1 |
| U3 | AP2112K-3.3TRG1 | SOT-23-5 | 1 |
| U4 | USBLC6-2SC6 | SOT-23-6 | 1 |
| Q1 | AO3401A | SOT-23 | 1 |
| LD1–LD11 | SK6812-class RGBW (GRBW) | 5050-4P | 11 |
| F1 | PPTC 2.0 A hold / 4.0 A trip | 1812 | 1 |
| SW1 | Tact switch, SMD | 3×4 mm | 1 |
| J1 | USB-C 2.0 receptacle, 16-pin, THT shield tabs | — | 1 |
| C1 | 470 µF / 10 V alu SMD | 8 × 10.2 mm | 1 |
| C2–C5 | 22 µF / 10 V X5R | 0805 | 4 |
| C6–C20 | 100 nF / 16 V X7R | 0402 | 15 |
| R1–R7 | 5.1 kΩ ±1 % | 0402 | 7 |
| R8, R9 | 100 kΩ ±1 % | 0402 | 2 |
| R10 | 4.7 MΩ ±5 % | 0402 | 1 |
| R11 | 47 Ω ±1 % | 0402 | 1 |
| DNP | D1 (S1A, SMA), D2 (low-leakage ESD, 0402), D3 (1N5819HW, SOD-123), C21 (0402), J2/J3/J4 (THT pads), LK1 (cuttable copper link) | — | 0 |
| Free | TP1–TP11 exposed pads, H1/H2 mounting holes, PAD_S / PAD_G touch copper | — | 0 |

**50 placements. 16 unique BOM lines. ~204 solder joints. Zero THT placements, zero hand-solder operations.**

### 6.1 Net list

| Net | Members |
|---|---|
| `VBUS_RAW` | J1.A4, J1.B4, J1.A9, J1.B9, U4.5, F1.1 |
| `VBUS_F` | F1.2, Q1.2(S), C7.2, D3.K(DNP), TP11 |
| `+5V` | Q1.3(D), C2.1, U3.1, U3.3(EN), LK1.1, C21.2(DNP) |
| `LED_5V` | LK1.2, D1.K(DNP), C1.+, C5.1, U2.5, C6.1, LD1.1 … LD11.1, C10.1 … C20.1, TP1 |
| `+3V3` | U3.5, C3.1, C4.1, C9.1, U1.3V3, R4.1, R5.1, R6.1, R9.1, TP2 |
| `GND` | everything below, both pours, U1 thermal pad |
| `GATE` | Q1.1(G), R8.1, C7.1, C21.1(DNP) |
| `EN` | U1.EN, R9.2, C8.1, TP10 |
| `CC1` / `CC2` | J1.A5 + R1.1 / J1.B5 + R2.1 |
| `USB_DP_CONN` / `USB_DM_CONN` | J1.A6 + J1.B6 + U4.3 / J1.A7 + J1.B7 + U4.1 |
| `USB_DP` / `USB_DM` | U4.4 + U1.IO19 / U4.6 + U1.IO18 |
| `LED_DATA_3V3` | U1.IO5, R3.1, U2.2(A) |
| `LED_DATA_5V` | U2.4(Y), R11.1 |
| `LED_DIN1` | R11.2, LD1.4(DIN), TP5 |
| `D_n_n+1` | LDn.2(DOUT) → LDn+1.4(DIN), n = 1…10 |
| `LD11_DOUT` | LD11.2, TP7 |
| `TOUCH_GPIO` | U1.IO3, R10.1, R7.1, D2.A(DNP) |
| `TOUCH_SENSE` | R7.2, J2.1, TP6, → centre bridge → J3.1, `PAD_S` |
| `BOOT_N` | U1.IO9, R6.2, SW1.1, SW1.2 |
| `STRAP2` / `STRAP8` | U1.IO2 + R4.2 / U1.IO8 + R5.2 |
| `UART_TX` / `UART_RX` | U1.IO21 + TP8 / U1.IO20 + TP9 |

`TOUCH_SENSE` is one continuous net in the attached (default) configuration; J2 and J3 are unpopulated pads either side of the break, in parallel with the copper crossing the centre bridge.

### 6.2 Block A — USB-C input

```
J1.A4/B4/A9/B9  VBUS -> VBUS_RAW
J1.A1/B1/A12/B12 GND -> GND        J1.SH1..SH4 -> GND (direct, no 1M||4n7 network)
J1.A5 CC1 -> CC1                   R1  5.1k  CC1 -> GND
J1.B5 CC2 -> CC2                   R2  5.1k  CC2 -> GND
J1.A6 + J1.B6 -> USB_DP_CONN       (tie under the connector body)
J1.A7 + J1.B7 -> USB_DM_CONN
U4  USBLC6-2SC6:  1 -> USB_DM_CONN, 6 -> USB_DM, 3 -> USB_DP_CONN, 4 -> USB_DP,
                  2 -> GND, 5 -> VBUS_RAW
F1  PPTC 2A/4A:   VBUS_RAW -> VBUS_F
```

**Two separate 5.1 kΩ Rd resistors, one per CC pin.** A single resistor bridging CC1 to CC2 is the single most common USB-C sink error and produces a port that is dead in one cable orientation.

**A6/B6 and A7/B7 must be shorted on the PCB.** The 16-pin part brings D+ and D− out once per orientation. Short them under the connector body with a short trace, not by routing both pairs separately to the ESD array.

**Shield tied directly to GND.** The product is a floating, adapter-powered object with one connector and no second ground reference, so there is no ground loop to break. A direct tie is what gives the shield an ESD path, and it costs zero parts.

**No 27 Ω series resistors on D±.** The ESP32-C3 USB Serial/JTAG reference design connects D+/D− directly; the on-die drivers are already source-terminated.

**Do not delete USB data.** It is the only recovery path when an OTA bricks a unit, and unlike a Pico W carrier there is no second connector to fall back on. Route as a 90 Ω differential pair, matched within 5 mm, over unbroken ground, no vias, no stubs.

**The USBLC6's VBUS pin is an ESD clamp, not a power TVS.** It will not survive a sustained overvoltage. That is the correct level of protection for a 5 V USB sink that never negotiates PD, but do not describe the board as overvoltage-protected. Reverse polarity is a separate matter, handled in §6.3.

**No barrel jack.** It adds a connector, reverse-polarity exposure, and an ORing problem (two Schottkys wasting 0.35 W, or a P-FET mux). J4 — a DNP 2-pin 2.54 mm footprint downstream of F1 with a DNP series Schottky D3 — lets a bench user inject 5 V without a respin, for zero cost, and D3 having no bypass link is deliberate: the aux path is unusable unless the user fits the diode, which is what restores reverse-polarity protection. **The README must say: use USB-C or J4, never both.** They hard-parallel.

### 6.3 Block B — inrush soft-start

```
Q1  AO3401A   (SOT-23: 1 = G, 2 = S, 3 = D)
Q1.2 (S) -> VBUS_F        SOURCE ON THE INPUT SIDE
Q1.3 (D) -> +5V           drain to load
Q1.1 (G) -> GATE
R8  100k    GATE -> GND
C7  100nF   GATE -> VBUS_F     i.e. GATE-TO-SOURCE, not gate-to-GND
C21 DNP 100nF  GATE -> +5V     Miller cap, deterministic dV/dt if needed
```

Two things here are the most commonly copied schematic errors in this circuit, so they are called out explicitly:

**The capacitor goes gate-to-SOURCE.** If it goes gate-to-GND, at power-up the gate sits at 0 V while the source rises to 5 V, V_GS is −5 V immediately, the FET turns fully on, and there is **no soft-start whatsoever.**

**The source is on the INPUT side.** A P-channel body diode has its anode at the drain and cathode at the source. Source-on-load makes the body diode conduct straight from VBUS into 470 µF the instant the connector mates, and the gate RC then only decides when the channel enhances and drops the 0.5 V diode to 50 mV. You get the full uncontrolled inrush the part was added to prevent. Source-on-input reverse-biases the body diode for load current, so the FET must actively enhance and the gate RC genuinely controls turn-on.

The trade is that reverse polarity is not blocked. That is acceptable because reverse polarity is **physically unreachable** on the shipped board — USB-C cannot present reversed VBUS, and the only exposure is J4, a DNP footprint a bench user must deliberately populate and then mis-wire, which D3 covers. Inrush, by contrast, happens on every unit on every plug-in.

If you want both in the populated path, the cheapest correct answer is two AO3401A back-to-back, common-drain, gates tied — same part number so no new BOM line, +$0.03, +1 placement, +60 mΩ. I do not recommend it: it spends money and dropout headroom protecting a footprint that is empty by default.

**Turn-off behaviour matters too.** On unplug, C1 discharges into the load; with LEDs off and the MCU drawing ~45 mA from 5 V, 470 µF falls below the LDO dropout in about 35 ms. A clean, fast rail collapse is what makes unplug/replug the documented recovery, because `boot.py:84` distinguishes `PWRON_RESET` from a crash. No bleed resistor needed.

### 6.4 Block C — 3.3 V regulation

```
U3  AP2112K-3.3TRG1  (SOT-23-5)
U3.1  VIN   -> +5V
U3.2  GND   -> GND
U3.3  EN    -> +5V        <-- TIED TO VIN. NOT to the LDO's own output.
U3.4  NC    -> no connect
U3.5  VOUT  -> +3V3
C2  22uF 0805   +5V  -> GND   (input,  <=3 mm from U3.1)
C3  22uF 0805   +3V3 -> GND   (output, <=3 mm from U3.5)
```

**EN goes to VIN, not to VOUT.** This is worth a paragraph because bootstrapping EN to the LDO's own output is a plausible-looking mistake that produces a 100 %-correlated dead batch: at power-up VOUT is 0 V, so EN is 0 V, so the regulator stays disabled, so VOUT never rises. There is no mechanism to break the latch. AP2112K, ME6211, RT9013 and SGM2212 all specify EN as a high-impedance logic input with **no internal pull-up to VIN** — their datasheets give EN→VIN as the always-on connection. If you want the option of gating the rail later, lay a DNP 0 Ω from EN to a control net; the copper default stays EN→VIN.

**Dropout budget, honestly.** Worst realistic case — 5 V charger at −10 %, long cheap cable, LEDs at full white:

```
4.50 V source
-0.24 V  cable + connector, 0.2 ohm @ 1.2 A
-0.06 V  F1 PPTC, 0.05 ohm
-0.07 V  Q1, 60 mohm
= 4.13 V at U3.1
minus the 0.379 V transient droop from a simultaneous LED turn-on (worst instant): 3.75 V
```

Against that, use the datasheet **maximum** dropout over temperature, not typical. AP2112K is specified at ~400 mV max at 600 mA, so at 350 mA it is comfortably under 300 mV → ≥3.45 V out, and the ESP32-C3's brownout detector sits far below that. ME6211's typical 250 mV at 350 mA looks better on paper but its max-over-temperature figure is thinner, and AMS1117 needs ~0.8 V and brownouts outright — and it is **SOT-223, so it is not a drop-in fallback.** Pin-compatible SOT-23-5 alternates that *are* drop-ins: ME6211C33M5G, RT9013-33GB, SGM2212-3.3. Avoid XC6206P332MR (200 mA — too small for the 350 mA TX burst).

Add "scope 3V3 at TP2 during a Wi-Fi TX burst with the string at full white, from a 4.5 V source through a 2 m cheap cable" to Stage 1. That single measurement settles the whole argument.

**Dissipation:** (5.0 − 3.3) × 0.10 A = 0.17 W continuous. SOT-23-5 with ~100 mm² of pour on the GND pin, θ_JA ≈ 180 °C/W → ΔT ≈ 31 °C, junction ~70 °C in a 39 °C interior. The 350 mA burst adds 0.6 W for 2 ms against a package time constant of seconds — thermally invisible.

### 6.5 Block D — MCU module

```
U1  ESP32-C3-MINI-1-N4
3V3   -> +3V3        GND -> GND (ALL GND pins, including the thermal pad)
EN    -> EN          R9  100k  EN -> +3V3      C8  100nF  EN -> GND
IO5   -> LED_DATA_3V3      <-- LED_PIN = 5, unchanged from config.py:36
IO3   -> TOUCH_GPIO        <-- TOUCH_PINS = [3]
IO2   -> STRAP2   R4 5.1k -> +3V3     (mandatory: IO2 low at reset = invalid, no boot)
IO8   -> STRAP8   R5 5.1k -> +3V3     (required for download boot)
IO9   -> BOOT_N   R6 5.1k -> +3V3, SW1 to GND
IO18  -> USB_DM        IO19 -> USB_DP        (fixed by silicon)
IO20  -> UART_RX (TP9) IO21 -> UART_TX (TP8)
C4  22uF 0805  +3V3 -> GND   <= 5 mm from the module's 3V3 pin
C9  100nF 0402 +3V3 -> GND   <= 2 mm from the module's 3V3 pin
```

**Pin choices, and why each one:**

| Signal | Pin | Reason |
|---|---|---|
| LED DIN | **IO5** | Deliberately identical to `config.py:36`. `config.py` is never OTA'd (`boot.py:5`) and `hardware_test.py:65` hard-codes `LED_PIN = 5`. Keeping GPIO5 means one golden `config.py` flashes to all 100 units. IO5 is a plain GPIO on the C3 — not strapping, not flash, high-Z at reset |
| Touch sense | **IO3** | GPIO12–17 on the C3 are bonded to the internal SPI flash and are not available on MINI-1, so the current `[12]` cannot survive. IO3 is a plain non-strapping GPIO. It does **not** need to be ADC-capable — the `config.py:47` comment claiming "raw ADC" is false; `touch.py:50-66` is pure digital GPIO timing |
| BOOT / straps / USB / UART0 | IO9 / IO2, IO8 / IO18, IO19 / IO20, IO21 | Fixed by silicon |

**C4 is a fourth 22 µF beyond the two the LDO needs, and it earns its $0.02.** A 350 mA, ≤2 ms 802.11b TX burst into an LDO 10 mm away is the single most common cause of "the module resets whenever it transmits". C4 supplies the burst locally; C3 refills C4. Same BOM line, one extra placement, no setup cost.

**R9 = 100 kΩ on EN is coupled to Q1's soft-start and must not be consolidated into the 5.1 kΩ line.** τ_EN = 10 ms against a rail that itself ramps over 10–15 ms means EN lags the rail throughout and crosses ~2.48 V about 30–35 ms after mate, comfortably after the rail is flat. With 5.1 kΩ (τ = 0.5 ms) EN tracks the ramping rail closely and can release the chip while VDD is still ~2 V, producing a brownout-reset loop on plug-in. 100 kΩ is already on the BOM for R8, so it costs nothing. If Stage 1 shows spurious resets, swap to 10 kΩ — one BOM line, not a respin.

**Antenna keep-out is a schematic-level instruction, not a layout detail.** No copper on any layer inside the datasheet keep-out; nothing — pours, traces, the 470 µF body, a metal screw or heat-set insert — within 8 mm of the antenna region. Violating this forfeits the modular approval, which is the entire reason the module was chosen. It is also why 2 layers is sufficient: you are not laying out an antenna.

> **Uncertainty, stated rather than papered over.** Connections above are by **pin name**, which is what the KiCad symbol carries. I do not have the ESP32-C3-MINI-1 numeric pad map to the standard required for a first-article board and will not invent it. Before layout, cross-check every name against Table 3 "Pin Definitions" in the datasheet and use Espressif's official symbol/footprint. Also verify the strapping table and confirm nothing inside the module already pulls IO2 or IO8 — if it does, delete R4 and/or R5. This is the one place the resistor consolidation could produce dead boards rather than saved pennies.

### 6.6 Block E — level shift and the LED chain

```
U2  SN74AHCT1G125DBVR (SOT-23-5)
U2.1 OE_n -> GND       ACTIVE LOW. Tie to GND to enable the output.
U2.2 A    -> LED_DATA_3V3
U2.3 GND  -> GND
U2.4 Y    -> LED_DATA_5V
U2.5 VCC  -> LED_5V    <-- downstream of LK1/D1, same rail as the LEDs
C6  100nF  LED_5V -> GND      <= 2 mm from U2.5
R3  5.1k   LED_DATA_3V3 -> GND      <= 5 mm from U2.2
R11 47R    LED_DATA_5V -> LED_DIN1  <= 5 mm from U2.4

for n = 1..11:
   LDn.1 (VDD) -> LED_5V ;  LDn.3 (VSS) -> GND ;  100nF directly at LDn.1
LD1.4 (DIN) <- LED_DIN1 ;  LDn.2 (DOUT) -> LDn+1.4 (DIN) ;  LD11.2 -> TP7 only
```

**U2's VCC is on `LED_5V`, downstream of the hedge link — not on `+5V`.** In the normal configuration the two nets are the same node through a 2.5 mΩ copper link, so nothing changes. In the hedge configuration (link cut, series diode fitted) powering the buffer from `+5V` would drive DIN to ~4.85 V into an LED whose own V_DD is 4.2 V, forward-biasing LD1's input protection diode into its rail for the whole 422 µs frame, sixty times a second. R11 limits it to a few mA, which is enough for continuous substrate injection and, on a bad lot, latch-up. On `LED_5V` the buffer runs at the same 4.2 V as the LEDs: V_OH ≈ 4.1 V against V_IH = 0.7 × 4.2 = 2.94 V, still +1.16 V of margin and no overdrive.

**R3 is the floating-input pull-down, and it is the cheapest reliability part on the board.** Before MicroPython runs — through the C3's boot ROM, the MicroPython init, and `main.py`'s import chain — IO5 is a high-Z input. An AHCT input left floating near mid-rail self-oscillates, draws crowbar current through both output transistors, and can clock a garbage frame into the string, producing a flash of random colour at every power-up and every one of the frequent reboots (daily at `main.py:431`, offline at `main.py:667-674`, crash at `main.py:876-894`). $0.001 from an existing value.

**R11 = 47 Ω, not 330–470 Ω.** Two different jobs get conflated in the usual advice. The 330–470 Ω folklore value exists for strips on flying leads; here the U2→LD1 run is ~12 mm and never leaves the PCB, and 470 Ω into LD1's ~15 pF plus ~10 pF of trace would add 12 ns of RC for nothing. The real job is damping: AHCT output impedance is 15–25 Ω into a microstrip that on 1.6 mm FR4 at 0.30 mm width is nearer 120 Ω than the 70–90 Ω usually assumed. At a ~3 ns edge rate the critical length is ~75 mm and this trace is 12 mm, so it is **electrically short and termination is not actually required** — the exact value does not matter. Keep 47 Ω anyway: it costs nothing, it damps whatever the trace does do, and it limits U2's output current into LD1's input ESD diode if 3V3 comes up while the 5 V rail is still on its 10 ms ramp.

**Inter-LED DOUT→DIN hops get no series resistor.** Each SK6812 fully regenerates from its own shift register; a resistor there only degrades the edge.

**Part substitution is the number one way to get this circuit wrong.** Mark the BOM line "AHCT/HCT ONLY — DO NOT SUBSTITUTE" and disable auto-substitution at the assembler.

| Part | Verdict |
|---|---|
| `SN74AHCT1G125DBVR` (LCSC C7484), `74HCT1G125GW` | Correct. Pin-identical, TTL thresholds |
| `SN74AHC1G125DBVR` (LCSC **C7468**) | **Wrong.** AHC at 5 V has V_IH = 3.5 V and fixes nothing. One letter, and the whole design. The LCSC codes differ by two digits |
| `74LVC1G125` at 3.3 V | **Wrong.** Outputs 3.3 V and fixes nothing |
| `SN74LVC1T45DBVR` | **Not pin-compatible** — SOT-23-6. Do not plan on it as a drop-in |
| `74AHCT1G126` | Works, but **OE is active HIGH — tie pin 1 to VCC, not GND** |

**Rejected alternatives to the buffer, with the numbers:**

- *Schottky in the LED V_DD path:* V_F collapses to 0.25 V at the 0.1 A normal operating current → rail 4.7 V → V_IH 3.29 V. The fix evaporates precisely where the lamp lives 99 % of its life. Reject.
- *Silicon diode:* works (rail 4.15–4.35 V), but burns 0.75 W at 0.9 A in one package, costs ~15 % brightness, and shifts the white point of a *lamp* — the W die dims disproportionately. DNP hedge only.
- *Dedicated 4.3 V LED buck:* more parts, more area, a switcher next to a certified antenna, for more money than a $0.11 buffer. Reject.
- *First LED as a sacrificial buffer:* LED1's input still sees the same out-of-spec 3.3 V, and if it mis-latches it corrupts the whole downstream chain. You buy twelve unreliable LEDs instead of eleven. Reject.

**The hedge, kept for $0.00.** `LK1` is a cuttable copper link — a 0.4 mm-wide, 2.0 mm-long neck between `+5V` and `LED_5V` with the soldermask opened and a silkscreen `CUT -> D1` scissors mark — bridging a DNP **SMA (DO-214AC)** land pattern. If the AHCT part ever has to be omitted, cut the link and hand-fit an **S1A**. Zero placements, zero BOM lines, ~15 mm² of head area.

> Do **not** use 1N4148W for this. It is a 300 mA part and the string draws 0.89 A; it would fail short (the level-shift fix silently disappears) or open (dead lamp). And a Schottky is wrong for the same reason it is wrong as a primary fix. The land pattern is SMA, not SOD-123. Caveat for whoever ever uses it: an S1A at 0.89 A drops ~1.0 V and dissipates 0.9 W, brightness is down ~15 %, the white point shifts, and the package gets hot. It is an emergency hedge, not an alternative design.

The 0.4 mm link neck carries 0.89 A over 2.5 mm — 5 squares × 0.494 mΩ = 2.5 mΩ, 2.2 mV, 2 mW, with an ~8 °C rise. It must be 0.4 mm, not the full bridge width, so a scalpel can cut it in two or three passes.

**LD11's DOUT goes to a test pad and nowhere else.** If TP7 toggles during a frame, all eleven shift registers latched and passed data — the whole chain verified with one scope probe.

**Data flows LD1 → LD11, head end → tab end.** Firmware index 0 is the first LED to receive data, so `REVERSE_LEDS = False` is correct and becomes permanently correct. It must still **exist as a symbol** in `config.py` — see §8.1.

> **Verify before layout:** SK6812 5050 pad assignment (I have it as 1 = VDD, 2 = DOUT, 3 = VSS, 4 = DIN) against the exact LCSC part's drawing. The 4-pad 5050 footprint is shared with WS2812B but pad-1 orientation and internal pin order have varied between clone lots, and a rotated LED row is a scrap panel.

### 6.7 Block F — touch front end

```
R10 4.7M   TOUCH_GPIO -> GND         at U1, <= 5 mm from IO3
R7  5.1k   TOUCH_GPIO -> TOUCH_SENSE at U1, <= 5 mm from IO3
D2  DNP 0402  TOUCH_GPIO -> GND      low-leakage ESD, empty by default
PAD_S  SENSE electrode, tab, under soldermask
PAD_G  GND return electrode, tab, alongside PAD_S under the same overlay
```

The circuit is small; the reasoning is in §7.5, where the geometry lives. Three schematic-level points:

**R10 sits on the GPIO side of R7, not the sense side.** Same measurement (R7 at 5.1 kΩ is three orders of magnitude below R10, so the two nodes track within ~180 ns of each other against a ~170 µs measurement), but if the sense trace is ever cut or opens, the GPIO still has a defined discharge path, and it puts R7 between the pad and everything fragile, which is the correct R-then-clamp ESD ordering.

**Both resistors live on the MAIN board, never on the tab.** This is a fail-safe, not a convenience. If R10 were on the tab, a builder who snaps it off and does not immediately rewire leaves IO3 floating, and `touch.py` then runs its wait to the safety cap on every main-loop iteration — turning a sub-millisecond measurement into tens of milliseconds inside a 16 ms frame, producing visible stutter and watchdog pressure. With R10 on the main board, an unwired snapped board reads a short stable discharge and simply never triggers. Fails silent, costs nothing.

**D2 stays empty, and if you ever populate it, the usual advice is not sufficient.** The pad is under soldermask *and* behind ≥0.8 mm of plastic, so there is no galvanic path and ESD arrives as heavily attenuated capacitive coupling that R7 and the C3's internal clamps handle. If field failures ever appear, note that on a 4.7 MΩ node the discharge current at 3.3 V is only 700 nA — a general ESD diode with 100 nA–1 µA of reverse leakage is the same order as the signal current and will distort or defeat the measurement. **Specify I_R ≤ 10 nA at 3.3 V in addition to C_j ≤ 1 pF, and re-baseline afterwards.** The commonly cited ESD9B5.0ST5G meets the capacitance spec but its leakage is not tight enough to assume.

### 6.8 Test points — eleven exposed 1.0 mm pads, zero cost

| TP | Net | Purpose |
|---|---|---|
| TP1 | `LED_5V` | rail voltage, droop under load |
| TP2 | `+3V3` | LDO output, dropout margin under Wi-Fi TX |
| TP3 / TP4 | `GND` | head reference / tab-end reference |
| TP5 | `LED_DIN1` | post-buffer data — verify the 5 V swing and bit timing **here**, not at IO5 |
| TP6 | `TOUCH_SENSE` | scope the discharge waveform directly, attached or pigtailed |
| TP7 | `LD11_DOUT` | whole-chain continuity |
| TP8 / TP9 | `UART_TX` / `UART_RX` | ROM bootloader console at 115200 — the fallback when USB enumeration fails |
| TP10 | `EN` | reset stimulus; replaces the deleted button |
| TP11 | `VBUS_F` | current probe for the Stage 1 inrush measurement |

J2 doubles as a SENSE + GND probe point at the far end.

---

## 7. Layout and mechanical

### 7.0 Board drawing

![EM-15 rev B, drawn to scale](fl11-board.svg)

Top view, to scale. LED centres, pitch, pad extents, break slot, mounting holes and the copper
bands are the specified values from the sections below. Head-section parts are indicative — this
design fixes their nets and clearances, not their exact x/y, which falls out of routing.

### 7.1 Outline and cross-section

**282.0 × 20.0 × 1.6 mm, 2 layer, 1 oz, single-sided SMT, white mask, black silkscreen.**

The board was narrowed from 24.0 mm to 20.0 mm. The reason is not cost, though it saves ~$0.15/board of area: a 24 mm board sitting 5 mm below the axis of a 26 mm bore consumes exactly 24.000 mm of available chord, leaving **zero** for the printed spine that has to capture both long edges. See §7.3 for the inequality that must hold.

Cross-section through the lit zone, y measured from the y = 0 long edge:

| y (mm) | Top layer | Bottom layer |
|---|---|---|
| 0.40 – 8.20 | **5 V pour**, 7.8 mm → LED anodes | solid GND |
| 8.50 – 13.50 | LED bodies (5050), centre y = 11.00 | solid GND, ≥4 thermal vias per LED |
| 13.60 – 17.00 | **GND pour**, 3.4 mm; 11 × 100 nF; DOUT→DIN chain | solid GND |
| 17.30 – 19.30 | guard 0.5 ‖ gap 0.35 ‖ **SENSE 0.30** ‖ gap 0.35 ‖ guard 0.5 | solid GND (the shield) |
| — | 0.40 mm copper setback at both long edges | same |

Putting SENSE on the far side of the LED band from the 5 V pour is a deliberate change from the obvious arrangement. It gives **9.1 mm of separation** between the high-impedance sense trace and the 0.89 A switching rail, with a grounded pour and the LED band in between, instead of the ~3 mm that a shared edge forces. It removes the one credible noise-coupling path in the design at zero cost, and it means no filter capacitor is needed on the sense node.

> If you ever do need to filter that node, **do not fit 1 nF.** At 4.7 MΩ, 1 nF is a 4.7 ms measurement inside a 16 ms frame. Size any filter as a fraction of the ~36 pF already there: 10–22 pF adds 30–60 % to the baseline (calibrated away at boot, delta unchanged) and costs well under a millisecond.

Guard rails are GND-connected and stitched to the bottom plane with vias every 10 mm. The SENSE net is **top layer only, for its entire length, with zero vias** — each via adds ~0.5 pF and a plating-void failure mode on the one net that cannot tolerate an intermittent.

### 7.2 LED geometry

Pitch **16.66667 mm** exactly (60 LED/m). All eleven at **y = 11.000 mm**.

| n | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| x (mm) | 64.000 | 80.667 | 97.333 | 114.000 | 130.667 | 147.333 | 164.000 | 180.667 | 197.333 | 214.000 | 230.667 |

Span LED1 → LED11 = **166.667 mm**. Note this is 166.67, not 167.7 — ten gaps, not eleven.

End margins are exactly half a pitch (8.333 mm), which puts the **lit zone at x 55.67 → 239.00, i.e. 183.33 mm.** Make the diffuser that length. Make it 166.67 and the two end LEDs sit at the very edge and look clipped.

Each LED's 100 nF sits at (x_n + 3.40, y = 15.50), long axis along y, with its own via straight to the bottom plane.

### 7.3 Optics and the enclosure fit

**16.667 mm is a wide pitch.** The lamp reads as an even line only if the diffuser stands off far enough — rule of thumb for a high-haze opal is 0.7–1.0 × pitch, so 12–17 mm here.

The geometry is forced by the tube. For a bore of radius r, the chord at height z is `2*sqrt(r^2 - z^2)`, and the following must hold:

```
chord(z)  >=  board_width + 2 x spine_wall + 0.6 mm assembly clearance
```

**Specified: 30 mm OD × 2.0 mm wall opal tube (26.0 mm bore), board mounted at z = −4.50 mm, LEDs facing the far wall.**

```
chord(-4.5) = 2*sqrt(13.0^2 - 4.5^2) = 24.39 mm
board 20.00 + 2 x 1.80 spine wall = 23.60 mm      clearance 0.79 mm  OK
LED lens top at z = -4.5 + 1.6 = -2.9
standoff to far wall = 13.0 - (-2.9) = 15.9 mm = 0.95 x pitch
```

**The diffuser material matters more than the standoff.**

| Property | Requirement |
|---|---|
| Haze | **≥85 %** |
| Total transmission | 40–60 % |
| Material | Opal PMMA (best diffusion per unit cost) or opal PC (tougher) |
| Length | ≥190 mm, covering at minimum x 55.67 → 239.00 |
| Reject | clear, surface-etched "frosted", or sandblasted acrylic — these are **low-haze** and show eleven distinct dots at any standoff under ~30 mm |

What the user sees if they get it wrong, and this belongs in the README verbatim:

- ≥15 mm with high-haze opal: a clean, even line.
- ~10 mm with opal: faint scalloping at a glancing angle.
- ≤5 mm, or any low-haze cover under 30 mm: **eleven distinct dots.**

This is not a defect of the board; it is a property of the 60 LED/m pitch. A real 60/m strip looks like dots too unless deeply diffused.

**Rejected optical options, with costs.** Milled slots between LEDs help *edge-lit* designs where light travels through the substrate — here the LEDs emit normal to the board, so slots would remove copper (thermal), weaken a 282 mm strip (mechanical), and buy nothing. An acrylic light pipe is $2.00–3.50 and needs ±0.3 mm alignment to eleven LEDs. Per-LED printed reflector cells are actively harmful — cell walls sharpen the boundary between LEDs and make scalloping *worse*. White soldermask plus a white printed spine is the cheapest optical gain available: 10–20 % more light out for $0.10 and a filament choice.

### 7.4 Mechanical stack and mounting

```
                     +-------- opal tube, 30 OD x 26 ID x 220 mm --------+
   +----------+      |                                                   |   +---------+
   |   BASE   |======|   PCB in printed white spine, z = -4.5            |===| TOP CAP |
   | (printed)|      |   LEDs facing UP toward the far wall              |   | + flat  |
   |  head    |      +---------------------------------------------------+   | TOUCH   |
   | x 0->56  |                     x 56 -> 240                              | FACE    |
   +----------+                                                              | x250-282|
     USB-C <-
```

| Part | Specification |
|---|---|
| **Base** | Printed. Internal cavity ≥58 × 22 × 14 mm (14 mm depth clears the 10 mm electrolytic plus board and tolerance). Two M2.5 bosses at H1/H2. **No metal within 8 mm of the antenna region** — use plastic self-tapping M2.5 × 6 screws, or heat-set inserts only at H1/H2, which are 27 mm away. A Ø3.5 mm access hole aligned to SW1, labelled `BOOT`, reachable with a paperclip. A cable clamp: a 3.2 mm channel pinched to 2.8 mm capturing the jacket 15 mm behind the plug, closed by the base lid, zero parts |
| **Spine** | Printed channel, white PETG or PLA, **1.80 mm slot engaging 2.00 mm of each long board edge**, outer width 23.60 mm, running **x 56 → 240 only** — it must never reach the head (antenna) or the tab. Print in two 100 mm halves with a lap joint if the bed is short. Doubles as the reflector. A 2.5 × 2.5 mm wire channel on the y = 0 side carries the pigtail in the snapped configuration, as far from the 5 V pour as the geometry allows |
| **Tube** | Opal, 30 OD × 2.0 wall × 220 mm, spec per §7.3 |
| **Top cap** | Printed, housing the 31.25 mm tab. **It is not a round continuation of the tube.** It carries a locally flat, raised **touch face** — see §7.5 |
| **H1, H2** | Ø2.70 NPTH at (4.50, 4.50) and (4.50, 15.50), 0.50 mm copper clearance both layers, M2.5 pan head Ø4.7 max |

H1 and H2 flank the USB-C receptacle deliberately: **the axial force from a yanked cable passes into the screws, not into the connector's solder joints.** Together with the THT shield tabs, a base aperture that the plug body bottoms against (receptacle mating face 0.5 mm proud), and the cable clamp, that is four independent strain-relief measures, all free or near-free.

**No mounting holes anywhere in the lit zone** — they would collide with the row and puncture both pours. The two long edges captured in the spine handle the flex of 282 mm of 1.6 mm FR4, which is why 1.6 mm is specified and 1.2 mm must not be substituted.

**No mounting holes on the tab either.** There is no room alongside the pad pair, and a metal screw within 8 mm of the pad would wreck the baseline. Fix a snapped-off tab with double-sided foam tape, which conveniently also provides the standoff if the pad is mounted copper-side-in.

### 7.5 Touch pad — geometry, and an honest account of the margin

This is the least-certain subsystem in the design. It is also the one with the most no-respin escape hatches. Both facts are stated here rather than buried.

#### What the firmware does

`touch.py:50-66` drives the pad node to 3.3 V for 10 µs, floats the pin, and waits for it to fall through the input's logic-low threshold, discharging entirely through the external pull-down. `_is_currently_touched()` compares the result against a baseline auto-measured at boot. Two properties of that follow:

```
t_total = k * R * C_total       <- pad self-C, trace, guard, wire: all live HERE
dt      = k * R * dC_finger     <- depends ONLY on the electrode geometry and the overlay
```

Since the baseline is re-measured on the board at every boot, **wire and trace capacitance shift the baseline, which is calibrated away, and do not shift the delta at all.** That is what makes one threshold cover both tab configurations, and it is why the guarded channel is specified with GND on both sides *and* a solid plane beneath rather than following the usual "minimise parasitics" instinct. On this algorithm, parasitic capacitance to ground is free.

#### Two corrections that change the numbers

**(a) The constant is not 0.7·R·C.** That is the ln 2 half-way figure. The wait ends when the input crosses its logic-low threshold, so `k = ln(V_DD / V_T)`. But V_T is *not* the datasheet `V_IL(max) = 0.25 V_DD` either — that is the guaranteed-low limit, not the actual switching point, which sits somewhere between 0.83 V and 2.48 V and varies part to part and with temperature. `k` therefore ranges from 1.39 down to 0.72, nearly a factor of two, **and it scales the delta, which per-boot baseline calibration does not remove.** The design's central "one shipped constant" claim would fail on that alone.

The fix is structural and costs nothing: **compare against a fraction of the baseline, not an absolute count.** `k`, R tolerance, CPU clock and bytecode speed all appear identically in numerator and denominator and cancel exactly, leaving only ΔC/C_total. See §8.3.

**(b) The finger's return path is not mains earth.** The usual justification — "a human body has 100–200 pF to earth, so it is effectively a short" — is false for the supply this lamp ships with. A $3.50 5 V USB-C adapter is a 2-prong Class II part with no earth pin; board GND floats, coupled to earth only through a Y-capacitor (1–2.2 nF if fitted, often omitted) or transformer interwinding capacitance (~10–30 pF). On a power bank or a laptop running on battery there is no earth path at all, and ΔC collapses by 57–80 %. The lamp would work on the bench and be unresponsive in a user's hand.

The fix is a **split electrode pair**: SENSE and a GND return, side by side, both under the same overlay and both inside the fingertip footprint, so the finger bridges sense → finger → GND *locally*. It costs nothing — it reuses guard copper and an existing net. It roughly halves the best-case ΔC and removes the supply dependency entirely, which is a good trade for a product you post to friends.

#### Geometry

Tab is 20.0 mm wide, x 250.75 → 282.00 (31.25 mm long). All top layer, **covered by soldermask** (prevents corrosion and surface leakage; 25 µm of mask is a 1.7 % series-dielectric effect, negligible). **No copper on either layer beneath either electrode.**

| Element | Extent |
|---|---|
| `PAD_G` (GND return) | x 254.0 → 279.0, y 1.20 → 9.20 → 200 mm² |
| gap | 1.40 mm |
| `PAD_S` (SENSE) | x 254.0 → 279.0, y 10.60 → 18.60 → 200 mm² |
| Guard rail | 1.00 mm GND, along the y = 19.3 edge and the free end at x = 280.5, 1.50 mm clearance to `PAD_S` |
| Bottom-layer mirror ring | same U, stitched to the top ring with Ø0.30 vias every 8 mm; bare FR4 inside |

Equal areas are correct: for two electrodes in series the coupling `C ∝ s(A−s)/A` maximises at `s = A/2`.

#### The numbers, with their uncertainty stated

A fingertip covers roughly 150 mm², split across the pair. Through a **1.0 mm** overlay at ε_r ≈ 2.9:

```
C_pad-finger  = 8.854e-12 x 2.9 x 75e-6 / 1.0e-3 = 1.93 pF per electrode
series pair   = 1.93/2                           = 0.96 pF        <- FLOATING source, worst case
with an earthed / Y-capped adapter the earth path adds in parallel: 2-4 pF typical

C_total (baseline) = pad self-C to guard ~8 pF + 195 mm guarded trace ~25 pF + pin/R node ~3 pF
                   ~= 36 pF

fraction dC/C_total = 0.96 / 36 = 2.7 %  worst case
                    = 3.0 / 36  = 8.3 %  typical
```

With R = 4.7 MΩ and `k` in its mid-range (~1.0), the baseline is about **170 µs** and the worst-case delta about **4.5 µs**, measured with `utime.ticks_us()` at 1 µs resolution.

**That is 4–5 LSB of margin in the worst case, and I am not going to dress it up as more.** It is workable and it is the honest floor; the typical case is 3–4× better. There are four independent knobs, none of which needs a respin:

| Knob | Effect | Cost |
|---|---|---|
| Thin the cap's touch face from 1.5 → 1.0 → 0.8 mm | ΔC ∝ 1/d: +50 %, +88 % | Print setting |
| R10 4.7 MΩ → 10 MΩ | Doubles absolute µs (does **not** change the fraction) | 0402 stuffing value |
| Burst timing: N charge/discharge cycles between two `ticks_us` reads | N× absolute µs, same fraction | Config constant, costs N × 170 µs of frame time |
| `TOUCH_SAMPLES` min-of-N | Lowers the noise floor | ~0.2 ms per extra sample |

**Why 4.7 MΩ and not the 22 MΩ that would look better on paper.** The pull-down current at the decision point is `V_T / R`. At 22 MΩ that is 45–50 nA — the same magnitude as the ESP32-C3's guaranteed GPIO input leakage. If a given part leaks *into* the node, the node asymptotes at `I_leak × R` = 50 nA × 22 MΩ = 1.1 V, above the low threshold; the pin never reads 0, the wait runs to its safety cap on every call, and a sub-millisecond measurement becomes tens of milliseconds inside a 16 ms loop. The lamp stutters and touch is permanently dead. Because leakage is part-to-part and temperature dependent, that hits a *fraction* of the batch — the worst possible distribution, since one good prototype proves nothing. At 4.7 MΩ the asymptote is 0.24 V, comfortably clear, and the rate error is ~20 % rather than ~100 %. **Stage 1 must measure the settled DC voltage on the pad node with the pin floated**; if it is below 0.3 V, 10 MΩ is available for the extra absolute margin.

Also do not go above ~10 MΩ for a second reason: FR4 surface leakage with flux residue at 60 % RH is 10⁸–10⁹ Ω and starts to be a meaningful fraction of R. Use standard cleaning; do not conformally coat unless Stage 1 shows humidity drift.

#### The overlay, and the enclosure change it forces

**This is the part that a round tube quietly breaks.** The pad is top-layer copper in the board plane at z = −4.5, facing +z. If the top cap simply continued the tube, the nearest surface in that direction would be the inner wall at z = +13.0 — **17.5 mm of air plus 2 mm of plastic**, not 1 mm of plastic. ΔC would fall by more than an order of magnitude and the lamp would never register a touch anywhere on its enclosure. No assembly adjustment fixes that; every unit would have to have its tab snapped and taped to the cap wall, which destroys the whole premise of the attached default.

**Requirement on the top cap: a locally flat, raised touch face that brings 1.0 mm of plastic down onto the pad plane over the full 25 × 17 mm electrode pair.** The cap is printed, so this is a modelling change and costs nothing. Additional rules:

| Rule | Value |
|---|---|
| Overlay thickness over both electrodes | 1.0 mm nominal, **0.8–2.0 mm** allowed |
| Air gap between soldermask and plastic | **≤0.3 mm.** 1 mm of air behaves like ~2.6 mm of plastic (ε_r 1 vs 2.9). Either the face presses the pad, or a 1 mm closed-cell foam pad fills the gap |
| Metal near the pad | **None within 8 mm.** No screw, no insert, no foil |
| Marking | Printed texture or colour change on the touch face so the user knows where to press |

Never expose the copper.

#### The hazard this board does not fix

`touch.py:37` captures the baseline at construction and `main.py:595` re-captures once after MQTT connect. **There is no drift tracking.** A finger resting on the pad during boot — including the daily 17:00 UTC OTA reboot — bakes in a touched baseline and touch stays dead until the next reboot.

Hardware mitigation: the tab is at the **opposite end from the USB connector**, so the hand that plugs the cable in is never on the pad. That helps; it does not close it. The real fix is about fifteen lines of OTA-able firmware (§8.3), and it must ship with the first batch.

### 7.6 The break-away tab

**Mouse bites, not V-score, and this is geometry rather than preference.** A V-groove is cut by a circular blade that must traverse the whole panel edge to edge; it cannot make an interior or partial cut. Our break is an internal separation inside a rectangular outline, so V-score there is not manufacturable at all. Internal routed slots are part of the profiling operation and carry no surcharge.

**Break line at x = 250.000, a 1.50 mm routed slot (x 249.25 → 250.75) across the full 20 mm width, interrupted by three bridges:**

| Bridge | y extent | Width | Mouse bites (Ø0.60 NPTH, drilled on x = 250.000) | Webs | Residual FR4 |
|---|---|---|---|---|---|
| Lower | 2.30 → 4.70 | 2.40 | y = 3.00, 4.00 | 0.40 / 0.40 / 0.40 | 1.20 mm |
| **Centre** | 7.80 → 12.20 | 4.40 | y = 8.70, 11.30 | 0.60 / **2.00** / 0.60 | **2.80 mm** |
| Upper | 15.30 → 17.70 | 2.40 | y = 16.00, 17.00 | 0.40 / 0.40 / 0.40 | 1.20 mm |

**Every web is ≥0.40 mm and every hole edge is ≥0.40 mm from the slot edge.** That is not a detail — a 0.20 mm web (which is what you get if you space three holes evenly across a 3.0 mm bridge) is below standard fab capability *and* below the scale of a single FR4 glass bundle, so those webs are unreinforced resin. They blow out on router exit, the residual cross-section becomes a lottery, and the break force figure becomes meaningless. Worse, a partially fractured bridge that still holds the sense trace across cracked substrate gives an intermittent high-impedance connection on the one net that cannot tolerate one — presenting in the field as touch that works until the lamp is moved.

**The centre bridge is deliberately solid across its middle 2.00 mm** and carries the two crossing conductors. This makes the *attached* configuration — the default, which most builders will ship — genuinely strong.

```
SENSE   y = 9.50, 0.30 mm wide   ->  0.35 mm to the nearest mouse-bite hole edge
GND     y = 10.50, 0.30 mm wide  ->  0.35 mm to the nearest hole edge
gap between them 0.70 mm
```

0.35 mm exceeds JLC's 0.30 mm copper-to-hole minimum. This is a deliberate local exception to the 1.50 mm pour setback: these two traces are sacrificial by design and are knife-cut before the snap.

**Break force — estimated from cross-section and FR4 flexural strength, not measured.**

```
Z = sum(b*h^2)/6 = 5.20 x 1.6^2 / 6 = 2.219 mm^3
M = sigma * Z    = 415 N/mm^2 x 2.219 = 921 N.mm
F at a 25 mm lever = 921/25 = 36.8 N  = 3.8 kgf   (intact, all three bridges)

after nipping the centre bridge (residual 2.40 mm):
Z = 1.024 mm^3, M = 425 N.mm, F = 17.0 N = 1.7 kgf
```

**Hand-snappable at roughly 3.8 kgf over a table edge, comfortably easy at 1.7 kgf after nipping the centre bridge with flush cutters.** No vice, no pliers required. Range across FR4 lots: 2.7–4.6 kgf. **Snap one prototype and measure it before writing a number into the build guide.**

Knife-cutting the two traces is a purely *electrical* operation — it removes 35 µm of copper and contributes nothing to the mechanical break.

#### Keepouts — the snapping-stress question, answered concretely

| Rule | Value | Why |
|---|---|---|
| Component keepout, main side | **15.00 mm** from the slot edge (x ≤ 234.25) | MLCC flex cracking is the failure mode most likely to pass at the assembler and die at the builder, intermittently and nearly undiagnosably |
| Actual nearest component | LED11 pads end at x ≈ 233.2 → **16.0 mm clear**; its 100 nF is *upstream* at x = 234.07 → 15.2 mm clear | |
| Component keepout, tab side | **the entire tab** | Zero components on the tab. Removes the failure mode rather than mitigating it |
| MLCC long-axis orientation | **parallel to the break line (along y)** within 25 mm | All eleven LED bypass caps are along y anyway |
| 0805 and the electrolytic | all in the head, ≥215 mm from the break | Not a factor |
| Copper pour setback | **1.50 mm** from every slot edge and every mouse-bite hole, both layers | Copper tears and lifts pads when snapped |

#### The electrical crossing

**Two plated through-hole pairs, 2.54 mm pitch, Ø1.00 mm drill / Ø1.60 mm pad.**

| Ref | Side | x | y | Nets |
|---|---|---|---|---|
| J2 | main | 245.00 | 8.73 / 11.27 | SENSE, GND |
| J3 | tab | 254.00 | 8.73 / 11.27 | SENSE, GND |

J2's copper edge is 3.45 mm from the slot, J3's is 2.45 mm. Both clear the 1.50 mm setback. A through-hole with no component on it cannot crack, so the 15 mm keepout — which applies to *placed components* — does not bind here.

**Two conductors, SENSE + GND, is the right count.** The GND wire twisted with SENSE *is* the guard; a third conductor would need to be actively driven to beat it, and the firmware has no driven-shield capability.

#### The snapped configuration

| Configuration | C_total | Baseline @4.7 MΩ | Fractional delta | Frame cost |
|---|---|---|---|---|
| **Attached** (default) | ~36 pF | ~170 µs | **2.7 % worst / 8.3 % typical** | ~1.1 % |
| Snapped + 100 mm twisted pair | ~42 pF | ~198 µs | 2.3 % / 7.1 % | ~1.3 % |
| **Snapped + 200 mm (maximum)** | ~48 pF | ~226 µs | **2.0 % / 6.3 %** | ~1.5 % |

Baseline shift is about **+2.8 µs per cm of wire**; the absolute delta does not move at all. With the **proportional** threshold of §8.3 the fraction does shrink slightly with wire length, so **set the threshold against the 200 mm case** and both configurations are covered by one constant with margin to spare.

Mandatory rules for the snapped case, and they belong in the README:

- 28 AWG **twisted** pair, ~2 twists/cm, **maximum 200 mm**.
- SENSE twisted with GND, routed in the spine's wire channel on the y = 0 side, **away from the LED power feed** and not draped along it.
- **The 200 mm limit is set by noise immunity, not capacitance.** A 200 mm run beside a switching LED supply, sampled once with no filtering, will produce false taps. The min-of-N sampling in §8.3 is what makes 200 mm honest rather than optimistic.
- **Do not use shielded cable.** It runs ~1 pF/cm and its shield must be grounded at one end only, which builders get wrong. If someone insists, cap it at 120 mm.
- `TOUCH_FRACTION` does **not** change. The build instructions must not offer a second value.

#### Silkscreen at the break

```
   scissors CUT BOTH TRACES FIRST
   ===+===   SENSE
   ===+===   GND
   THEN BEND DOWN - NEVER TWIST
```

Text height 1.0 mm, black on white mask, printed on the main side at x ≈ 240–249 where it stays readable after the snap. This is the one place where silkscreen prevents a warranty return.

### 7.7 Assembly rules the fab needs

| Rule | Value | Why |
|---|---|---|
| **Thermal relief on every 0402/0805 pad connecting to a pour** | 4 spokes, 0.4 mm wide, 0.25 mm gap | Every LED bypass cap sits inside the 5 V pour with one terminal flooded and the other on a via to the plane. That thermal-mass asymmetry on the smallest package on the board is textbook tombstoning, and on *this* board a tombstoned cap is invisible at bring-up — it presents as exactly the "random LED flicker" the cap exists to prevent. It is a KiCad zone property and costs nothing |
| **LED pads: solid connection, no relief** | 4 thermal vias per LED, ≥60 mm²/layer | Deliberate, for θ_JA. See the rework note below |
| **LED rework note** | Bottom-side preheat to 120 °C before any hot air; mask adjacent lenses with Kapton | An LED whose ground pad is bonded to a full plane through four vias needs enough hot-air energy to soften the PPA lens of its neighbours 16.7 mm away. In practice a bad LED is a scrapped board, which is why the scrap allowance is 6 % rather than 3 % |
| Reflow | **Leaded Sn63Pb37, ~217 °C peak** | Cheaper at JLC *and* materially kinder to the SK6812 lens and phosphor than 245–250 °C |
| Cleaning | Standard no-clean, standard cleaning process. **Do not skip cleaning near the tab** | Surface leakage on a multi-MΩ node |
| Depanel | Routed-slot mouse bites between boards. **The internal break slot is NOT to be broken at the factory** | |

> **On LED moisture sensitivity, be realistic about what is available.** SK6812-class 5050 parts are typically MSL 3, and the standard remedies are not on offer at Economic PCBA: JLC does not run per-customer reflow profiles, free-text notes about peak temperature are not actioned on the line, and the standard MSL3 rebake at 125 °C for 24 h is **above** the deformation threshold of the PPA lens (these parts usually cap storage at 60 °C), so it would damage them. The three controls that actually exist are: select the leaded paste option, which is the only profile lever exposed; buy the LEDs on a single sealed in-date dry-pack reel and consign it with the desiccant and humidity indicator intact so floor life is not consumed in JLC's stores; and manage the rest by inspection — photograph the first article's white point against a reference and check it again on the qty-100 batch. Say so in the README rather than implying process control you do not have.

### 7.8 Panelisation

The outline is a **plain 282 × 20 mm rectangle** — the tab is an internal slot, not an outline feature — so there is nothing to nest and zero panel waste from the tab.

```
 PANEL 282.0 x 140.0 mm, 2-layer, 1.6 mm

 +--------------------------------------------------------------+  <- 5 mm rail
 | (+)                        [o] fiducials                 (+)  |
 |==============================================================|  <- 2.0 mm routed slot
 |  board 1   [HEAD]-------LEDs-------[gap][slot][TAB]           |  20 mm
 |==============================================================|
 |  board 2                                                      |  20 mm
 |==============================================================|
 |  boards 3, 4, 5, 6                                            |
 |==============================================================|
 | (+)                                                      (+)  |  <- 5 mm rail
 +--------------------------------------------------------------+
   ^ NO transverse rails. Board ends ARE panel ends.
```

| Parameter | Value |
|---|---|
| Boards per panel | **6** |
| Panel size | **282.0 × 140.0 mm** (6 × 20 + 5 × 2.0 slots + 2 × 5 rails) |
| Panel area / board area | 394.8 cm² / 56.4 cm² |
| **Utilisation** | 6 × 56.4 / 394.8 = **85.7 %** |
| Separation | **2.0 mm routed slots with mouse-bite tabs** between boards, three per boundary, at x = 40, 141, 242 |
| Rails | 5.0 mm on the two **282 mm** long edges only |
| Fiducials | 3 × Ø1.00 mm bare copper, Ø2.00 mm mask opening, asymmetric triple in the rails |
| Tooling holes | 2 × Ø3.00 mm NPTH in the rails |
| Panel ID | Silkscreen `EM-15 REV A 6UP ^` on a rail |
| Panels for 100 boards | **17** (102 boards) |

Two things about this arrangement are corrections worth stating:

**No V-score anywhere.** The module's antenna must sit near a board long edge, and a V-score blade cutting to ~1/3 depth from each face with ±0.15 mm positional tolerance and a ~0.28 mm surface groove has no usable clearance to a module can set back under about 1.0 mm. Either the fab flags it and the order stalls, or it runs and shears the shield, cracks the module's outermost solder joints, or nicks the antenna feed — invalidating the modular approval that the whole architecture exists to obtain, and doing it invisibly, as degraded RF rather than a dead board. Routed separation removes the blade entirely. It costs a little routing time and no material, and it hands back the 0.5 mm V-score copper setback to the touch guard rail.

**No transverse rails.** J1 sits at x = 0.00 with its mating face required to stand 0.5 mm proud of the base aperture, and the touch pad's free end is at x = 282. A rail at either end would have to be separated by mouse bites, and a 0.3 mm nub on the USB-C end face fouls plug insertion or stops the base closing. Conveyor grip is along the two 282 mm rails, which is what the design relies on anyway. Deleting the end rails also raises utilisation and leaves both board ends as clean routed profile.

### 7.9 Routing order

Each step depends on the previous one; reworking an earlier step is what turns a 14-hour layout into a 30-hour one. Do not autoroute — there are about 60 nets and three of them (SENSE, the 5 V path, D±) have hand-routing constraints no autorouter respects.

1. Outline, break slot, mouse bites, H1/H2, and **every keep-out as a rule area, not a graphic** — antenna, break, pad backside, pour setbacks.
2. Place the eleven LEDs at their exact x coordinates, y = 11.000, rotated 90°. Every other dimension derives from this row.
3. Place `PAD_S`, `PAD_G`, the guard ring and J3 on the tab; J2 in the gap. This fixes the SENSE endpoint.
4. Place U1 and verify the antenna keep-out against the datasheet figure, with the antenna end at the y = 0 long edge.
5. Place J1 at x = 0 and H1/H2 at x = 4.50.
6. Place C1, then F1 → Q1 → U3 around it. C1's position sets the star node.
7. Place U2 + R11 + R3 + C6 as a tight cluster between the module and LED1.
8. Place R7, R10, D2 (DNP) and TP6 at the head end of the guarded channel.
9. Place the eleven 100 nF at (x_n + 3.40, 15.50), then the remaining passives, SW1 and test points.
10. **Route SENSE first**, end to end, top layer, zero vias, with its two guard rails as one locked group. It is the fussiest net and the least tolerant of being squeezed by whatever routes first.
11. Route the DOUT→DIN chain, then U2 → R11 → LD1.DIN.
12. Route VBUS → F1 → Q1 → star node → the 5 V bridge across the head at y 8.6–10.6, 2.0 mm wide, clearing the antenna keep-out, then into the 5 V pour.
13. Route D+/D− as a 90 Ω pair through U4 to IO18/IO19: matched within 5 mm, no stubs, **no vias**, no series resistors.
14. Route 3V3, EN, straps, IO9/SW1.
15. Pour GND (bottom, whole board) with all keep-outs active; then 5 V (top, y 0.40–8.20) and GND (top, y 13.60–17.00).
16. Stitching and thermal vias. Then silkscreen: LED1 arrow, polarity marks, the break-line block, `CUT -> D1`, `BOOT`, rev, test-point labels.
17. DFM sweep (§9.4) and a 3D render against the base/spine/cap STLs.

**KiCad rules beyond the standard set:**

```
Rule area ANTENNA_KO   : per datasheet, both layers, forbid track/via/pad/zone/footprint
Rule area PAD_BACK_KO  : under PAD_S and PAD_G, B.Cu, forbid track/via/zone
Rule area BREAK_KO     : x 234.25 -> 282.0, all layers, forbid footprint
Rule area POUR_SETBACK : 1.5 mm around the slot and every mouse-bite hole, both layers, forbid zone
Net class SENSE        : width 0.30, clearance 0.35, VIA COUNT MUST BE ZERO (check manually)
Net class POWER_5V     : min 2.00 on discrete tracks, pours exempt
Net class USB          : diff pair 90 ohm, skew <= 5 mm, via count zero
```

Manual checks DRC will not catch: SENSE via count, MLCC long-axis orientation within 25 mm of the break, thermal-relief application, and pour continuity in the lit zone.

---

## 8. Firmware

### 8.1 `config.py` deltas

`config.py` is per-board and **never OTA'd** (`boot.py:5`), so this is the golden file flashed to all units, and anything wrong in it is a manual edit on every board forever. That is why `LED_PIN` was deliberately kept at 5.

| Constant | Now | EM-15 | Why |
|---|---|---|---|
| `LED_PIN` | `5` | **`5` — unchanged** | IO5 chosen on the C3 specifically so this and `hardware_test.py:65` never move |
| `NUM_LEDS` | `10` | **`11`** | |
| `TOUCH_PINS` | `[12]` | **`[3]`** | GPIO12–17 are internal flash pins on the C3, not bonded out on MINI-1 |
| `TOUCH_THRESHOLD` | `1` | *(legacy path only)* | Superseded by `TOUCH_FRACTION` on EM-15; kept present for old boards |
| `TOUCH_FRACTION` | — | **new, set at Stage 1** | Proportional threshold. See §8.3 |
| `TOUCH_METHOD` | — | **`"ticks"`** | Selects the µs-timed measurement. Absent ⇒ legacy loop counting |
| `TOUCH_SAMPLES` | — | **`5`** | min-of-N. Absent ⇒ single sample, i.e. legacy |
| `TOUCH_BASELINE_TRACKING` | — | **`True`** | Absent ⇒ off, i.e. legacy |
| `GROUP_MAX_LEDS` | `8` | **`8` — keep** | See §8.2 |
| `REVERSE_LEDS` | `False` | **`False` — MUST REMAIN PRESENT** | `colour.py:15` does a bare `from config import REVERSE_LEDS` with no try/except. Delete the symbol and the board does not boot. It is also a live runtime feature (`main.py:331`, `colour.py:242`), so it is not just a build constant |
| `MAX_CHANNEL_SUM` | — | **`680`** | Hard power/thermal clamp, §5.4 |
| `BOARD_REV` | — | `"EM-15"` | Optional, telemetry only, guarded import. Lets you tell an EM-15 from a discrete build in the MQTT status without a serial console |
| `LED_BRIGHTNESS`, `NUM_GROUPS`, `GROUP_MIN_LEDS`, `HOLD_TIME_MS`, `WATCHDOG_ENABLED`, palette, MQTT, WiFi, WebREPL | | unchanged | |

**Every new symbol read by an OTA'd file must have an `except ImportError` fallback that restores legacy behaviour.** `boot.py:16` syncs `main.py`, `colour.py`, `sk6812.py` and `touch.py` to *every* board, old and new, and an old board's `config.py` cannot be updated to add a flag. This is not politeness — the discrete boards run `TOUCH_THRESHOLD = 1` against a ±1-count noise floor, and switching them to proportional thresholds or aggressive baseline tracking would cause false taps.

There is a related hazard worth knowing about: `main.py:50-52` imports `sk6812`/`touch`/`colour` at module level, **outside** the crash-guard try/except at `main.py:880-894`. An `ImportError` there does not trigger the crash reboot — MicroPython prints a traceback and drops to the REPL, the board sits there, and on the next power cycle `boot.py:84` sees `PWRON_RESET` and resets the fail counter, so the crash-loop rollback never fires either. **A wrong-platform push is a permanent brick requiring USB.** The mitigation is in `boot.py` (§8.4).

### 8.2 `GROUP_MAX_LEDS` — keep 8, and here is the data

`colour.py:52` does `sizes[-1] += remaining` unconditionally, so the declared cap is not enforced on the last group. With `NUM_LEDS = 10` the worst case is `(1,1,8)` and the cap happens to be respected exactly; with 11, `(1,1,9)` becomes reachable. Benign — sizes still sum to 11, `strip.set()` bounds-checks, nothing crashes.

The obvious fix is to raise the constant to 9 so it is honest. Running the actual algorithm 200 000 times per option says don't:

| `NUM_LEDS`, `GROUP_MAX_LEDS` | mean largest group | P(a 9-LED group) | most common shape |
|---|---|---|---|
| 10, 8 *(today, the look you have)* | 5.96 | 0 % | (8,1,2) 6.4 % |
| **11, 8 (recommended)** | 6.28 | **1.6 %** | (8,1,2) 6.4 % |
| 11, 9 | 6.61 | **13.7 %** | **(9,1,1) 11.1 %** |

Raising the cap makes nine of eleven LEDs in one flat block the single most common partition, once every nine taps. Leaving it at 8 keeps the largest-group distribution closest to the ten-LED lamp you already like, and the 1.6 % over-run is cosmetically identical to a partition you would get anyway. It also means **no change to `index.html`**, which hard-codes `randomPartition(cfg.numLeds, n, 1, 8)`.

If you want the constant literally true, the fix belongs in `_random_partition`, not in config — but that file is OTA'd to ten-LED boards too, so don't.

**Confirmed against the code:** `NUM_LEDS` is imported at module scope (`colour.py:12`) and used only for the partition, the group-sum clamp (`colour.py:201-210`), the pixel walk (`colour.py:350-354`), `main.py:228-229`'s RAM cap, and the driver's preallocated buffer. **No hardcoded LED count anywhere else.** 10 → 11 really is a config change.

`index.html:585` defaults `numLeds` to `"10"`. Mismatch is benign in both directions — `colour.py:203-210` pads or clamps the trailing group — but change the default to `11` when you cut over.

### 8.3 `touch.py` — the measurement rewrite

Four changes, all gated on guarded config imports so legacy boards are byte-for-byte unaffected.

**(1) Measure with `utime.ticks_us()`, not by counting interpreted loop iterations.** The loop counter is a scale factor set by MicroPython bytecode speed and CPU clock, which is why the repo currently carries `TOUCH_THRESHOLD = 1` in `config.py` and `50` in `hardware_test.py` — an order of magnitude apart, in the same repo. A µs timer is immune to both.

**(2) Take the minimum of N samples, not the median or the mean.** This is the important one and it turns a liability into a strength. The ESP32-C3 is single-core: the Wi-Fi and lwIP FreeRTOS tasks preempt the interpreter on the same core, and any preemption inside the wait lets wall-clock time advance past the crossing. **With `ticks_us`, every form of corruption is one-sided — preemption can only make the reading larger.** The true value is therefore a floor, and `min` over a handful of samples is a near-perfect denoiser. (With the old loop counter the corruption was one-sided *downward*, which is far worse: it drags the baseline toward the low tail and then a clean sample reads as a touch.)

A finger is present for the whole ~1 ms burst, so min-of-5 still captures a touch.

**(3) Compare against a fraction of the baseline.** `k = ln(V_DD/V_T)`, R tolerance, and any residual timing scale all appear identically in the baseline and the delta and cancel exactly:

```python
def _is_currently_touched(self):
    val = self._measure()                      # min-of-N, microseconds
    return (val - self._baseline) > self._baseline * TOUCH_FRACTION
```

Set `TOUCH_FRACTION` from Stage 1 against the **snapped 200 mm** case, which is the smallest fraction, and it covers both configurations with one constant.

**(4) Baseline tracking, rate-limited and outlier-rejected.** Slow drift tracking is the only fix for boot-time baseline poisoning (§7.5), but a naive asymmetric tracker is dangerous. Rules:

- Reject any sample below ~60 % of the current baseline before it reaches the tracker — with min-of-N that should never happen, and if it does, something is wrong rather than drifting.
- Step the baseline by **at most ±1 µs per second**, symmetric. No proportional steps.
- Clamp the baseline to a plausible band derived from the boot calibration.
- Force a re-baseline if "touched" persists past 30 s. That alone closes the boot-poisoning hazard and has no failure mode of its own.

Also: `pin.init(machine.Pin.IN)` → `pin.init(machine.Pin.IN, None)`. The ESP32 port may leave a previously configured pull in place when `pull` is omitted, and a stray pull-up makes the wait run to its safety cap on every call. Probe the argument once at construction so a port that rejects it still works. **Confirm in Stage 0** — a baseline pinned at the cap is the signature.

### 8.4 `sk6812.py`, `boot.py`, and the rest

**`sk6812.py` is the one rewritten file.** `rp2` appears only there and in `hardware_test.py` — `main.py`, `boot.py`, `colour.py` and `touch.py` never import it, so they need no changes. Keep the class API byte-identical (`__init__(pin, num_leds, brightness)`, `set`, `set_all`, `set_brightness`, `show`, `off`) so nothing else moves, and select the back end by **capability detection at import**, not a config flag — the file is OTA'd to boards whose `config.py` cannot be updated, so a flag would be unreachable on exactly the boards that need it:

```python
try:
    import rp2
    _HAVE_PIO = True
except ImportError:
    _HAVE_PIO = False
# rp2 path: the existing PIO program, byte-identical to what is in the field.
# otherwise:  machine.bitstream(pin, 0, (300, 900, 600, 600), buf)   # ns T0H,T0L,T1H,T1L
```

The bitstream path is **strictly better than the shipped driver.** Tracing the current PIO program at its 10 MHz clock gives timings that do not match its own comment and are all outside the SK6812 windows: T0H 500 ns (spec 150–450), T0L 700 (750–1050), T1H 900 (450–750), T1L 300 (450–750). It works only because genuine parts are tolerant, and it is a latent part-substitution landmine. An explicit ns tuple removes it permanently. **Do not "fix" the rp2 path in the same change** — every deployed lamp depends on the current timing and there is no upside to changing behaviour on hardware you cannot easily reach. Ship it separately, or not at all.

**Do not shortcut with `neopixel.NeoPixel(pin, 11, bpp=4, timing=1)`.** Its byte order is right (`ORDER = (1,0,2,3)` → G,R,B,W, matching the existing `(G<<24)|(R<<16)|(B<<8)|W`), but `timing=1` is the **WS2812B** preset `(400, 850, 800, 450)` and T1H = 800 ns is 50 ns outside the SK6812 window. Call `machine.bitstream` directly. `neopixel` remains a working fallback.

**The power clamp lives in `SK6812.show()`, not in `colour.py`.** `show()` is the single choke point for every LED write on the board — the colour engine, the boot pulse, `hardware_test.py`, and `strip.off()` on the crash path. Putting it in `colour.py` would leave the boot pulse and any future path uncapped. Guard the config import so boards without `MAX_CHANNEL_SUM` get `cap = None` and byte-identical output to today.

Frame time: 11 × 32 bits × 1.2 µs = **422 µs**, 2.6 % of a 16 ms frame. The ≥80 µs latch is supplied incidentally by the inter-frame gap. **Verify in Stage 0** that 422 µs of interrupts-off does not disturb Wi-Fi; the fallback is `esp32.RMT` (the C3 has 2 TX channels), but RMT means building a ~700-entry pulse list per frame in MicroPython, which is much worse for 60 fps, so prove bitstream first.

**`boot.py` gets four changes.** It is not OTA'd, so this must be flashed manually — free on new boards, once over WebREPL on existing ones *before* the first cross-platform push.

1. **An import smoke test.** The existing `compile()` gate proves a file *parses*; `import rp2` parses perfectly and then raises on an ESP32. Add `SMOKE_FILES = ("sk6812.py", "touch.py", "colour.py")` and `exec()` the staged copy of each before committing. All three have side-effect-free module bodies (constants, class definitions, a PIO assembly on rp2 — no hardware is claimed), so this is safe, and it catches a wrong-platform driver, a new config symbol imported without a fallback, and any top-level `NameError` a syntax check cannot see. `main.py` is deliberately **not** in the list — its module body constructs the strip and the touch manager.
2. **Move the identity check before `compile()`, and compare in 512-byte chunks.** The common case — the daily 17:00 reboot with nothing changed — currently compiles a 36 KB `main.py` in RAM for no reason *and* holds two full copies of it while comparing. On a C3 with the Wi-Fi and mbedTLS stacks already on the heap, that is the tightest moment in the whole firmware. After the change, a no-change boot does zero compiles and never holds more than one 36 KB string. Straight win on RP2040 too.
3. `import gc`, with `del` and `gc.collect()` between files and immediately after the response is closed.
4. No change to `REPO_RAW` or `SYNC_FILES`.

**`main.py` needs no changes.** Confirmed by inspection: it never imports `rp2`, and its only port-specific calls (`machine.WDT`, `unique_id`, `reset`, `reset_cause`, `network.WLAN`, `webrepl`, `ntptime`, `umqtt.simple`) all exist on the esp32 port. Leave `WDT(timeout=8000)` alone — it sits at the RP2040's ~8.388 s ceiling and has headroom on ESP32, and keeping it identical keeps both platforms behaving the same. The optional `BOARD_REV` addition follows the existing `WATCHDOG_ENABLED` pattern at `main.py:35-38`.

**`hardware_test.py` needs a rewrite**, not a tweak. It currently hard-codes `TOUCH_PIN = 12` and `NUM_LEDS = 8` — the LED count is already wrong for the existing ten-LED build — and carries its own inline PIO copy of the driver. Structure in §9.2.

**Operational recommendation, zero code change: canary via a staging branch.** `boot.py` is per-board and not OTA'd, so point one discrete Pico W and one EM-15 at a `staging` branch by editing one line of their `boot.py`. Push to `staging`, wait one daily reboot cycle, confirm both canaries came back, then fast-forward `master`. It costs nothing and it is the only mechanism you have that tests both platforms before the fleet sees a change.

---

## 9. Bill of materials, ordering, and the prototype plan

### 9.1 BOM

Prices are per placement at the LCSC tier you land in buying for that quantity, including 5–10 % spares.

| # | Ref | Qty | Part | LCSC | Package | @10 | @100 | @500 | JLC tier |
|---|---|---|---|---|---|---|---|---|---|
| 1 | U1 | 1 | **ESP32-C3-MINI-1-N4** | C2838502 | module | 3.470 | **2.920** | 2.920 | Extended |
| 2 | LD1–11 | **11** | **SKC6812RGBW-WS** (OPSCO) | C5378724 | SMD5050-4P | 0.1024 | **0.0821** | 0.0821 | Extended |
| 3 | U2 | 1 | **SN74AHCT1G125DBVR** | **C7484** | SOT-23-5 | 0.060 | 0.045 | 0.038 | Extended |
| 4 | U3 | 1 | AP2112K-3.3TRG1 | verify | SOT-23-5 | 0.090 | 0.065 | 0.055 | Basic |
| 5 | Q1 | 1 | AO3401A | C15127 | SOT-23 | 0.040 | 0.025 | 0.020 | Basic |
| 6 | J1 | 1 | TYPE-C-31-M-12, THT shield tabs | C165948 | USB-C 16P | 0.250 | 0.140 | 0.120 | Basic |
| 7 | U4 | 1 | USBLC6-2SC6 | verify | SOT-23-6 | 0.120 | 0.075 | 0.065 | Basic |
| 8 | F1 | 1 | PPTC 2 A hold / 4 A trip, ≤0.06 Ω | search | 1812 | 0.070 | 0.045 | 0.038 | likely Ext |
| 9 | SW1 | 1 | SMD tact switch | search | 3×4 mm | 0.050 | 0.035 | 0.030 | likely Basic |
| 10 | C1 | 1 | 470 µF / 10 V alu, ≤10 mm, ESR ≤0.2 Ω | search | 8×10.2 | 0.150 | 0.100 | 0.085 | likely Ext |
| 11 | C2–C5 | **4** | 22 µF 0805 X5R ≥10 V | verify | 0805 | 0.025 | 0.012 | 0.010 | Basic |
| 12 | C6–C20 | **15** | 100 nF 0402 X7R **16 V** | verify | 0402 | 0.003 | 0.0015 | 0.0012 | Basic |
| 13 | R1–R7 | **7** | 5.1 kΩ 0402 1 % | verify | 0402 | 0.002 | 0.0008 | 0.0006 | Basic |
| 14 | R8, R9 | 2 | 100 kΩ 0402 1 % | verify | 0402 | 0.002 | 0.0008 | 0.0006 | Basic |
| 15 | R10 | 1 | **4.7 MΩ 0402 5 %** | search | 0402 | 0.006 | 0.003 | 0.002 | verify tier |
| 16 | R11 | 1 | 47 Ω 0402 1 % | search | 0402 | 0.002 | 0.0008 | 0.0006 | Basic |
| — | DNP | 4 | D1 (SMA), D2 (0402), D3 (SOD-123), C21 (0402), J2/J3/J4 (THT), LK1 | — | — | 0 | 0 | 0 | — |
| — | free | 11 | TP1–TP11, H1/H2, PAD_S/PAD_G | — | — | 0 | 0 | 0 | — |

**16 unique lines. 50 placements. ~204 joints. Zero THT placements, zero hand-solder operations, zero consigned parts.**

Component subtotal per board: **@10 $5.62, @100 $4.43, @500 $4.34**, before attrition. The module and the LEDs are 78 % of it.

**Line-level notes that matter:**

- **The LEDs are the number one live risk.** The "reference" `SK6812RGBW-NW` (C5160656) already shows unavailable at LCSC. `SKC6812RGBW-WS` (C5378724) is the primary because it is the one positively confirmed in the JLC *assembly* library, and warm white matches `BASE_WARM_WHITE`. `SKC6812RGBW-NW` (C5348912) is the second source and is cheaper below 1000 pcs, so use it for prototypes regardless. **`SKC` is not `SK`** — data order, bit timing, V_IH and per-channel current are unconfirmed and are a mandatory Stage 0 gate. **Buy all ~1,200 pieces in one PO, one date code, one bin, and tick "do not substitute".** An RGB three-channel part drops into the same footprint and would silently break `colour.py`'s entire W-dominant model — the one substitution that produces 100 boards that light up and are still wrong.
- **C7484 is AHCT. C7468 is AHC.** Two digits apart, and the wrong one fixes nothing. Put the note in the schematic as text, not just the BOM.
- **100 nF at 16 V, not 50 V.** The highest rail is 5 V; 16 V X7R 0402 is Basic and cheap, the 50 V equivalent is often Extended. At 5 V bias a 16 V part loses ~20 %, irrelevant for a bypass cap.
- **R10 is the line that must not be value-engineered.** It converts `TOUCH_FRACTION` from a per-unit measurement into a shipped constant. If 4.7 MΩ 0402 is thin, use 4.7 MΩ 0603 or 10 MΩ 0402 (§7.5). **Do not fall back to 1 MΩ** — that collapses the delta and reintroduces per-unit calibration on all 100 boards.
- For the passive lines the C-number is not load-bearing; pick whatever JLC currently lists as **Basic** in that value, package and tolerance. That is exactly why they are cheap.

### 9.2 PCB, assembly and landed cost

**PCB:** 2 layer, FR-4, standard T_g, **1.6 mm**, **1 oz**, **HASL with lead**, **white mask / black silk**, 2.0 mm routed inter-board slots, internal break slot and NPTH mouse bites, order number "specify a location" on a rail (free; removal costs ~$1.50).

**Assembly:** JLCPCB Economic PCBA, single-sided. Published rates: setup $8.18, stencil $1.53, $0.0016/joint, $3.07 per unique Extended part, $0.00 for Basic. Assuming 5 Extended lines:

```
fixed    = 8.18 + 1.53 + 5 x 3.07 = $25.06
variable = 204 joints x $0.0016   = $0.326 per board
```

| | qty 10 | qty 30 (5 panels) | qty 100 (17 panels) | qty 500 |
|---|---|---|---|---|
| Components (+3 %) | 5.79 | 5.35 | **4.56** | 4.47 |
| PCB | 4.00 | 1.40 | **0.82** | 0.56 |
| Assembly | 2.83 | 1.16 | **0.58** | 0.38 |
| Freight (DHL, CN→CH) | 2.50 | 1.05 | **0.45** | 0.30 |
| Swiss import VAT @8.1 % | 1.22 | 0.72 | 0.52 | 0.46 |
| Customs clearance (~$22 flat) | 2.20 | 0.73 | 0.22 | 0.04 |
| Scrap / DOA allowance **6 %** | 0.91 | 0.52 | 0.44 | 0.37 |
| **TOTAL LANDED, ASSEMBLED BOARD** | **$19.45** | **$10.93** | **$7.59** | **$6.58** |
| *(ex-VAT/duty, e.g. shipped to a US address)* | *$16.03* | *$9.48* | *$6.85* | *$6.08* |

**Honest quotable ranges: qty 10 → $18–23. qty 30 → $10–13. qty 100 → $7.00–9.00. qty 500 → $6.00–7.50.** PCB pricing is a model, not a quote, and is ±25 %.

The **6 % scrap allowance** is not padding. An eleven-deep series-data chain of parts that cannot practically be reworked (§7.7) at a typical 0.3 % per-LED assembled defect rate gives 3.3 % of boards with at least one dead LED, and each is a whole-board write-off, not a component loss. Add normal SMT fallout and 6 % is the honest number.

At qty 10, fixed cost is 89 % of the assembly bill and ~45 % of the landed total. **Note the shape of the curve: with a 6-up panel, JLC's five-panel minimum means ordering "10" gets you 30 boards for about 56 % more money.** Order 30.

### Complete boxed lamp, qty 100

| Item | $ |
|---|---|
| Assembled EM-15 board | 7.59 |
| Opal diffuser tube, 30 mm OD × 220 mm, cut from extrusion | 2.50 |
| Printed base + spine + top cap, in-house (**filament only**) | 1.90 |
| 5 V / 2.4 A USB-C supply | 3.50 |
| USB-C cable, 1 m | 1.00 |
| Packaging | 0.60 |
| **TOTAL** | **$17.09** |

**Is the $20 target real? Plainly:**

- Bare assembled board at qty 100: **$7.59.** Comfortably inside.
- Complete boxed lamp with a supply, enclosure printed by you: **$17.09.** Inside, with $2.90 of room.
- Without a supply in the box: **$13.59.**
- **With an outsourced printed enclosure (MJF/SLS at $6–9): $22–25. Over target.**
- Injection moulding is not viable at 100 units — tooling alone is $1,500+, i.e. $15/unit.
- Honest floor for the electronics alone with these features, no hand-soldering, green mask, no PPTC, cheapest LED tier, ex-VAT: **≈$5.60/board at qty 100.** Below that you are deleting the level shifter or the bulk cap, which buys pennies and costs a revision.

**Two costs are not in that table and both are larger than the BOM.** The enclosure line prices filament, not machine time: base + 184 mm spine + top cap is roughly 6.5 hours per lamp, so **100 lamps is ~650 printer-hours — about a month of continuous single-machine printing — plus a 5–10 % print-failure rate.** And your own time: the driver port plus Stage 0 is ~6 h, KiCad layout ~14–18 h (a 282 mm board with a guarded high-impedance net and a panel is not a quick one), bring-up ~4 h, README rewrite ~2 h. At any honest rate that dwarfs the qty-100 BOM, which is itself the strongest argument for the architecture with the fewest ways to need a second spin.

### 9.3 What was deleted, and what breaks

| Deleted or consolidated | Saved | What breaks |
|---|---|---|
| USB-UART bridge + its crystal | $0.35, 2 lines | Nothing — the C3 has native USB Serial/JTAG |
| External crystal + load caps + QSPI flash | $0.27, 3 lines | Nothing — inside the module |
| Separate VBUS TVS | $0.04, 1 line | Nothing measurable — U4 clamps ESD, C1 is a better hot-plug clamp |
| Touch TVS → DNP | $0.05, 1 line | Nothing — the pad is under mask *and* behind plastic, no galvanic path |
| RESET button | $0.04, 1 line | Nothing — and it removes the three-presses-in-60 s rollback path. TP10 replaces it |
| Power indicator LED + resistor | $0.02, 2 lines | Nothing — it is a light leak inside a lamp; the eleven RGBW LEDs *are* the indicator |
| Barrel jack → DNP pads | $0.20, 1 line | Nothing — and it deletes the ORing problem (2 Schottkys at 0.35 W, or a P-FET mux) |
| Connector at the break → bare THT pads | $0.35, 1 line, 1 crimp op | Nothing — a soldering iron is already required to rewire |
| USB 27 Ω series pair | 1 line | Nothing — the C3 reference design connects D± directly |
| Guard conductor at the break (3rd pad pair) | — | Nothing — GND twisted with SENSE *is* the guard |
| Series diode → DNP + cuttable link | $0.02, 1 line | Nothing — the hedge is preserved at zero cost |
| Separate 10 µF LED-rail line → reuse 22 µF | $0.01, 1 line | Nothing — 22 µF X5R at 5 V bias is ~11 µF effective, exactly what the rail wants |
| Second-side assembly | ~$0.55 | Nothing — everything fits on one side |
| Second PCB / flex tail for the LED bar | ~$1.50 | Nothing — the break-away tab is the right answer |
| Resistors → 4 values, capacitors → 3 values | ~6 lines ≈ $18 one-off setup | Nothing |

**Refused to cut — $0.42 total, and this is the price of not needing a revision:**

| Kept | $ | Because |
|---|---|---|
| U2 + C6 (74AHCT1G125) | 0.11 | 3.3 V into a 5 V SK6812 is unconditionally out of spec; intermittent field failure no OTA can reach |
| C10–C20 (11 × 100 nF) | 0.02 | Unbypassed LED neighbours are the *actual* cause of "random flicker" |
| C1 (470 µF) | 0.10 | 0.379 V droop on a 0→0.891 A step |
| Q1 + R8 + C7 | 0.04 | Uncontrolled 470 µF inrush = "only works if I replug it" |
| F1 (PPTC 2 A) | 0.06 | Protects the *user's charger*, not the board |
| U4 (USBLC6) | 0.07 | Protects the only OTA-brick recovery path |
| C4 (4th 22 µF at the module) | 0.02 | Wi-Fi TX brownout is the classic ESP32 module failure |
| R10 + defined electrode geometry | 0.003 | Converts the threshold from a per-unit measurement into a shipped constant |
| R3 (5.1 kΩ on IO5) | 0.001 | Stops a floating AHCT input latching garbage at power-up |

### 9.4 Ordering procedure

**Before you click anything, verify the BOM against the live library (30 minutes).** Go to jlcpcb.com/parts, search every C-number, and record library tier and stock. Specifically:

- [ ] C2838502 (module), stock ≥ 200
- [ ] **C5378724 (LEDs), stock ≥ 1,300.** If not, switch to C5348912 and re-check. If neither is in the *assembly* library, plan consignment of a 1,000-pc reel now
- [ ] **C7484 — and confirm you have not typed C7468**
- [ ] AP2112K-3.3, C15127, C165948, USBLC6 — should all be Basic
- [ ] Your chosen PPTC, tact, 470 µF, 4.7 MΩ and the four passive values — record tiers
- [ ] Count the Extended lines and recompute `fixed = 8.18 + 1.53 + 3.07 × N`

**Files.** Panelise in KiCad (or KiKit) to the 282 × 140 mm arrangement in §7.8, then generate: RS-274X gerbers of the **panel** (`F.Cu, B.Cu, F.Mask, B.Mask, F.SilkS, B.SilkS, F.Paste, Edge.Cuts`), Excellon drills with PTH and NPTH separate (including the Ø1.00 mm J2/J3 holes and the Ø0.60 mm mouse bites), a BOM CSV (`Comment, Designator, Footprint, LCSC Part #`, one row per unique value), and a CPL CSV in **panel coordinates** with all 300 placements (50 × 6), all `Top`. **Do not list the DNP footprints or test points in either file.**

**PCB tab.** 2 layers, dimensions should auto-read **282 × 140 mm** — check it. Delivery format **Panel by Customer**, break-away rail **yes** (we drew our own), **PCB Qty = number of panels, not boards** — check the summary says "5 panels / 30 single boards" and not 5 boards. 1.6 mm, White mask / Black silk, HASL with lead, 1 oz, no gold fingers / castellated / edge plating, tented vias, order number "specify a location", **Confirm Production File = Yes** (worth the day it costs on a first article).

**Assembly tab.** Economic, Top Side, PCBA Qty in boards, tooling holes "Added by Customer", leaded solder paste if offered, **Confirm Parts Placement = Yes**.

**The parts review screen is where boards get killed.** Resolve every "part not found". Never accept a JLC-suggested alternative silently. On the LED line add: *"D1–D11 must be SKC6812RGBW-WS (C5378724), 4-channel RGBW, GRBW data order. Do NOT substitute an RGB (3-channel) part — it is footprint-compatible and functionally wrong."* Confirm the buffer line shows C7484 / SN74AHCT1G125DBVR.

**The placement preview is not optional.** Check **every one of the eleven LED rotations** — LED rotation is the single most common JLC PCBA error, because the LCSC tape-and-reel convention frequently differs from the KiCad footprint's. Zoom on LD1 and LD11 and confirm DIN faces the buffer / the previous LED's DOUT. Getting this wrong makes 100 boards where nothing lights. Also check U1's pin 1, the USB-C overhang at the board edge, **Q1's source toward the input and drain toward the load** (a reversed P-FET conducts through its body diode permanently and silently deletes the soft-start), and **U2 pin 1 to GND**.

**Separately from LCSC, to yourself, the same week:** 100 spare LEDs (the rework part you will actually need), 10 spares each of the module, AHCT, LDO and FET, and 28 AWG twisted pair for testing the snapped configuration.

### 9.5 Prototype plan

#### Stage 0 — before layout. ~$15, one evening. Retires most of the project risk.

One ESP32-C3 dev board and 5 loose LEDs of the **exact intended LCSC part number**. Prove, in this order:

1. `machine.bitstream(pin, 0, (300, 900, 600, 600), buf)` drives the five LEDs, and **the colour order really is G,R,B,W** — light one channel at a time. If OPSCO ships R,G,B,W, every colour in the app is wrong.
2. **A complete `boot.py` OTA cycle** — HTTPS to raw.githubusercontent.com plus `compile()` of the 36 KB `main.py`. This is the most RAM-hungry thing the firmware does and the one real C3 unknown. Log `gc.mem_free()` before and after.
3. `main.py` end to end: `network.WLAN`, `umqtt.simple` via `mip`, `ntptime`, `webrepl`, `machine.WDT`, `unique_id`, `reset_cause`. ⚠ `mip.install("urequests")` may 404 on recent MicroPython — micropython-lib renamed it to `requests`. If so, install `requests` and drop `from requests import *` at `/lib/urequests.py`.
4. **Measure the touch node on a breadboarded 4.7 MΩ and a scrap of copper foil**: the settled DC voltage with the pin floated (this is the leakage floor that decides 4.7 vs 10 MΩ), the baseline in µs, and the finger delta through 1 mm of plastic.
5. Confirm 422 µs of interrupts-off per frame does not disturb Wi-Fi — watch MQTT keepalives over an hour.
6. Confirm `pin.init(Pin.IN, None)` clears a deliberately-set internal pull.

**If any of this fails you have lost $15 and an evening, and you fall back to the Pico W head at +$520.** That asymmetry — a firmware risk you can retire in advance versus supply and process risks you cannot — is the whole argument for this architecture.

#### Stage 1 — 30 prototype boards, ~$330 all-in

**Visual, before power (2 minutes):** all eleven LED pin-1 chamfers pointing the same way (one reversed LED kills everything downstream); module orientation and a clean antenna keep-out; 470 µF polarity; USB-C 0.5 mm pitch under magnification; **the buffer's part marking says AHCT, not AHC or LVC.**

**Multimeter, unpowered, no USB.** Anything marked STOP means do not apply power.

| From | To | Expect | If wrong |
|---|---|---|---|
| LED_5V | GND | >100 kΩ after 10 s settling | <1 kΩ → **STOP** |
| +3V3 | GND | >50 kΩ | <1 kΩ → **STOP** |
| USB VBUS | +5V | diode-check ≈0.3–0.6 V one way, open the other | continuity both ways → FET shorted or reversed |
| **CC1 / CC2** | GND | **5.1 kΩ each** | **2.55 kΩ on either = one resistor bridging both CC pins.** Dead in one cable orientation |
| **IO2 / IO8** | +3V3 | **5.1 kΩ each** | open on IO2 → **STOP**, the module never boots |
| IO5 | GND | 5.1 kΩ | open → floating AHCT input |
| U2 pin 1 | GND | 0 Ω | open → a '126 was fitted, or the net is wrong |
| U3 pin 3 (EN) | U3 pin 1 (VIN) | **0 Ω** | anything else → the rail never comes up |
| DIN test point | LD1 DIN | **47 Ω** | 330–470 Ω → wrong resistor |
| SENSE (TP6) | GND | **4.7 MΩ ±5 %** | 0.5–2 MΩ → flux contamination, clean and re-measure; open → touch runs to the safety cap every loop |
| D+ | D− | open | continuity → bridge, USB dead |
| J2.SENSE / J2.GND | J3 equivalents | continuity | tab attached |

**Power-on. Do not plug it into a wall charger first.** Bench supply at 5.00 V, current limit 150 mA, on the DNP aux pads or a USB breakout. Expected quiescent before firmware: eleven SK6812 ICs at ~1 mA, LDO Iq, C3 booting → **40–70 mA.** Above ~120 mA with no LEDs lit, power off and go back to the meter. Then check 3V3 = 3.20–3.40 V, raise the limit to 1.5 A, and move to the real supply. **Do not fit the diffuser yet** — you need to see individual LEDs.

**Then run the staged self-test** (`hardware_test.py`, rewritten, self-contained, dual-platform, no WiFi for stages 0–3):

- **`stage0`** — identity and environment: `sys.platform`, `sys.implementation` (**record the MicroPython version and pin that exact image for all 100 units**), which LED back end was selected, `machine.freq()`, `reset_cause()`, `gc.mem_free()`, filesystem free bytes, import checks, and the measured touch timing primitives.
- **`stage1a` WALK** — exactly one white LED steps 1 → 11 with the index printed. A skipped position localises a dead or reversed LED, or a broken DOUT→DIN hop, to a *specific* LED. **The first bad position is the fault**; everything after it is a symptom.
- **`stage1b` BYTE ORDER** — full strip r, then g, then b, then w, naming the expected colour. Red showing green means G/R swapped. **White showing nothing while colours smear along the strip means an RGB three-byte part was fitted** — stop, wrong part.
- **`stage1c` LATCH** — full white for 2 s. **Any twitching or a wrong-coloured first LED here is the level shifter**, not the data: AHC/LVC fitted, or OE̅ not pulled low.
- **`stage2` TOUCH** — 400 untouched samples → baseline and noise (p99−p1), 150 touched → delta, printed as a fraction with a PASS/FAIL against `delta ≥ 4 × noise`. Run it **three times**: (a) tab attached with the real cap fitted, (b) after snapping one prototype's tab and wiring 200 mm of twisted pair — confirm the *fraction* holds and the baseline rose by roughly 2.8 µs/cm, (c) with the sense wire deliberately draped along the LED power feed, to see how bad it gets when a builder does the wrong thing. Run (a) with **at least five boards and three different people** (dry hand, damp hand, child's hand) and set `TOUCH_FRACTION` from the **worst** delta with ≥3× margin. **Measure on three power sources — earthed bench supply, the shipped 2-prong adapter, and a USB power bank — and require the criterion to pass on all three.**
- **`stage3` CURRENT** — four known patterns, 6 s each: all off + WiFi off (40–70 mA), warm white @0.6 (140–200 mA), full white RGBW @1.0 with the clamp bypassed (780–950 mA), clamped (560–680 mA). Anything above 1.3 A or a rail below 4.5 V is a fault.
- **`stage4` EVENTS** — live tap/hold with raw and delta printed on every transition. Run for a few minutes and watch for chatter.

**Also in Stage 1, and each of these settles something this document could only model:**

1. Scope the 5 V rail on hot-plug from a real charger, **20 cycles**, confirming a ~10 ms ramp with no re-trigger and a clean boot every time.
2. Scope 3V3 at TP2 during a Wi-Fi TX burst with the string at full white, from a 4.5 V source through a 2 m cheap cable.
3. Scope SENSE at TP6 with the string cycling off → full white.
4. **Deliberately snap one tab** — cut both centre-bridge traces, then bend flat over a table edge, never twist — and re-test both halves. **Measure the actual break force with a spring scale** and write the real number into the build guide.
5. Two hours at full white with a thermocouple on LD6 (middle of the string, hottest by adjacent-LED coupling), inside the real enclosure. Set `MAX_CHANNEL_SUM` from that measurement, not from the model.
6. Confirm TP7 (`LD11_DOUT`) toggles.
7. Photograph the white point against a reference for the MSL comparison later.

**Then, and only then, order 100.** Skipping Stage 1 is the single most expensive thing available here: one respin costs more than the entire component saving this document argues for.

### 9.6 Residual risks, ranked

1. **RGBW 5050 LED supply.** A genuine single source — OPSCO is effectively the only vendor in the LCSC catalogue and the reference part is already unavailable. Mitigation is **consignment (~$25 for a 1,000-piece reel), not substitution.** Buy the full run in one PO, verify stock the day you order, tick "do not substitute", keep a 100-piece reserve.
2. **Touch margin.** 2.7 % worst-case fractional delta is workable and honest but it is *modelled*, not measured, and it is the least-certain number in this document. Stage 0 item 4 and Stage 1 `stage2` exist to settle it, with four no-respin knobs (§7.5) if it comes in low. The single most important measurement in Stage 1 is the snapped-pigtail comparison: **if the fraction changes materially with wire length, the guard and return model is wrong and the one-constant claim collapses.**
3. **ESP32-C3-MINI-1 tier, stock, and strapping.** Verify before layout, including whether the module already pulls IO2 or IO8 internally. The `-H4` variant is a same-footprint fallback but was thin on stock; `WROOM-02-N4` is cheaper and a **different footprint**, i.e. a respin, not a swap.
4. **Inrush peak.** 235 mA is a linear-ramp estimate; the honest range is 200–400 mA. Stage 1 item 1, with two drop-in fixes.
5. **`machine.bitstream` on the C3.** Believed supported (it is what `neopixel` uses) but not verified on that chip. Stage 0 item 1, fallback `esp32.RMT` — which is materially worse for 60 fps, so prove bitstream first.
6. **Boot-time baseline poisoning.** Unchanged from the current design and **not fixed by this board.** Tab placement helps; only the firmware drift tracking closes it. Ship it with the first batch.
7. **Thermal is safe only because of the clamp.** Unclamped sustained full white puts T_j at ~102 °C. The clamp sits below and independent of `LED_BRIGHTNESS` so a user cannot defeat it, but an OTA could.
8. **Break force is estimated**, from cross-section and FR4 flexural strength. Snap one prototype and measure before writing the build guide.
9. **Enclosure machine time.** ~650 printer-hours for 100 lamps is a schedule risk of the same class as the $520 module decision, and it is the item most likely to push the complete lamp over $20 if it has to be outsourced.
10. **Certification.** The module carries modular approval so there is no intentional-radiator campaign, but a commercial sale still needs FCC Part 15B and a CE/RED DoC — a bill exceeding the BOM cost of your first 300 units. "Possible small sale later" is the expensive phrase in the brief.
11. **`config.py` is never OTA'd.** Anything wrong in it is a manual edit on every unit forever. `REVERSE_LEDS = False` **must remain present** or `colour.py:15` fails to import and the board does not boot.

---

## 10. What the README must say

**Snapping the touch tab**

> The touch pad is on a break-away tab at the top of the board. **Leave it attached** unless you want the pad somewhere else — attached is the default and needs no wire, no connector and no firmware change.
>
> To snap it off, in this order:
> 1. **Cut both traces on the centre bridge** with a craft knife at the silkscreen scissors mark.
> 2. Optional but recommended: nip the centre bridge with flush cutters. This drops the break force from about 3.8 kgf to about 1.7 kgf.
> 3. Lay the board **flat and supported** with the break line at a table edge and **bend the tab down. Never twist.**
> 4. File the nubs if the tab must sit flush.
>
> Rewire with **28 AWG twisted pair, 200 mm maximum**, SENSE twisted with GND, soldered into the J2/J3 through-hole pairs either side of the break. Route it in the spine's wire channel, **away from the LED power feed**. Do not use shielded cable unless you keep it under 120 mm.
>
> **The touch threshold does not change.** The wire adds to the resting baseline, which is measured automatically at every boot; the touch delta itself does not change. One value covers both configurations.
>
> If you snap the tab off and never rewire it, touch simply stops working. The board will not stutter, hang or misbehave — the pull-down resistor is on the main board for exactly that reason.

**Enclosure**

> The touch face on the top cap must be **flat and press directly onto the pad**, with **1.0 mm** of plastic over it (0.8–2.0 mm acceptable). This is not optional: a round cap that follows the tube leaves 17 mm of air over the pad and touch will not work at all. Leave no air gap larger than 0.3 mm — use closed-cell foam if the fit is loose. **No metal within 8 mm of the pad.** Never expose the copper.
>
> Keep all metal at least **10 mm** from the module's antenna end.
>
> The enclosure needs **≥180 cm² of external surface with passive venting.** A 30 mm × 220 mm tube gives 210 cm² and qualifies.
>
> **Diffuser: high-haze opal only** (≥85 % haze), **≥15 mm** from the LED plane. The specified 30 mm OD tube with the board 4.5 mm below the tube axis gives 15.9 mm. A clear or surface-frosted cover, or anything closer than about 10 mm, and you will see eleven distinct dots. That is the 60 LED/m pitch, not a fault.

**Recovery.** The ESP32-C3 uses **esptool and `--chip esp32c3 write_flash`**, not UF2 or BOOTSEL. `mpremote` over the native USB Serial/JTAG works the same. The UF2 instructions in the current README do not apply to this board.

**Provisioning.** One golden `config.py` for every unit. There is no per-board calibration step.
