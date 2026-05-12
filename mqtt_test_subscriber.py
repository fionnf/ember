#!/usr/bin/env python3
"""
Standalone MQTT subscriber to verify the smoke test is posting messages.

Run this while your mqtt_smoke.py is running to confirm messages are being received.
This requires the paho-mqtt library: pip install paho-mqtt
"""

import sys
import time

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("ERROR: paho-mqtt not installed. Install it with:")
    print("  pip install paho-mqtt")
    sys.exit(1)


# Match the configuration in mqtt_smoke.py
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC_PREFIX = "picolight_smoke_test"
TOPIC_SMOKE = f"{MQTT_TOPIC_PREFIX}/smoke"


def on_connect(client, userdata, flags, rc, properties=None):
    """Callback for when the client connects to the broker."""
    if rc == 0:
        print(f"✓ Connected to {MQTT_BROKER}:{MQTT_PORT}")
        print(f"✓ Subscribing to topic: {TOPIC_SMOKE}")
        client.subscribe(TOPIC_SMOKE)
    else:
        print(f"✗ Failed to connect, return code {rc}")


def on_message(client, userdata, msg):
    """Callback for when a message is received."""
    payload = msg.payload.decode("utf-8")
    print(f"\n[{time.strftime('%H:%M:%S')}] Message received:")
    print(f"  Topic: {msg.topic}")
    print(f"  Payload: {payload}")
    print(f"  Retained: {msg.retain}")


def on_disconnect(client, userdata, rc, properties=None):
    """Callback for when the client disconnects."""
    if rc != 0:
        print(f"\n✗ Unexpected disconnect (code: {rc})")
    else:
        print(f"\n✓ Disconnected")


def main():
    print("=" * 60)
    print("MQTT Subscriber - Smoke Test Verification")
    print("=" * 60)
    print(f"Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"Topic: {TOPIC_SMOKE}")
    print("\nWaiting for messages...(Press Ctrl+C to stop)")
    print("-" * 60)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n\nStopping subscriber...")
        client.disconnect()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

