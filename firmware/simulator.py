import json, time, random
import paho.mqtt.client as mqtt

client = mqtt.Client()
client.connect("localhost", 1883, 60)
client.loop_start()

while True:
    data = {
        "device_id": "sim-01",
        "timestamp": int(time.time()),
        "temperature": round(random.uniform(25, 35), 2),
        "humidity": round(random.uniform(40, 80), 2),
        "light": random.randint(0, 4095),
    }
    client.publish("iot/group01/sim-01/data", json.dumps(data), qos=1)
    print(data)
    time.sleep(5)