FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 sandbox_user
COPY . .
RUN chown -R sandbox_user:sandbox_user /app
USER sandbox_user
CMD ["python", "main.py"]
