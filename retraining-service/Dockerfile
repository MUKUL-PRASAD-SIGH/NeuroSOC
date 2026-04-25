FROM python:3.11-slim

WORKDIR /workspace

COPY retraining-service/requirements.txt /tmp/retraining-requirements.txt
RUN pip install --no-cache-dir -r /tmp/retraining-requirements.txt

COPY retraining-service ./retraining-service
COPY inference-service ./inference-service
COPY datasets ./datasets
COPY data ./data
COPY models ./models

WORKDIR /workspace/retraining-service

CMD ["python", "main.py", "--daemon"]
