markdown
# AI-Powered Real-Time Anomaly Detection in Microservice Architectures
*(Thesis Implementation)*

This project is the implementation for the Master’s thesis:  
**“AI-Powered Real-Time Anomaly Detection in Microservice Architectures using Apache Kafka and Stream Processing”**

It demonstrates how **Apache Kafka**, **unsupervised AI models** (Isolation Forest and Autoencoder), and a **containerised microservices stack** can be combined to detect anomalies in real time from live system metrics.

---

## 🚀 Features
- **Streaming backbone:** Apache Kafka used as the messaging layer for continuous metric ingestion.
- **Synthetic producers:** A producer microservice simulates microservice metrics (latency, CPU, memory) with ~1% injected anomalies.
- **Two anomaly detectors:**
    - Isolation Forest (IF) – tree-based outlier detection.
    - Autoencoder (AE) – neural network for reconstruction error.
- **Metrics exposure:** Each detector exports Prometheus metrics (latency, throughput, anomalies, TP/FP, AE reconstruction error).
- **Visualization:** Prometheus scrapes metrics and Grafana displays dashboards comparing IF and AE side by side.
- **Containerised architecture:** Each service (producer, IF detector, AE detector, Kafka, Prometheus, Grafana) runs in Docker.

---

## 🏗 Architecture
Producer → Kafka → \[Isolation Forest Detector] + \[Autoencoder Detector] → Prometheus → Grafana


- Producer pushes synthetic events into Kafka topic `service-metrics`.
- Detectors consume events, apply models, and flag anomalies in real time.
- Prometheus scrapes detectors’ metrics endpoints.
- Grafana visualises precision/recall, throughput, anomaly counts, and AE reconstruction error.

---

## 📦 Setup & Run

### Prerequisites
- Docker Desktop (Mac or Linux or windows)
- Docker Compose

### Run
bash docker compose up --build
`

### Access services

* **Prometheus:** [http://localhost:9090](http://localhost:9090)

    * Check **Status → Targets** to verify detectors are UP.
* **Grafana:** [http://localhost:3000](http://localhost:3000)

    * Login: `admin` / `admin` (then set new password).
    * Add Prometheus data source (`http://prometheus:9090`).
    * Import `grafana-dashboard.json` from the repo.

---

## 📊 Key Metrics

* `detector_latency_seconds{model="if|ae"}` → Event-to-detection latency.
* `detector_throughput_mps{model="if|ae"}` → Messages per second.
* `detector_anomalies_total{model="if|ae"}` → Total anomalies flagged.
* `detector_true_positives_total` / `detector_false_positives_total` → TP/FP counts.
* `detector_reconstruction_error{model="ae"}` → AE model’s error per event.

---

## 📈 Dashboard

The Grafana dashboard (`grafana-dashboard.json`) contains:

* Latency comparison (IF vs AE)
* Throughput
* Anomalies per model
* True vs False Positives
* AE reconstruction error

---

## 🔮 Future Improvements

This prototype demonstrates the feasibility of real-time anomaly detection in microservice systems, but several extensions are possible:

1. **Kubernetes Deployment**

    * Extend beyond Docker Compose with Kubernetes manifests or Helm charts.
    * Add horizontal scaling of producers/detectors for realistic microservice orchestration.

2. **Integration with Real Microservices**

    * Instead of synthetic data, connect to actual service telemetry (logs, traces, Prometheus exporters).

3. **Additional Models**

    * Add LSTM or Temporal Convolutional Networks for sequence-aware anomaly detection.
    * Explore hybrid ensembles combining statistical + deep learning methods.

4. **Feature Engineering & Stream Processing**

    * Use Kafka Streams or Apache Flink to aggregate sliding windows (e.g., average latency per 10s).
    * Support richer features (request rates, error codes).

5. **Adaptive & Online Learning**

    * Implement online retraining to adapt models dynamically as workload patterns change.

6. **Explainability**

    * Add SHAP/LIME explanations for anomalies to help operators understand why an event was flagged.

7. **Security & Fault-Tolerance**

    * Harden Kafka and monitoring stack for production-grade reliability.
    * Deploy redundant detectors and producers to simulate real microservice environments.

--- 
## 📚 Academic Context 
This project was developed as part of a Master’s thesis exploring the **effectiveness of unsupervised AI models (Isolation Forest vs Autoencoder)** in detecting anomalies in live microservice environments. The research demonstrates how **stream processing + containerisation + monitoring** can provide a scalable and observable anomaly detection pipeline. 
--- 
## 👨‍💻 Author 
Rishikesh Patel — Master’s Thesis Project
