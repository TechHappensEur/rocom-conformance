#!/usr/bin/env python3
# FILE: fixtures/vda5050_mock.py
# Lightweight VDA 5050 mock fixture for conformance tests.
# Echo responder for identity registration and data profile tests.
# Not a full simulator — just enough for MQTT contract validation.
import json
import os
import paho.mqtt.client as mqtt

BROKER = os.environ.get("MQTT_BROKER", "mosquitto")
PORT = int(os.environ.get("MQTT_BROKER_PORT", 1883))


def on_connect(client, userdata, flags, rc):
    client.subscribe("#", qos=1)


def on_message(client, userdata, msg):
    topic = msg.topic
    payload = json.loads(msg.payload.decode())

    # Echo registration with identity check
    if "/register" in topic:
        agent_id = payload.get("agent_id", "unknown")
        client.publish(
            f"{topic}/ack",
            json.dumps({"status": "registered", "agent_id": agent_id, "echo": True}),
            qos=1,
        )

    # Echo state queries
    elif "/state/" in topic:
        client.publish(f"{topic}/echo", json.dumps({"echo": True}), qos=1)


def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    print(f"VDA5050 mock connected to {BROKER}:{PORT}")
    client.loop_forever()


if __name__ == "__main__":
    main()
