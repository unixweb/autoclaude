"""
Gunicorn Configuration for MQTT Dashboard

This configuration file handles proper initialization of the MQTT client
in each worker process when using eventlet workers.
"""

# Server socket
bind = "0.0.0.0:5000"

# Worker processes
worker_class = "sync"  # Simple synchronous worker
workers = 1
threads = 1  # Single thread to avoid MQTT client ID conflicts
preload_app = False  # Load app in each worker, not in master

# Timeouts
timeout = 120
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"


def post_fork(server, worker):
    """
    Called after a worker has been forked.

    No longer needed - MQTT connection is handled by separate mqtt-bridge service.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Worker {worker.pid}: Started (MQTT handled by bridge service)")


def on_starting(server):
    """Called just before the master process is initialized."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Gunicorn master process starting...")


def when_ready(server):
    """Called just after the server is started."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Gunicorn is ready to accept connections")


def on_exit(server):
    """Called just before exiting Gunicorn."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Gunicorn is shutting down...")
