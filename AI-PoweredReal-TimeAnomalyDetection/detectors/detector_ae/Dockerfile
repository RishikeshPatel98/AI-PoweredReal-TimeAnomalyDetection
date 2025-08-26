# Force ARM64 and Python 3.10, install TF 2.15 (arm64 wheel exists)
FROM --platform=linux/arm64/v8 python:3.10-slim
ARG TF_VER=2.15.0
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends       build-essential     && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir tensorflow==${TF_VER}
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY detector.py .
CMD ["python", "detector.py"]
