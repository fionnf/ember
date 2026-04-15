# ============================================================
#  config.py  —  Edit this file for EACH board individually
# ============================================================

# ── Board identity ──────────────────────────────────────────
BOARD_ID = "board_a"          # Change to "board_b" on the second Pico

# ── WiFi credentials ────────────────────────────────────────
WIFI_SSID     = "your_wifi_name"
WIFI_PASSWORD = "your_wifi_password"

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
LED_PIN        = 0             # GPIO pin connected to DIN of SK6812 strip
NUM_LEDS       = 8             # Number of LEDs on the strip
LED_BRIGHTNESS = 0.6           # 0.0 – 1.0  global brightness cap

# ── Capacitive touch sensors ────────────────────────────────
# List all GPIO pins that have a touch sensor attached.
# You can attach as many as you like — any sensor can trigger events.
TOUCH_PINS = [14]              # e.g. [14, 15]  for two sensors

# Touch detection threshold: lower = more sensitive.
# Raw ADC on the Pico reads charge/discharge time via a resistor.
# Typical resting value ~5–50; touch raises it significantly.
# Tune this per your setup (see README for calibration tip).
TOUCH_THRESHOLD   = 400        # counts above baseline = "touched"
HOLD_TIME_MS      = 3000        # ms held before it counts as a "long press" (toggle off/on)

# ── Colour palette ──────────────────────────────────────────
# Base warm-white RGBW values  (R, G, B, W)  — 0-255 each
# W channel carries most of the warmth; RGB adds tint.
BASE_WARM_WHITE = (255, 160, 60, 220)

# How much each impulse can shift hue (0.0 – 1.0 of the full palette)
HUE_SHIFT_MIN  = 0.02
HUE_SHIFT_MAX  = 0.20

# Palette of possible hue tints blended on top of warm white.
# Each entry is (R, G, B) normalised 0-255.  Order matters — adjacent
# entries will drift between each other smoothly.
TINT_PALETTE = [
    (255, 160,  60),   # 0  warm amber
    (255, 200, 100),   # 1  golden
    (255, 240, 200),   # 2  soft white
    (200, 220, 255),   # 3  cool white / daylight
    (160, 180, 255),   # 4  blue-white
    (180, 140, 255),   # 5  lavender
    (120, 100, 220),   # 6  purple
    (100, 220, 180),   # 7  aqua-green
    (140, 255, 160),   # 8  soft green
    (255, 180, 120),   # 9  peach
]

# ── Animation parameters ─────────────────────────────────────
FADE_STEPS     = 60            # steps in a colour-change crossfade
FADE_DELAY_MS  = 16            # ms between fade steps  (~60 fps)
BREATHE_SPEED  = 0.0008        # how fast brightness "breathes" when idle
BREATHE_DEPTH  = 0.08          # how much brightness oscillates (0 = none)
IDLE_DRIFT_INTERVAL_S = 45     # seconds between autonomous gentle hue drifts

# ── Reconnect behaviour ─────────────────────────────────────
RECONNECT_DELAY_MS = 5000      # ms to wait before retrying WiFi / MQTT
