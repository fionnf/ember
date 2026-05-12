# Pico W Dual LED Sync — Setup Guide

Two Pico W boards that keep their SK6812 RGBW strips in sync via MQTT.
Touch one → both shift colour across independent LED groups.
Long-press → both fade off.  Long-press again → both fade back on.

---

## Files

| File | Purpose |
|---|---|
| `config.py` | **Edit per board** — WiFi networks, MQTT, LED pin, touch pins, colour palette |
| `main.py` | Main firmware — identical on both boards |
| `sk6812.py` | PIO-based SK6812 RGBW driver |
| `touch.py` | Capacitive touch detection |
| `colour.py` | Organic colour engine (groups, palette, fades, breathing) |
| `hardware_test.py` | Standalone wiring test — no WiFi/MQTT needed |
| `mqtt_smoke.py` | WiFi + MQTT smoke test for a single board |

---

## Hardware Wiring

### SK6812 strip
```
Pico W                SK6812 strip
GPIO (LED_PIN) ──── DIN   ← data flows this way →   DOUT
3.3V or 5V     ──── +5V / VCC   (use 5V for brighter strips)
GND            ──── GND
```
> **Important:** data flows one direction only — from DIN to DOUT through each LED.
> Both boards must inject their data wire into a **DIN** pad, not DOUT.
> A 300–470 Ω series resistor on the DIN line prevents ringing.
> For more than ~10 LEDs, power the strip from its own 5V supply (not the Pico).

#### Board B — connecting to the far end of the strip
If board B connects via a connector at the far end of the strip, that connector
is DOUT and **will not work**. Run a separate data wire from board B's GPIO pin
back to the DIN end of its LED section, or flip the connector direction.
To reverse the LED group order in software, uncomment in `config.py`:
```python
REVERSE_LEDS = True
```

### Capacitive touch sensor (per sensor)
```
Pico W               Touch pad
GPIO (TOUCH_PIN) ──┬── bare copper pad / foil
                   └── 1 MΩ resistor ── GND
```
No external ADC needed. The Pico measures charge/discharge time directly.
Multiple sensors can be added — list all GPIO pins in `TOUCH_PINS`.

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

### 3. Enable WebREPL (one-time, per board)
While connected via USB in Thonny's shell, run:
```python
import webrepl_setup
```
Follow the prompts and set the password to match `WEBREPL_PASSWORD` in `config.py`
(default: `linked1`). This only needs to be done once — the setting persists.

### 4. Upload all `.py` files to both Picos
Using Thonny (File → Upload to /) or:
```bash
mpremote connect /dev/ttyACM0 cp config.py main.py sk6812.py touch.py colour.py :
```

### 5. Edit `config.py` on each board
Minimum changes:
```python
BOARD_ID   = "board_a"               # "board_b" on the second Pico
WIFI_NETWORKS = [
    ("your_network",  "your_password"),
    ("backup_network", "password2"),  # optional extras
]
MQTT_TOPIC_PREFIX = "picolight_abc123"   # same on BOTH boards
LED_PIN    = 5                        # GPIO pin connected to strip DIN
NUM_LEDS   = 10                       # number of LEDs on your strip
TOUCH_PINS = [12]                     # GPIO(s) with touch sensor(s)
```

### 6. MQTT broker options

**Option A — free public broker (easiest)**
```python
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT   = 1883
```
No account needed. Change `MQTT_TOPIC_PREFIX` to something personal so you
don't collide with other users on the public broker.

**Option B — self-hosted Mosquitto**
```bash
sudo apt install mosquitto mosquitto-clients
sudo systemctl enable mosquitto
```
Set `MQTT_BROKER` to that machine's LAN IP or public domain.

---

## Wireless File Editing (WebREPL)

Once a board is running on WiFi you can edit files and use the REPL without
a USB cable.

1. At boot, the board prints its IP:
   ```
   [wifi] connected to eth-iot — IP 192.168.1.42
   [webrepl] started — connect at ws://192.168.1.42:8266
   ```
2. Open **http://micropython.org/webrepl/** in a browser
3. Enter `ws://192.168.x.x:8266` and the password from `WEBREPL_PASSWORD`
4. You now have a live REPL — drag and drop `.py` files onto the page to upload them

> **Tip:** assign the board a static IP on your router (by MAC address) so the
> address never changes.

---

## Multiple WiFi Networks

`config.py` supports a list of networks — the board scans what's visible and
tries them in order:
```python
WIFI_NETWORKS = [
    ("home_wifi",    "password1"),
    ("office_wifi",  "password2"),
    ("iPhone",       "hotspotpass"),
]
```
Networks not currently in range are skipped automatically.

---

## LED Groups

The strip is divided into `NUM_GROUPS` independent sections (default: 3).
Each tap gives every group its own random colour shift and warm-white intensity
(60–100%), so the strip evolves organically rather than as a single block.

```python
NUM_GROUPS = 3   # change to 4 for more granularity
```

---

## Touch Calibration

If touches aren't detected or there are false triggers:

1. Open a REPL and watch the `[touch]` output at boot
2. Adjust `TOUCH_THRESHOLD` in `config.py`:
   - **Increase** if there are false triggers
   - **Decrease** if real touches are missed
3. For long wires to the pad, try a smaller pull-down (e.g. 470 kΩ instead of 1 MΩ)

---

## Customising the Colours

Everything visual lives in `config.py`:

### Base warm white
```python
BASE_WARM_WHITE = (0, 0, 0, 200)   # R, G, B, W — pure warm white LED
```

### Tint palette
`TINT_PALETTE` is the list of colours the engine drifts between on each tap.
The current palette runs: amber → orange → red → pink → purple → blue → cyan → green → lime → yellow.
Add, remove, or reorder entries freely.

### Hue shift per tap
```python
HUE_SHIFT_MIN = 0.20   # minimum jump along the palette
HUE_SHIFT_MAX = 0.50   # maximum jump
```

### Animation
```python
BREATHE_SPEED = 0.0008        # higher = faster pulse
BREATHE_DEPTH = 0.08          # higher = more visible pulse (0 = flat)
FADE_STEPS    = 60            # more steps = slower, smoother fade
IDLE_DRIFT_INTERVAL_S = 45    # autonomous colour drift every N seconds
```

---

## How It Works

```
Touch event
    │
    ▼
ColourEngine.impulse()
 — each LED group gets its own random palette shift
 — each group gets a random warm-white intensity (60–100%)
 — all groups start fading simultaneously
    │
    ▼
MQTT publish → broker → remote board subscribes
    │
    ▼
Remote board: ColourEngine.force_colour(pos)
 — mirrors the palette position with a small per-group jitter
 — starts its own crossfades
```

Both boards share a float `palette_pos` (0.0–1.0) per group as state.
At position 0 the W channel is full and RGB is off (pure warm white).
At position 1 the RGB channels are fully saturated and W fades to zero.

Long-press sends `{"on": false}` over MQTT — both boards fade off together.

---

## Hardware Test

To verify wiring without needing WiFi or any other project files:

1. Flash `hardware_test.py` to the Pico as `main.py`
2. It cycles the strip through RED → GREEN → BLUE → WHITE → WARM WHITE → OFF
3. Then enters a touch test loop — tap or hold the sensor and watch the output

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Board B LEDs don't light up | Connected to DOUT not DIN | Run data wire to DIN end of strip |
| Strip shows wrong colours | Wrong byte order | This strip uses GRBW — confirmed in `sk6812.py` |
| Groups appear reversed on board B | Far-end connector reverses order | Uncomment `REVERSE_LEDS = True` in config.py |
| Touch never fires | Threshold too high | Lower `TOUCH_THRESHOLD` |
| Touch fires constantly | No pull-down resistor | Add 1 MΩ between GPIO and GND |
| One board doesn't sync | Different `MQTT_TOPIC_PREFIX` | Must be identical on both boards |
| WebREPL won't connect | `webrepl_setup` not run | Run `import webrepl_setup` once via USB |
| Lags / drops messages | Public broker busy | Switch to self-hosted Mosquitto |
