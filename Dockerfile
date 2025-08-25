FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Gunicorn serves Flask app object named "app" inside server.py
CMD ["gunicorn","-w","2","-t","60","-b","0.0.0.0:10000","server:app"]
