"""
Gunicorn configuration for the POS Management System.

For more information, see:
https://docs.gunicorn.org/en/stable/settings.html
"""

import multiprocessing

# =============================================================================
# Server Socket
# =============================================================================

bind = "0.0.0.0:8000"

# =============================================================================
# Worker Processes
# =============================================================================

# Recommended: (2 * CPU cores) + 1
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gthread"
threads = 2
worker_tmp_dir = "/dev/shm"

# =============================================================================
# Timeouts
# =============================================================================

timeout = 120
graceful_timeout = 30
keepalive = 5

# =============================================================================
# Logging
# =============================================================================

accesslog = "-"
errorlog = "-"
loglevel = "info"

# =============================================================================
# Server Mechanics
# =============================================================================

# Restart workers after this many requests to prevent memory leaks.
max_requests = 1000
max_requests_jitter = 50

# Preload the application to save memory (copy-on-write).
preload_app = True
