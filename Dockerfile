# ---- base image ----
FROM python:3.12-slim

# Prevent Python from writing .pyc files / buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set workdir
WORKDIR /app

# System deps (certs, curl for health/debug)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

# ---- Python deps ----
# Copy only requirements first to leverage Docker layer caching
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ---- App code ----
# Copy the rest of your repo (server.py, collect.py, feeds.py, templates/, static/, etc.)
COPY . /app

# Optional: provide a default refresh key (can override with env at deploy)
ENV REFRESH_KEY=mbb_refresh_6P7wP9dXr2Jq

# Build-time: collect initial feed so the site has content on first boot
# (If this fails due to a transient network issue, we don't want the build to fail -> '|| true')
RUN python collect.py || true

# Expose the port your app will listen on (match CMD below)
EXPOSE 8000

# Healthcheck (optional but helpful)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -fsS http://localhost:8000/api/last-mod || exit 1

# ---- Run ----
# Start Gunicorn serving Flask app object "app" from server.py on port 8000
CMD ["gunicorn", "server:app", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "120"]
