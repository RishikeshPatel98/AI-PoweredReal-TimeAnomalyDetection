import os, time, json, random
import numpy as np
from confluent_kafka import Producer

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
TOPIC = os.getenv("TOPIC", "service-metrics")

p = Producer({"bootstrap.servers": BOOTSTRAP})

def synthetic_event():
    latency = np.random.normal(100, 8)
    cpu = np.random.normal(35, 4)
    mem = np.random.normal(500, 15)

    label = 0
    if random.random() < 0.01:
        label = 1
        which = random.choice(["latency","cpu","mem"])
        if which == "latency":
            latency += np.random.normal(120, 20)
        elif which == "cpu":
            cpu += np.random.normal(40, 10)
        else:
            mem += np.random.normal(200, 40)

    return {"ts": time.time(), "latency": float(max(0, latency)),
            "cpu": float(max(0, cpu)), "memory": float(max(0, mem)),
            "label": label}

def delivery(err, msg):
    if err:
        print("Delivery failed:", err)

def main():
    print(f"Producing to {TOPIC} on {BOOTSTRAP}")
    while True:
        e = synthetic_event()
        p.produce(TOPIC, json.dumps(e).encode("utf-8"), callback=delivery)
        p.poll(0)
        time.sleep(0.02)

if __name__ == "__main__":
    main()
