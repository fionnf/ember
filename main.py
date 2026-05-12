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
    WIFI_NETWORKS,
    MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD,
    MQTT_TOPIC_PREFIX,
    LED_PIN, NUM_LEDS, LED_BRIGHTNESS,
    TOUCH_PINS,
    FADE_DELAY_MS,
    RECONNECT_DELAY_MS,
    WEBREPL_PASSWORD,
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

    # Scan for visible SSIDs so we skip networks that aren't in range
    print("[wifi] scanning...")
    visible = set()
    try:
        for ap in wlan.scan():
            visible.add(ap[0].decode("utf-8", "ignore"))
    except Exception:
        pass  # scan failed — just try all networks anyway
    print(f"[wifi] visible networks: {visible}")

    for ssid, password in WIFI_NETWORKS:
        if visible and ssid not in visible:
            print(f"[wifi] {ssid} not in range, skipping")
            continue
        print(f"[wifi] trying {ssid}...")
        wlan.connect(ssid, password)
        deadline = utime.ticks_add(utime.ticks_ms(), 12_000)
        while not wlan.isconnected():
            if utime.ticks_diff(deadline, utime.ticks_ms()) <= 0:
                print(f"[wifi] {ssid} timed out")
                wlan.disconnect()
                utime.sleep_ms(500)
                break
            utime.sleep_ms(200)
        if wlan.isconnected():
            print(f"[wifi] connected to {ssid} — IP {wlan.ifconfig()[0]}")
            return wlan

    raise OSError("No known WiFi network found")


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

    # Connect WiFi — best-effort, continue offline if it fails
    wifi_ok = False
    try:
        connect_wifi()
        wifi_ok = True
    except OSError as e:
        print(f"[wifi] failed: {e} — running offline")

    # Start WebREPL if WiFi is up — allows wireless file editing
    if wifi_ok:
        try:
            import webrepl
            webrepl.start(password=WEBREPL_PASSWORD)
            print(f"[webrepl] started — connect at ws://<board-ip>:8266")
        except Exception as e:
            print(f"[webrepl] failed to start: {e}")

    # Connect MQTT — best-effort, continue without sync if it fails
    try:
        client = connect_mqtt()
    except Exception as e:
        print(f"[mqtt] connect failed: {e} — running standalone")

    # Calibrate touch baseline (nobody touching at boot)
    print("[touch] calibrating baseline...")
    touch.calibrate_all()
    print("[touch] ready")

    last_frame = utime.ticks_ms()
    _reconnect_at = utime.ticks_add(utime.ticks_ms(), RECONNECT_DELAY_MS)

    while True:
        now = utime.ticks_ms()

        # ── Reconnect MQTT in the background if disconnected ──
        if client is None and utime.ticks_diff(now, _reconnect_at) >= 0:
            try:
                client = connect_mqtt()
            except Exception as e:
                print(f"[mqtt] reconnect failed: {e}")
            _reconnect_at = utime.ticks_add(now, RECONNECT_DELAY_MS)

        # ── Poll MQTT for incoming messages ──
        if client is not None:
            try:
                client.check_msg()    # non-blocking poll
            except Exception as e:
                print(f"[mqtt] check_msg error: {e}")
                client = None

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

        utime.sleep_ms(1)


# ── Run ──────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
