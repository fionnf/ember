# ============================================================
#  config.py  —  Edit this file for EACH board individually
# ============================================================

# ── Board identity ──────────────────────────────────────────
BOARD_ID = "board_a"          # Change to "board_b" on the second Pico

# ── WiFi credentials ────────────────────────────────────────
# List all known networks — the board will try each in order until one connects.
WIFI_NETWORKS = [
    ("eth-iot",       "-6uWFXWia3Vb"),
    ("Gaydar",  "rainb0wLAN"),
    # ("iPhone",      "hotspotpass"),
]

# ── MQTT broker ─────────────────────────────────────────────
# Both boards must be able to reach this address.
# Free public option: "broker.hivemq.com"  (no auth, port 1883)
# Self-hosted (e.g. Raspberry Pi running Mosquitto): use its LAN/public IP
MQTT_BROKER   = "broker.hivemq.com"
MQTT_PORT     = 1883
MQTT_USER     = ""             # Leave empty if not required
MQTT_PASSWORD = ""             # Leave empty if not required

# Pick a unique prefix so you don't clash with other people on the public broker
MQTT_TOPIC_PREFIX = "picolight_lf26"   # ← change this to something personal

# ── LED strip ───────────────────────────────────────────────
LED_PIN        = 5             # GPIO pin connected to DIN of SK6812 strip
NUM_LEDS       = 10            # Number of LEDs on the strip
LED_BRIGHTNESS = 0.6           # 0.0 – 1.0  global brightness cap
# REVERSE_LEDS = True          # Uncomment on board_b if connected to the far end of the strip

# ── Capacitive touch sensors ────────────────────────────────
# List all GPIO pins that have a touch sensor attached.
# You can attach as many as you like — any sensor can trigger events.
TOUCH_PINS = [12]              # e.g. [14, 15]  for two sensors

# Touch detection threshold: lower = more sensitive.
# Raw ADC on the Pico reads charge/discharge time via a resistor.
# Typical resting value ~5–50; touch raises it significantly.
# Tune this per your setup (see README for calibration tip).
TOUCH_THRESHOLD   = 1        # counts above baseline = "touched"
HOLD_TIME_MS      = 3000        # ms held before it counts as a "long press" (toggle off/on)

# ── Colour palette ──────────────────────────────────────────
# Base warm-white RGBW values  (R, G, B, W)  — 0-255 each
# W channel carries most of the warmth; RGB adds tint.
BASE_WARM_WHITE = (0, 0, 0, 200)       # W channel only — pure warm white LED

# How much each impulse can shift hue (0.0 – 1.0 of the full palette)
HUE_SHIFT_MIN  = 0.20
HUE_SHIFT_MAX  = 0.50

# Palette of possible hue tints blended on top of warm white.
# Each entry is (R, G, B) normalised 0-255.  Order matters — adjacent
# entries will drift between each other smoothly.
TINT_PALETTE = [
    (255, 180,   0),   # 0  warm amber
    (255, 100,   0),   # 1  orange
    (255,   0,   0),   # 2  red
    (255,   0, 120),   # 3  hot pink
    (180,   0, 255),   # 4  purple
    (  0,   0, 255),   # 5  blue
    (  0, 180, 255),   # 6  cyan
    (  0, 255,  80),   # 7  green
    (180, 255,   0),   # 8  lime
    (255, 200,   0),   # 9  yellow
]

# Number of independent colour groups the strip is divided into
NUM_GROUPS = 3

# ── Animation parameters ─────────────────────────────────────
FADE_STEPS     = 60            # steps in a colour-change crossfade
FADE_DELAY_MS  = 16            # ms between fade steps  (~60 fps)
BREATHE_SPEED  = 0.0008        # how fast brightness "breathes" when idle
BREATHE_DEPTH  = 0.08          # how much brightness oscillates (0 = none)
IDLE_DRIFT_INTERVAL_S = 45     # seconds between autonomous gentle hue drifts

# ── WebREPL ─────────────────────────────────────────────────
# Allows wireless file editing and REPL access over WiFi.
# Connect at http://micropython.org/webrepl/ using the board's IP address.
WEBREPL_PASSWORD = "linked1"   # 4–9 characters

# ── Reconnect behaviour ─────────────────────────────────────
RECONNECT_DELAY_MS = 5000      # ms to wait before retrying WiFi / MQTT
