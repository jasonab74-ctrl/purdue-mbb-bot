# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# System updates (optional but safe)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# App code
COPY . .

# Ensure unbuffered logs
ENV PYTHONUNBUFFERED=1

# IMPORTANT: use shell-form CMD so $PORT expands
CMD gunicorn --bind 0.0.0.0:$PORT server:app
