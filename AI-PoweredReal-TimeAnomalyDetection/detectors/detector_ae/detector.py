import os, json, time, numpy as np
from confluent_kafka import Consumer
from joblib import dump, load
from prometheus_client import start_http_server, Gauge, Counter
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.preprocessing import StandardScaler

MODEL_LABEL = os.getenv("MODEL_LABEL", "ae")
BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
TOPIC = os.getenv("TOPIC", "service-metrics")
GROUP_ID = os.getenv("GROUP_ID", "anomaly-detector-ae")
PROM_PORT = int(os.getenv("PROM_PORT", "8001"))
AE_MODEL_PATH = os.getenv("AE_MODEL_PATH", "/app/models/ae.keras")
AE_META_PATH = os.getenv("AE_META_PATH", "/app/models/ae_meta.pkl")

latency_g = Gauge('detector_latency_seconds', 'Event->detection latency (s)', ['model'])
tput_g    = Gauge('detector_throughput_mps', 'Messages per second', ['model'])
anoms_c   = Counter('detector_anomalies_total', 'Total anomalies flagged', ['model'])
pr_tp     = Counter('detector_true_positives_total', 'True positives', ['model'])
pr_fp     = Counter('detector_false_positives_total', 'False positives', ['model'])
recon_err_g = Gauge('detector_reconstruction_error', 'AE reconstruction error (MSE)', ['model'])

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

def ae_load():
    try:
        model = keras.models.load_model(AE_MODEL_PATH)
        meta = load(AE_META_PATH)
        return model, meta["scaler"], meta["threshold"]
    except Exception:
        return None, None, None

def ae_save(model, scaler, threshold):
    model.save(AE_MODEL_PATH)
    dump({"scaler": scaler, "threshold": threshold}, AE_META_PATH)

def ae_bootstrap_fit(buffer):
    X = np.vstack(buffer)
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    input_dim = Xs.shape[1]
    inp = keras.Input(shape=(input_dim,))
    x = keras.layers.Dense(16, activation='relu')(inp)
    x = keras.layers.Dense(8, activation='relu')(x)
    x = keras.layers.Dense(16, activation='relu')(x)
    out = keras.layers.Dense(input_dim, activation=None)(x)
    model = keras.Model(inp, out)
    model.compile(optimizer='adam', loss='mse')

    model.fit(Xs, Xs, epochs=25, batch_size=64, verbose=0, validation_split=0.1)

    Xhat = model.predict(Xs, verbose=0)
    errs = np.mean((Xs - Xhat)**2, axis=1)
    med = np.median(errs); mad = np.median(np.abs(errs - med)) + 1e-9
    threshold = med + 3.0 * mad

    ae_save(model, scaler, threshold)
    print("[AE] model fitted:", X.shape, "threshold:", float(threshold))
    return model, scaler, threshold

def ae_predict(model, scaler, threshold, x):
    xs = scaler.transform(x)
    xhat = model.predict(xs, verbose=0)
    err = float(np.mean((xs - xhat)**2))
    recon_err_g.labels(MODEL_LABEL).set(err)
    return err > threshold

def main():
    print("Detector(AE) consuming", TOPIC)
    start_http_server(PROM_PORT)
    c = build_consumer()

    buffer = []
    BOOTSTRAP_N = 1000
    last_window_start = time.time()
    count_in_window = 0

    ae_model, ae_scaler, ae_threshold = ae_load()

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

        if ae_model is None:
            buffer.append(x[0])
            if len(buffer) >= BOOTSTRAP_N:
                ae_model, ae_scaler, ae_threshold = ae_bootstrap_fit(buffer); buffer.clear()
            continue

        is_anom = ae_predict(ae_model, ae_scaler, ae_threshold, x)
        if is_anom:
            anoms_c.labels(MODEL_LABEL).inc()
            if int(e.get("label", 0)) == 1:
                pr_tp.labels(MODEL_LABEL).inc()
            else:
                pr_fp.labels(MODEL_LABEL).inc()

if __name__ == "__main__":
    main()
