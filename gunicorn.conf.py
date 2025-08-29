# Gunicorn config
bind = "0.0.0.0:"  # Railway injects $PORT; CLI will append it
workers = 2
worker_class = "gthread"
threads = 4
timeout = 60
