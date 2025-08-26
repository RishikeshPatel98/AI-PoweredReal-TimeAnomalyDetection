import os, json, time, numpy as np
from confluent_kafka import Consumer
from joblib import dump, load
from prometheus_client import start_http_server, Gauge, Counter

MODEL_LABEL = os.getenv("MODEL_LABEL", "if")
BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
TOPIC = os.getenv("TOPIC", "service-metrics")
GROUP_ID = os.getenv("GROUP_ID", "anomaly-detector-if")
PROM_PORT = int(os.getenv("PROM_PORT", "8000"))
MODEL_PATH = os.getenv("MODEL_PATH", "/app/models/iso.pkl")

latency_g = Gauge('detector_latency_seconds', 'Event->detection latency (s)', ['model'])
tput_g    = Gauge('detector_throughput_mps', 'Messages per second', ['model'])
anoms_c   = Counter('detector_anomalies_total', 'Total anomalies flagged', ['model'])
pr_tp     = Counter('detector_true_positives_total', 'True positives', ['model'])
pr_fp     = Counter('detector_false_positives_total', 'False positives', ['model'])

def build_consumer():
    c = Consumer({
        "bootstrap.servers": BOOTSTRAP,
        "group.id": GROUP_ID,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
    })
    c.subscribe([TOPIC])
    return c

def features_from_event(e):
    return np.array([[e['latency'], e['cpu'], e['memory']]], dtype=float)

def if_load():
    try:
        obj = load(MODEL_PATH)
        return obj["scaler"], obj["iso"]
    except Exception:
        return None, None

def if_save(scaler, iso):
    dump({"scaler": scaler, "iso": iso}, MODEL_PATH)

def if_bootstrap_fit(buffer):
    from sklearn.preprocessing import StandardScaler
    from sklearn.ensemble import IsolationForest
    X = np.vstack(buffer)
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    iso = IsolationForest(n_estimators=200, contamination=0.02, random_state=42)
    iso.fit(Xs)
    if_save(scaler, iso)
    print("[IF] model fitted:", X.shape)
    return scaler, iso

def if_predict(scaler, iso, x):
    xs = scaler.transform(x)
    pred = iso.predict(xs)[0]
    return (pred == -1)

def main():
    print("Detector(IF) consuming", TOPIC)
    start_http_server(PROM_PORT)
    c = build_consumer()

    buffer = []
    BOOTSTRAP_N = 1000
    last_window_start = time.time()
    count_in_window = 0

    scaler, iso = if_load()

    while True:
        msg = c.poll(1.0)
        if msg is None or msg.error():
            continue
        e = json.loads(msg.value())
        x = features_from_event(e)

        now = time.time()
        count_in_window += 1
        if now - last_window_start >= 1.0:
            tput_g.labels(MODEL_LABEL).set(count_in_window / (now - last_window_start))
            count_in_window = 0
            last_window_start = now

        if "ts" in e:
            latency_g.labels(MODEL_LABEL).set(max(0.0, now - float(e["ts"])))

        if scaler is None:
            buffer.append(x[0])
            if len(buffer) >= BOOTSTRAP_N:
                scaler, iso = if_bootstrap_fit(buffer); buffer.clear()
            continue

        is_anom = if_predict(scaler, iso, x)
        if is_anom:
            anoms_c.labels(MODEL_LABEL).inc()
            if int(e.get("label", 0)) == 1:
                pr_tp.labels(MODEL_LABEL).inc()
            else:
                pr_fp.labels(MODEL_LABEL).inc()

if __name__ == "__main__":
    main()
