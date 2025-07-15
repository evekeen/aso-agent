"""Gunicorn configuration for ASO Playwright Service."""

bind = "0.0.0.0:8001"
workers = 1  # Single worker to prevent browser conflicts
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 300  # 5 minutes timeout
keepalive = 2
max_requests = 1000
max_requests_jitter = 50
preload_app = True
enable_stdio_inheritance = True

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "aso-playwright-service"

# Worker settings
worker_tmp_dir = "/dev/shm"
tmp_upload_dir = None

# SSL (if needed)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"