"""Minimal Pico W smoke test for WiFi + MQTT.

Connects to WiFi, publishes a retained boot message, then keeps sending
heartbeat updates to a dedicated MQTT topic so you can verify the board
from another device (MQTT Explorer, HiveMQ WebSocket client, mosquitto_sub,
etc.).

Use this as a temporary `main.py` on the Pico you want to test, or upload it
alongside the rest of the project and run it from the REPL / Thonny.
"""

import ujson
import network
import utime
from umqtt.simple import MQTTClient

from config import (
    BOARD_ID,
    WIFI_SSID,
    WIFI_PASSWORD,
    MQTT_BROKER,
    MQTT_PORT,
    MQTT_USER,
    MQTT_PASSWORD,
    MQTT_TOPIC_PREFIX,
)


TOPIC_SMOKE = (MQTT_TOPIC_PREFIX + "/smoke").encode()
HEARTBEAT_MS = 15_000
WIFI_RETRY_MS = 5_000
MQTT_RETRY_MS = 5_000


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return wlan

    print(f"[wifi] connecting to {WIFI_SSID!r}...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    deadline = utime.ticks_add(utime.ticks_ms(), 20_000)
    while not wlan.isconnected():
        if utime.ticks_diff(deadline, utime.ticks_ms()) <= 0:
            raise OSError("WiFi timeout")
        utime.sleep_ms(200)

    print(f"[wifi] connected, IP={wlan.ifconfig()[0]}")
    return wlan


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


def publish(client, payload):
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
                publish(client, boot_payload)
                last_heartbeat = utime.ticks_ms()

            now = utime.ticks_ms()
            if utime.ticks_diff(now, last_heartbeat) >= HEARTBEAT_MS:
                heartbeat_payload = {
                    "type": "heartbeat",
                    "board": BOARD_ID,
                    "ip": wlan.ifconfig()[0],
                    "uptime_s": utime.ticks_ms() // 1000,
                }
                publish(client, heartbeat_payload)
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
