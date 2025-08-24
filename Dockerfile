# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir gunicorn

# Copy code
COPY . .

# Expose port
ENV PYTHONUNBUFFERED=1

# Start the Flask app with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:${PORT}", "server:app"]
