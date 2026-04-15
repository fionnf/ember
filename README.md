# Pico W Dual LED Sync — Setup Guide

Two Pico W boards on different WiFi networks that keep their SK6812 RGBW
strips in perfect sync via MQTT.  Touch one → both gently shift colour.
Long-press → both go dark.  Long-press again → both wake up.

---

## Files

| File | Purpose |
|---|---|
| `config.py` | **Edit per board** — WiFi, MQTT, LED pin, touch pins, colour palette |
| `main.py` | Main firmware — identical on both boards |
| `sk6812.py` | PIO-based SK6812 RGBW driver |
| `touch.py` | Capacitive touch detection |
| `colour.py` | Organic colour engine (palette, fades, breathing) |
| `mqtt_smoke.py` | WiFi + MQTT smoke test for a single board |

---

## Hardware Wiring

### SK6812 strip
```
Pico W                SK6812 strip
GPIO (LED_PIN) ──── DIN
3.3V or 5V   ──── +5V / VCC   (use 5V for brighter strips)
GND          ──── GND
```
> A 300–470 Ω series resistor on the DIN line prevents ringing.
> For more than ~10 LEDs, power the strip from its own 5V supply (not the Pico).

### Capacitive touch sensor (per sensor)
```
Pico W               Touch pad
GPIO (TOUCH_PIN) ──┬── bare copper pad / foil
                   └── 1 MΩ resistor ── GND
```
No external ADC needed.  The Pico measures charge/discharge time directly.
Multiple sensors can be added — list all their GPIO pins in `TOUCH_PINS`.

---

## First-Time Setup

### 1. Flash MicroPython
Download the latest **Pico W** MicroPython UF2 from
https://micropython.org/download/RPI_PICO_W/ and flash it the usual way
(hold BOOTSEL, drag UF2).

### 2. Install `umqtt.simple`
Open a REPL (Thonny or mpremote) and run:
```python
import mip
mip.install("umqtt.simple")
```

### 3. Upload all five `.py` files to both Picos
Using Thonny (File → Upload) or:
```bash
mpremote connect /dev/ttyACM0 cp config.py main.py sk6812.py touch.py colour.py :
```

### 4. Edit `config.py` on each board
Minimum changes:
```python
BOARD_ID      = "board_a"          # "board_b" on the second Pico
WIFI_SSID     = "your_network"
WIFI_PASSWORD = "your_password"
MQTT_TOPIC_PREFIX = "picolight_abc123"   # same value on BOTH boards
LED_PIN       = 0                  # GPIO pin connected to strip DIN
NUM_LEDS      = 8                  # length of your strip
TOUCH_PINS    = [14]               # GPIO(s) with touch sensor(s)
```

### 5. MQTT broker options

**Option A — free public broker (easiest)**
```python
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT   = 1883
```
No account needed.  Both boards just need internet access.
Change `MQTT_TOPIC_PREFIX` to something random/personal so you don't
collide with other users.

**Option B — self-hosted Mosquitto**
Run on any always-on machine (a Pi at home works):
```bash
sudo apt install mosquitto mosquitto-clients
sudo systemctl enable mosquitto
```
Then set `MQTT_BROKER` to that machine's public IP/domain.

---

## Touch Calibration

If touches aren't detected (or there are false triggers):

1. Open a REPL while the board is running
2. Temporarily add some print statements to `touch.py → _measure_raw()`
   to see the raw counts at rest vs. touched
3. Adjust `TOUCH_THRESHOLD` in `config.py` accordingly:
   - Increase if there are false triggers
   - Decrease if it misses real touches
4. For very long wires to the pad, you may need a smaller pull-down
   resistor (e.g., 470 kΩ instead of 1 MΩ)

---

## Quick WiFi + MQTT smoke test

If you only have one Pico right now, use `mqtt_smoke.py` to confirm the board
can join WiFi and publish to the cloud broker.

### What it does

- connects to the WiFi settings in `config.py`
- connects to the MQTT broker in `config.py`
- publishes a **retained** JSON message to:

```text
<MQTT_TOPIC_PREFIX>/smoke
```

- sends a heartbeat every 15 seconds

### How to use it

1. Upload `mqtt_smoke.py` to the Pico.
2. If you want it to auto-run on boot, temporarily rename it to `main.py`
   on that board.
3. Open a cloud MQTT viewer such as:
   - HiveMQ WebSocket client
   - MQTT Explorer
   - `mosquitto_sub`
4. Subscribe to:

```text
<MQTT_TOPIC_PREFIX>/smoke
```

You should see a retained `boot` message first, then periodic `heartbeat`
messages.

### Example subscribe command

```bash
mosquitto_sub -h broker.hivemq.com -p 1883 -t 'picolight_lf26/smoke' -v
```

If you change `MQTT_TOPIC_PREFIX` in `config.py`, use that value in the
subscribe topic.

---

## Customising the Colours

Everything visual lives in `config.py`:

### Change the base warm white
```python
BASE_WARM_WHITE = (255, 160, 60, 220)   # R, G, B, W
```
- Lower `W` for less warmth, increase `R`/`G`/`B` for more colour
- Pure cool white: `(0, 0, 0, 255)`

### Change the tint palette
`TINT_PALETTE` is a list of RGB colours the engine drifts between.
Position 0 in the list = most "towards warm white",
position N = most saturated tint.  Add, remove, or reorder freely.

### Change how far a touch shifts the colour
```python
HUE_SHIFT_MIN = 0.02    # tiny nudge
HUE_SHIFT_MAX = 0.20    # big jump
```

### Breathing / animation speed
```python
BREATHE_SPEED = 0.0008   # higher = faster pulse
BREATHE_DEPTH = 0.08     # higher = more visible pulse (0 = none)
FADE_STEPS    = 60       # more steps = slower, smoother fade
IDLE_DRIFT_INTERVAL_S = 45   # autonomous drift every N seconds
```

---

## How It Works

```
Touch event
    │
    ▼
ColourEngine.impulse()
 — picks a nearby palette position at random
 — starts a crossfade to the new colour
    │
    ▼
MQTT publish → broker → remote board subscribes
    │
    ▼
Remote board: ColourEngine.force_colour(pos)
 — mirrors the same palette position
 — starts its own crossfade
```

Both boards store a float `palette_pos` (0.0–1.0) as shared state.
Impulses shift it left/right by a small random amount, so colours
always evolve organically rather than jumping to fixed presets.

Long-press sends `{"on": false}` over MQTT, which both boards honour.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Strip flickers or wrong colours | Wrong byte order | SK6812 uses GRBW — driver handles this, but check your strip datasheet |
| Touch never fires | Threshold too high | Lower `TOUCH_THRESHOLD` |
| Touch fires constantly | No pull-down resistor | Add 1 MΩ between GPIO and GND |
| One board doesn't sync | Different `MQTT_TOPIC_PREFIX` | Must be identical on both |
| Lags / drops | Public broker busy | Switch to self-hosted Mosquitto |
