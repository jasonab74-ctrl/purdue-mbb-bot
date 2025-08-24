# Dockerfile
FROM python:3.11-slim

# Prevents Python buffering logs
ENV PYTHONUNBUFFERED=1
# Render provides $PORT; default to 8000 for local
ENV PORT=8000

# System basics (optional, but useful)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Flask app listens on 0.0.0.0:PORT from app/api.py
EXPOSE 8000

# Start the app. Using module form so Python can find the package.
CMD ["python", "-m", "app.api"]
