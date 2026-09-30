"""
Collector: Subscribe MQTT, validate dữ liệu, ghi vào InfluxDB.
Đồng thời đo end-to-end latency và ghi vào measurement 'latency'.
"""
import os
import json
import time
import logging
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("collector")

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "iot/+/+/data")

INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")

influx = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = influx.write_api(write_options=SYNCHRONOUS)


def is_valid(data: dict) -> bool:
    """Kiểm tra schema + range hợp lệ."""
    required = ["device_id", "timestamp", "temperature", "humidity", "light"]
    if not all(k in data for k in required):
        return False
    try:
        t = float(data["temperature"])
        h = float(data["humidity"])
        l = int(data["light"])
        ts = int(data["timestamp"])
    except (TypeError, ValueError):
        return False

    if not (-40 <= t <= 80):
        return False
    if not (0 <= h <= 100):
        return False
    if not (0 <= l <= 4095):
        return False
    # timestamp không được lệch quá 1 ngày
    if abs(time.time() - ts) > 86400:
        return False
    return True


def on_connect(client, userdata, flags, reason_code, properties=None):
    log.info("Connected to MQTT broker (rc=%s)", reason_code)
    client.subscribe(MQTT_TOPIC, qos=1)
    log.info("Subscribed: %s", MQTT_TOPIC)


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode("utf-8"))
    except json.JSONDecodeError:
        log.warning("Invalid JSON on topic %s", msg.topic)
        return

    if not is_valid(data):
        log.warning("Invalid data: %s", data)
        return

    ts = int(data["timestamp"])
    device_id = str(data["device_id"])

    # 1) Ghi dữ liệu raw
    point_raw = (
        Point("sensor_raw")
        .tag("device_id", device_id)
        .field("temperature", float(data["temperature"]))
        .field("humidity", float(data["humidity"]))
        .field("light", int(data["light"]))
        .time(ts, WritePrecision.S)
    )

    # 2) Ghi latency
    latency_ms = (time.time() - ts) * 1000.0
    point_lat = (
        Point("latency")
        .tag("device_id", device_id)
        .field("end_to_end_ms", latency_ms)
        .time(datetime.now(timezone.utc), WritePrecision.NS)
    )

    try:
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=[point_raw, point_lat])
        log.info("Saved %s | T=%.2f H=%.2f L=%d | latency=%.1f ms",
                 device_id, data["temperature"], data["humidity"],
                 data["light"], latency_ms)
    except Exception as e:
        log.error("InfluxDB write failed: %s", e)


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="collector-01")
    client.on_connect = on_connect
    client.on_message = on_message

    log.info("Connecting to MQTT %s:%d ...", MQTT_BROKER, MQTT_PORT)
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()


if __name__ == "__main__":
    main()