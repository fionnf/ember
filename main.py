# ============================================================
#  main.py  —  Entry point, runs on BOTH boards identically
#  Only config.py differs between boards.
# ============================================================

import time
import utime
import ujson
import network
from umqtt.simple import MQTTClient

from config import (
    BOARD_ID,
    WIFI_SSID, WIFI_PASSWORD,
    MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD,
    MQTT_TOPIC_PREFIX,
    LED_PIN, NUM_LEDS, LED_BRIGHTNESS,
    TOUCH_PINS,
    FADE_DELAY_MS,
    RECONNECT_DELAY_MS,
)
from sk6812 import SK6812
from touch   import TouchManager
from colour  import ColourEngine

# ── MQTT topics ─────────────────────────────────────────────
# All boards publish to and subscribe from the same shared topic.
# They ignore messages that carry their own BOARD_ID (echo prevention).
TOPIC_EVENTS = (MQTT_TOPIC_PREFIX + "/events").encode()

# ── Module-level objects ─────────────────────────────────────
strip  = SK6812(pin=LED_PIN, num_leds=NUM_LEDS, brightness=LED_BRIGHTNESS)
touch  = TouchManager(TOUCH_PINS)
engine = ColourEngine()
client = None   # MQTTClient, initialised after WiFi

# ── WiFi ─────────────────────────────────────────────────────

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return wlan
    print(f"[wifi] connecting to {WIFI_SSID}...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    deadline = utime.ticks_add(utime.ticks_ms(), 20_000)
    while not wlan.isconnected():
        if utime.ticks_diff(deadline, utime.ticks_ms()) <= 0:
            raise OSError("WiFi timeout")
        utime.sleep_ms(200)
    print(f"[wifi] connected — IP {wlan.ifconfig()[0]}")
    return wlan


# ── MQTT ─────────────────────────────────────────────────────

def on_message(topic, msg):
    """Called by the MQTT library when a message arrives."""
    try:
        data = ujson.loads(msg)
    except Exception:
        return

    # Ignore our own echoed messages
    if data.get("from") == BOARD_ID:
        return

    print(f"[mqtt] recv: {data}")
    pos = data.get("pos")
    on  = data.get("on")

    if on is not None:
        engine.set_power(bool(on))
    if pos is not None and on is not False:
        engine.force_colour(float(pos))


def connect_mqtt() -> MQTTClient:
    client_id = (BOARD_ID + "_" + MQTT_TOPIC_PREFIX).encode()
    c = MQTTClient(
        client_id,
        MQTT_BROKER,
        port=MQTT_PORT,
        user=MQTT_USER.encode() if MQTT_USER else None,
        password=MQTT_PASSWORD.encode() if MQTT_PASSWORD else None,
        keepalive=30,
    )
    c.set_callback(on_message)
    c.connect()
    c.subscribe(TOPIC_EVENTS)
    print(f"[mqtt] connected to {MQTT_BROKER}, subscribed to {TOPIC_EVENTS}")
    return c


def publish_event(payload: dict):
    """Publish a colour/power event to the shared topic."""
    global client
    if client is None:
        return
    payload["from"] = BOARD_ID
    try:
        client.publish(TOPIC_EVENTS, ujson.dumps(payload))
    except Exception as e:
        print(f"[mqtt] publish error: {e}")
        client = None   # trigger reconnect


# ── Startup sequence ─────────────────────────────────────────

def startup_animation():
    """Brief warm-white fade-in to show the strip is alive."""
    for step in range(30):
        t = step / 29
        w = int(200 * t)
        r = int(255 * t)
        g = int(140 * t)
        b = int(40 * t)
        strip.set_all(r, g, b, w)
        strip.show()
        utime.sleep_ms(20)


# ── Main loop ────────────────────────────────────────────────

def main():
    global client

    # Initial LED feedback
    startup_animation()

    # Connect WiFi (blocking, with retry)
    while True:
        try:
            connect_wifi()
            break
        except OSError as e:
            print(f"[wifi] failed: {e}, retrying...")
            utime.sleep_ms(RECONNECT_DELAY_MS)

    # Connect MQTT (blocking, with retry)
    while True:
        try:
            client = connect_mqtt()
            break
        except Exception as e:
            print(f"[mqtt] connect failed: {e}, retrying...")
            utime.sleep_ms(RECONNECT_DELAY_MS)

    # Calibrate touch baseline (nobody touching at boot)
    print("[touch] calibrating baseline...")
    touch.calibrate_all()
    print("[touch] ready")

    last_frame = utime.ticks_ms()

    while True:
        now = utime.ticks_ms()

        # ── Reconnect MQTT if disconnected ──
        if client is None:
            try:
                client = connect_mqtt()
            except Exception as e:
                print(f"[mqtt] reconnect failed: {e}")
                utime.sleep_ms(RECONNECT_DELAY_MS)
                continue

        # ── Poll MQTT for incoming messages ──
        try:
            client.check_msg()    # non-blocking poll
        except Exception as e:
            print(f"[mqtt] check_msg error: {e}")
            client = None
            continue

        # ── Poll touch sensors ──
        event = touch.update()

        if event == "tap":
            print("[touch] tap")
            engine.impulse()
            publish_event(engine.get_event_payload())

        elif event == "hold":
            print("[touch] hold → toggle power")
            engine.toggle_power()
            publish_event(engine.get_event_payload())

        # ── Render frame at target FPS ──
        if utime.ticks_diff(now, last_frame) >= FADE_DELAY_MS:
            engine.tick(strip)
            last_frame = now

        # Tiny yield to keep the MQTT stack healthy
        utime.sleep_ms(1)


# ── Run ──────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
