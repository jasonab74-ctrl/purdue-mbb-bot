# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose the port Railway (or Render) assigns
EXPOSE 10000

# Run with Gunicorn, binding to the platform's $PORT
CMD ["sh", "-c", "gunicorn server:app --workers=2 --threads=4 --timeout=120 --bind 0.0.0.0:$PORT"]
