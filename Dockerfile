FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Make sure BOTH server.py and collect.py get copied into /app
COPY . .

# Ensure Python can import modules from /app
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Shell-form so $PORT expands at runtime
CMD gunicorn --bind 0.0.0.0:$PORT server:app
