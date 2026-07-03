# Linked Friend Lights

Two Raspberry Pi Pico W boards keeping their SK6812 RGBW LED strips in sync over MQTT. Touch one lamp and both shift colour together. Control everything from a web app that works on any phone or browser.

---

## Overview

```
[Web UI] ──MQTT (WebSocket)── [board_a / BOSS] ──sync── [board_b / follower]
                                SK6812 strip               SK6812 strip
```

One board (`board_a`, display name **FF**) is the BOSS; the other (`board_b`, **LS**) is the follower. Both subscribe to the same MQTT topic and keep their strips in sync. The web UI publishes JSON commands to the same topic and reflects live state from both boards.

---

## Hardware

| Part | Notes |
|------|-------|
| Raspberry Pi Pico W (×2) | The W variant — needs WiFi |
| SK6812 RGBW LED strip | 10 LEDs per board, GRBW byte order |
| Data pin | GPIO 5 |
| 300–470 Ω resistor | Series on DIN — prevents ringing |
| 5 V power supply | USB or direct to strip |

### Wiring

```
Pico W GPIO 5 ──[330Ω]──── DIN ────────────── DOUT
5 V / 3.3 V   ─────────── VCC
GND           ─────────── GND

Pico W TOUCH_PIN ──┬──── copper pad / foil
                   └─[1MΩ]── GND
```

> Data flows DIN → DOUT; connect the board's data wire to the **DIN** end of the strip.

If board B connects via the far end (DOUT side), set `REVERSE_LEDS = True` in `config.py` to flip group order in software.

---

## Firmware

### Files

| File | OTA-updated | Purpose |
|------|-------------|---------|
| `boot.py` | Never | OTA bootstrap — downloads firmware from GitHub on every boot |
| `main.py` | Yes | Main loop: WiFi, MQTT, touch, alarms, BOSS sync |
| `colour.py` | Yes | Colour engine: groups, fades, breathing, drift |
| `sk6812.py` | Yes | PIO-based SK6812 RGBW driver |
| `touch.py` | Yes | Capacitive touch detection |
| `config.py` | Never | Per-board constants (never overwritten by OTA) |

### OTA Updates

`boot.py` runs before `main.py` on every boot. It connects to WiFi and downloads the latest `main.py`, `colour.py`, `sk6812.py`, and `touch.py` from the `master` branch of this repo. `config.py` and `boot.py` are never touched. If WiFi is unavailable the board boots from whatever is already on flash.

To update both boards: commit and push to `master`, then click **↺ Reboot Both Boards** in the Settings panel.

### Configuration (`config.py`)

```python
BOARD_ID   = "board_a"    # "board_b" on the second Pico
BOSS       = True         # True on board_a only

NUM_LEDS       = 10
LED_PIN        = 5
REVERSE_LEDS   = False

NUM_GROUPS     = 3
GROUP_MIN_LEDS = 1
GROUP_MAX_LEDS = 8

LED_BRIGHTNESS = 0.6
FADE_STEPS     = 60       # steps per colour transition (~1 s at 60 Hz)
BREATHE_SPEED  = 0.0008   # radians/ms
BREATHE_DEPTH  = 0.04     # ±4% brightness oscillation

IDLE_DRIFT_INTERVAL_S = 45

MQTT_BROKER        = "broker.hivemq.com"
MQTT_PORT          = 1883
MQTT_TOPIC_PREFIX  = "picolight_lf26"

WIFI_NETWORKS = [
    ("YourSSID", "YourPassword"),
]
```

### MQTT

- **Broker:** `broker.hivemq.com:1883` (TCP on device) / `:8884` WSS (web)
- **Events topic:** `picolight_lf26/events`
- **Scenes topic:** `picolight_lf26/scenes` (retained)
- **Alarms topic:** `picolight_lf26/alarms` (retained)

All messages are JSON with a `from` field for echo suppression.

### Colour Engine (`colour.py`)

The `ColourEngine` class manages per-group colour state:

- **Palette position** (`pos`, float 0.0–1.0): maps into a 30-stop hue palette blended with warm white. `0.0` = pure warm white (W channel only); higher values = saturated hues with W fading out.
- **Groups**: the strip is split into 1–N independent colour zones. Each group has a `pos` (hue) and a `w` (warm-white level). Group sizes are stored separately.
- **Fade**: each group independently crossfades to its target over `FADE_STEPS` ticks.
- **Breathing**: a per-group sine oscillator adds a slow ±4% brightness pulse with staggered phases.
- **Drift**: optional autonomous colour drift — subtle hue nudges and group-size shifts every `IDLE_DRIFT_INTERVAL_S` seconds. Disabled by default in the web UI (`driftEnabled = false`).
- **Power**: soft on/off with an ~800 ms fade.

### BOSS / Follower Sync

When the BOSS's physical touch sensor fires, it runs `ColourEngine.impulse()` (random colour change), then publishes its new state with `"sync": true`. The follower applies the same groups with a fast fade (`SYNC_FADE_STEPS`) so both strips match immediately.

Every 60 s the BOSS publishes its state with `"sync": true` as a drift-correction heartbeat. The follower applies it with a slow 300-step fade so re-alignment is invisible.

### Alarms

Alarms are stored as JSON in `alarms.json` on each board's flash and also kept in a retained MQTT message. On each main-loop tick the board checks the current UTC time against active alarms and executes:

- **Sunrise** (`type: "sunrise"`): ramps brightness from 0 to `alarm.brightness` over `duration_min` minutes.
- **Bedtime** (`type: "sunset"`): fades brightness to 0 over `duration_min` minutes.

### WiFi Watchdog

If the board loses WiFi for more than 10 minutes (`WIFI_OFFLINE_REBOOT_MS = 600000`) it reboots to reconnect and pick up any OTA update. Known networks are stored in `wifi_networks.json` on flash and tried in order.

### State Persistence

On/off state is written to `state.json` after each power toggle and restored on boot before connecting to MQTT.

---

## Web UI

`index.html` at the repo root is served via **GitHub Pages**. It connects to the HiveMQ broker over WebSockets. No install required — open it in any browser.

### Controls

| Control | What it does |
|---------|-------------|
| **Power** | Soft on/off; state reflected in board pills immediately |
| **Tap** | Random colour change (same as physically touching the lamp) |
| **Warm White** | Resets all groups to `pos=0.0, w=1.0` (pure warm white) |
| **Brightness** | Global brightness 0–100% |
| **Fade Speed** | Colour transition duration (~0.3 s–10 s) |
| **Send to** | Target Both boards / FF only / LS only |

### Strip preview

The top card shows the RGBW strip in real time. Click the small divider cells below the strip to split or merge colour groups.

### Groups

Each group gets a numbered handle on the palette bar — drag it along the hue gradient to pick a colour. The **Warm White** slider below each group blends in warm white independently.

### Alarms

Create sunrise/bedtime alarms per board with day-of-week selection, duration, and target brightness. Alarms are published to a retained MQTT topic so boards receive them after a reboot even if the web app is not open.

### Scenes

Save and load complete lamp states (colours, group layout, brightness, fade speed). Stored in `localStorage`. Built-in scene: **Static Rainbow** (one LED per group, evenly spaced across the hue palette).

### Settings panel

| Field | Default | Description |
|-------|---------|-------------|
| WebSocket URL | `wss://broker.hivemq.com:8884/mqtt` | MQTT broker |
| Topic Prefix | `picolight_lf26` | Must match boards |
| LEDs | `10` | LEDs per strip |
| Groups | `3` | Initial group count |

Also: **Add WiFi Network** (sends credentials to both boards over MQTT), **↺ Reboot Both Boards** (triggers OTA update).

### Board presence pills

The two pills (FF / LS) at the top right show each board's status:

- **Green (online)** — board seen within 65 s and lights are on
- **Amber (standby)** — board seen within 65 s but lights are off
- **No highlight (offline)** — no message received within 65 s

---

## MQTT Message Reference

### State update (web → boards)

```json
{
  "from": "web_app",
  "groups": [
    {"pos": 0.0,  "w": 1.0, "size": 4},
    {"pos": 0.35, "w": 0.8, "size": 3},
    {"pos": 0.7,  "w": 0.6, "size": 3}
  ],
  "on": true,
  "brightness": 0.6,
  "fade_steps": 60,
  "drift_enabled": false,
  "drift_interval": 45
}
```

### Heartbeat (board → all)

```json
{"from": "board_a", "heartbeat": true, "fw": "1.4.2"}
```

### Impulse / sync (board → board)

```json
{
  "from": "board_a",
  "groups": [...],
  "on": true,
  "brightness": 0.6,
  "fade_steps": 60,
  "drift_enabled": false,
  "drift_interval": 45,
  "sync": true
}
```

### Alarms (retained on `/alarms`)

```json
[
  {
    "enabled": true,
    "type": "sunrise",
    "hour": 7,
    "minute": 0,
    "duration_min": 30,
    "brightness": 1.0,
    "days": [0, 1, 2, 3, 4],
    "boards": ["board_a", "board_b"]
  }
]
```

`days`: 0=Monday … 6=Sunday. All times are **UTC**.

---

## First-Time Setup

1. **Flash MicroPython** — download the Pico W UF2 from micropython.org, hold BOOTSEL, drag it on.

2. **Install umqtt** (in Thonny shell or `mpremote`):
   ```python
   import mip
   mip.install("umqtt.simple")
   ```

3. **Upload files** (only once):
   ```bash
   mpremote connect /dev/ttyACM0 cp boot.py config.py :
   ```
   Create `wifi_networks.json` on the board:
   ```json
   [{"ssid": "YourNetwork", "password": "YourPassword"}]
   ```

4. **Edit `config.py`** — set `BOARD_ID`, `BOSS`, `NUM_LEDS`, `LED_PIN`, `MQTT_TOPIC_PREFIX`.

5. **Reboot** — `boot.py` downloads `main.py`, `colour.py`, `sk6812.py`, `touch.py` from master and starts.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Board B LEDs don't light | Connected to DOUT | Run wire to DIN end |
| Wrong colours | Byte-order mismatch | SK6812 uses GRBW — check `sk6812.py` |
| Groups reversed on board B | Far-end connector | `REVERSE_LEDS = True` in `config.py` |
| Touch never fires | Threshold too high | Lower `TOUCH_THRESHOLD` in `config.py` |
| Touch fires constantly | Missing pull-down | 1 MΩ between GPIO and GND |
| Boards not syncing | Different topic prefix | `MQTT_TOPIC_PREFIX` must match on both |
| Board reboots after ~10 min offline | WiFi watchdog | Expected; board reconnects and checks OTA |
| Sunrise alarm not firing | NTP not synced | Board needs WiFi at boot; check `[ntp]` log |
| OTA not updating | `boot.py` not on board | Flash `boot.py` manually once via USB |

---

## Project Structure

```
linked_friend_lights/
├── index.html              # GitHub Pages web UI (copy of web_app/index.html)
├── web_app/
│   └── index.html          # Web UI source
├── main.py                 # Firmware — main loop (OTA-fetched)
├── colour.py               # Firmware — colour engine (OTA-fetched)
├── sk6812.py               # Firmware — PIO LED driver (OTA-fetched)
├── touch.py                # Firmware — capacitive touch (OTA-fetched)
├── boot.py                 # OTA bootstrap (deployed manually, never overwritten)
├── config.py               # Per-board hardware config (never overwritten)
└── README.md
```

---

Personal project — no license.
