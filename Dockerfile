# Use a lightweight Python base image
FROM python:3.11-slim

# Prevent Python from buffering logs (so logs stream in Render)
ENV PYTHONUNBUFFERED=1
# Render provides $PORT at runtime (default to 8000 for local dev)
ENV PORT=8000

# Set working directory
WORKDIR /app

# Install dependencies first for better build caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app code
COPY . .

# Expose the port Flask will run on
EXPOSE 8000

# Start the Flask app (runs app/api.py as a module)
CMD ["python", "-m", "app.api"]
