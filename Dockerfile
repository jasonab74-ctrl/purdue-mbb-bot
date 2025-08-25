FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render will detect port; we expose for clarity
ENV PORT=10000
CMD gunicorn app.api:app --bind 0.0.0.0:${PORT:-8000} --workers 2
