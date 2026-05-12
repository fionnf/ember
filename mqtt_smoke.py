"""Standalone Pico W smoke test for WiFi + MQTT.

Edit the constants below directly, upload this file to a Pico W, and run it
as `main.py` or from the REPL / Thonny. It publishes a retained boot message
and then periodic heartbeat updates to a dedicated MQTT topic so you can
verify the board from another device (MQTT Explorer, HiveMQ WebSocket client,
mosquitto_sub, etc.).
"""

try:
    import ujson
except ImportError:  # desktop fallback
    import json as ujson

try:
    import network
except ImportError:  # desktop fallback
    class _MissingPin:
        pass

    class _MissingWLAN:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("network module is unavailable; run this on MicroPython/Pico W")

        def active(self, *_args, **_kwargs):
            raise RuntimeError("network module is unavailable; run this on MicroPython/Pico W")

        def isconnected(self):
            raise RuntimeError("network module is unavailable; run this on MicroPython/Pico W")

        def connect(self, *_args, **_kwargs):
            raise RuntimeError("network module is unavailable; run this on MicroPython/Pico W")

        def ifconfig(self):
            return ("0.0.0.0", "0.0.0.0", "0.0.0.0", "0.0.0.0")

        def scan(self):
            return []

    class _NetworkShim:
        STA_IF = 0
        WLAN = _MissingWLAN

    network = _NetworkShim()

try:
    import utime
except ImportError:  # desktop fallback
    import time as _time

    class _UTimeShim:
        @staticmethod
        def ticks_ms():
            return int(_time.monotonic() * 1000)

        @staticmethod
        def ticks_add(a, b):
            return a + b

        @staticmethod
        def ticks_diff(a, b):
            return a - b

        @staticmethod
        def sleep_ms(ms):
            _time.sleep(ms / 1000)

    utime = _UTimeShim()

try:
    from umqtt.simple import MQTTClient
except ImportError:  # desktop fallback
    class MQTTClient:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("umqtt.simple is unavailable; run this on MicroPython/Pico W")

        def connect(self):
            raise RuntimeError("umqtt.simple is unavailable; run this on MicroPython/Pico W")

        def publish(self, *_args, **_kwargs):
            raise RuntimeError("umqtt.simple is unavailable; run this on MicroPython/Pico W")




# ============================================================
# Standalone configuration — edit these values directly.
# ============================================================
BOARD_ID = "smoke_test_board"
WIFI_SSID = "eth-iot"
WIFI_PASSWORD = "-6uWFXWia3Vb"

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_USER = ""
MQTT_PASSWORD = ""

# Keep this unique so your messages do not collide with other users.
MQTT_TOPIC_PREFIX = "picolight_smoke_test"


TOPIC_SMOKE = (MQTT_TOPIC_PREFIX + "/smoke").encode()
HEARTBEAT_MS = 15_000
WIFI_RETRY_MS = 5_000
MQTT_RETRY_MS = 5_000


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    print("[wifi] MAC:", ":".join("{:02x}".format(b) for b in wlan.config("mac")))
    print("[wifi] scanning for visible networks...")

    try:
        nets = wlan.scan()
        found = False
        for net in nets:
            ssid = net[0].decode("utf-8", "ignore")
            if ssid == WIFI_SSID:
                found = True
            print("[wifi]  SSID:", repr(ssid))
        print("[wifi] target found:", found)
    except Exception as e:
        print("[wifi] scan failed:", e)

    if wlan.isconnected():
        print("[wifi] already connected:", wlan.ifconfig()[0])
        return wlan

    print(f"[wifi] connecting to {WIFI_SSID!r}...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    deadline = utime.ticks_add(utime.ticks_ms(), 40_000)  # 40s instead of 20s
    last_status = None

    while utime.ticks_diff(deadline, utime.ticks_ms()) > 0:
        status = wlan.status()
        if status != last_status:
            print("[wifi] status =", status)
            last_status = status

        if status == 3:
            print("[wifi] connected, IP =", wlan.ifconfig()[0])
            return wlan

        if status < 0:
            raise OSError("WiFi failed, status={}".format(status))

        utime.sleep_ms(250)

    raise OSError("WiFi timeout, final status={}".format(wlan.status()))




def connect_mqtt():
    client_id = (BOARD_ID + "_smoke").encode()
    client = MQTTClient(
        client_id,
        MQTT_BROKER,
        port=MQTT_PORT,
        user=MQTT_USER.encode() if MQTT_USER else None,
        password=MQTT_PASSWORD.encode() if MQTT_PASSWORD else None,
        keepalive=30,
    )
    client.connect()
    print(f"[mqtt] connected to {MQTT_BROKER}:{MQTT_PORT}")
    return client


def publish_message(client, payload):
    msg = ujson.dumps(payload)
    # Retain the latest message so it is visible even if you subscribe later.
    client.publish(TOPIC_SMOKE, msg, retain=True)
    print(f"[mqtt] published {msg}")


def main():
    last_heartbeat = 0
    client = None
    wlan = None

    while True:
        try:
            if wlan is None or not wlan.isconnected():
                wlan = connect_wifi()

            if client is None:
                client = connect_mqtt()
                boot_payload = {
                    "type": "boot",
                    "board": BOARD_ID,
                    "ip": wlan.ifconfig()[0],
                    "uptime_s": utime.ticks_ms() // 1000,
                }
                publish_message(client, boot_payload)
                last_heartbeat = utime.ticks_ms()

            now = utime.ticks_ms()
            if utime.ticks_diff(now, last_heartbeat) >= HEARTBEAT_MS:
                heartbeat_payload = {
                    "type": "heartbeat",
                    "board": BOARD_ID,
                    "ip": wlan.ifconfig()[0],
                    "uptime_s": utime.ticks_ms() // 1000,
                }
                publish_message(client, heartbeat_payload)
                last_heartbeat = now

            utime.sleep_ms(100)

        except OSError as e:
            print(f"[wifi] error: {e}")
            client = None
            wlan = None
            utime.sleep_ms(WIFI_RETRY_MS)

        except Exception as e:
            print(f"[mqtt] error: {e}")
            client = None
            utime.sleep_ms(MQTT_RETRY_MS)


if __name__ == "__main__":
    main()
