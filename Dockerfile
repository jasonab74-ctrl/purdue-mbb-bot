FROM python:3.11-slim

# sane defaults
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=10000

WORKDIR /app

# minimal OS deps (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

# install Python deps first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy app
COPY . .

# optional, but nice locally
EXPOSE 10000

# simple healthcheck (Render ignores it but it’s useful elsewhere)
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD curl -fsS http://127.0.0.1:${PORT}/healthz || exit 1

# run gunicorn with a modest timeout and 2 workers
# (use $PORT if Render ever changes it; default to 10000)
CMD bash -lc 'exec gunicorn --bind 0.0.0.0:${PORT:-10000} --timeout 45 --workers 2 server:app'
