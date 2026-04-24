FROM python:3.11-slim

# Install libpcap for Scapy
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpcap-dev gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Init Kafka topics first, then start ingestion service
CMD ["sh", "-c", "python kafka_setup.py && python main.py"]
