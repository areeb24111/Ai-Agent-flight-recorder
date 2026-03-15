# Agent Flight Recorder API – for Google Cloud Run and other containers
FROM python:3.11-slim

WORKDIR /app

# Install deps (add psycopg2-binary if using Postgres)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY app ./app
COPY sdk_flight_recorder.py .

# Cloud Run sets PORT (default 8080)
ENV PORT=8080
EXPOSE 8080

# Optional: copy pre-built frontend for combined deploy (build stage can add backend/static)
# COPY static ./static

CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
