"""Standalone Pico W smoke test for WiFi + MQTT."""

try:
    import ujson
except ImportError:
    import json as ujson

import network
import utime
import machine
from umqtt.simple import MQTTClient


# ============================================================
# Configuration
# ============================================================
BOARD_ID = "smoke_test_board"

# Use the exact SSID shown by wlan.scan()
WIFI_SSID = "eth-iot"
WIFI_PASSWORD = "-6uWFXWia3Vb"

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_USER = ""
MQTT_PASSWORD = ""

MQTT_TOPIC_PREFIX = "picolight_smoke_test"
TOPIC_SMOKE = (MQTT_TOPIC_PREFIX + "/smoke").encode()

HEARTBEAT_MS = 15_000
WIFI_CONNECT_TIMEOUT_MS = 30_000
WIFI_RETRY_MS = 5_000
MQTT_RETRY_MS = 5_000


def format_mac(mac_bytes):
    return ":".join("{:02x}".format(b) for b in mac_bytes)


def wifi_status_text(status):
    mapping = {
        0: "STAT_IDLE",
        1: "STAT_CONNECTING",
        2: "STAT_WRONG_PASSWORD_OR_HANDSHAKE",
        3: "STAT_GOT_IP",
        -1: "STAT_NO_AP_FOUND",
        -2: "STAT_WRONG_PASSWORD",
        -3: "STAT_ASSOC_FAIL",
    }
    return mapping.get(status, "UNKNOWN")


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    try:
        wlan.config(pm=0xa11140)  # disable power save
    except Exception:
        pass

    mac = format_mac(wlan.config("mac"))
    print("[wifi] MAC:", mac)

    print("[wifi] scanning for visible networks...")
    found = False
    try:
        networks = wlan.scan()
        seen = []
        for net in networks:
            ssid = net[0].decode("utf-8", "ignore")
            if ssid and ssid not in seen:
                seen.append(ssid)
        for ssid in seen:
            print("[wifi]  SSID:", ssid)
            if ssid == WIFI_SSID:
                found = True
        print("[wifi] target found:", found)
    except Exception as e:
        print("[wifi] scan unavailable:", e)

    if wlan.isconnected():
        print("[wifi] already connected, IP={}".format(wlan.ifconfig()[0]))
        return wlan

    print("[wifi] connecting to {!r}...".format(WIFI_SSID))
    wlan.disconnect()
    utime.sleep_ms(200)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    deadline = utime.ticks_add(utime.ticks_ms(), WIFI_CONNECT_TIMEOUT_MS)
    last_status = None

    while utime.ticks_diff(deadline, utime.ticks_ms()) > 0:
        status = wlan.status()

        if status != last_status:
            print("[wifi] status = {} ({})".format(status, wifi_status_text(status)))
            last_status = status

        if status == 3:
            ip = wlan.ifconfig()[0]
            print("[wifi] connected, IP={}".format(ip))
            return wlan

        if status in (-1, -2, -3):
            raise OSError("WiFi failed: {} ({})".format(status, wifi_status_text(status)))

        utime.sleep_ms(250)

    raise OSError("WiFi timeout, final status={} ({})".format(wlan.status(), wifi_status_text(wlan.status())))


def connect_mqtt():
    client_id = (BOARD_ID + "_smoke").encode()
    client = MQTTClient(
        client_id=client_id,
        server=MQTT_BROKER,
        port=MQTT_PORT,
        user=MQTT_USER.encode() if MQTT_USER else None,
        password=MQTT_PASSWORD.encode() if MQTT_PASSWORD else None,
        keepalive=30,
    )
    client.connect()
    print("[mqtt] connected to {}:{}".format(MQTT_BROKER, MQTT_PORT))
    return client


def publish_message(client, payload):
    msg = ujson.dumps(payload)
    client.publish(TOPIC_SMOKE, msg, retain=True)
    print("[mqtt] published", msg)


def make_payload(msg_type, wlan):
    return {
        "type": msg_type,
        "board": BOARD_ID,
        "ip": wlan.ifconfig()[0],
        "uptime_s": utime.ticks_ms() // 1000,
        "rssi": wlan.status("rssi") if hasattr(wlan, "status") else None,
    }


def main():
    wlan = None
    client = None
    last_heartbeat = utime.ticks_ms()

    while True:
        try:
            if wlan is None or not wlan.isconnected():
                wlan = connect_wifi()
                client = None

            if client is None:
                client = connect_mqtt()
                publish_message(client, make_payload("boot", wlan))
                last_heartbeat = utime.ticks_ms()

            now = utime.ticks_ms()
            if utime.ticks_diff(now, last_heartbeat) >= HEARTBEAT_MS:
                publish_message(client, make_payload("heartbeat", wlan))
                last_heartbeat = now

            utime.sleep_ms(100)

        except OSError as e:
            print("[net] error:", e)
            try:
                if client is not None:
                    client.disconnect()
            except Exception:
                pass
            client = None
            wlan = None
            utime.sleep_ms(WIFI_RETRY_MS)

        except Exception as e:
            print("[mqtt] error:", e)
            try:
                if client is not None:
                    client.disconnect()
            except Exception:
                pass
            client = None
            utime.sleep_ms(MQTT_RETRY_MS)


if __name__ == "__main__":
    main()
