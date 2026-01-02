# MQTT Dashboard Docker Image
# Multi-stage build: Vue.js frontend + Flask backend
# =====================================================

# -----------------------------------------------------
# Stage 1: Build the Vue.js frontend
# -----------------------------------------------------
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files for dependency installation
COPY frontend/package.json frontend/package-lock.json* ./

# Install dependencies (use npm ci if lockfile exists, otherwise npm install)
RUN if [ -f package-lock.json ]; then npm ci --silent; else npm install --silent; fi

# Copy frontend source code
COPY frontend/ ./

# Build the production frontend
RUN npm run build

# -----------------------------------------------------
# Stage 2: Production image with Python backend
# -----------------------------------------------------
FROM python:3.12-slim AS production

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FLASK_ENV=production \
    SOCKETIO_ASYNC_MODE=eventlet

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 dashboard \
    && useradd --uid 1000 --gid dashboard --shell /bin/bash --create-home dashboard

# Copy backend requirements and install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/ ./

# Copy built frontend from the first stage
COPY --from=frontend-builder /app/frontend/dist ./static

# Copy docker-entrypoint.sh script
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Update Flask app to serve static files
# Create a simple wrapper that serves static files with Flask-SocketIO support
RUN cat > /app/wsgi.py << 'EOF'
"""
WSGI entry point for the MQTT Dashboard.

This module configures the Flask application to serve the Vue.js frontend
static files, initializes Flask-SocketIO for WebSocket support, and provides
the WSGI application instance for Gunicorn.
"""

import os
from flask import send_from_directory, send_file

from app import create_app
from app.config import get_config
from app.mqtt_client import init_mqtt_client
from app.services.sys_monitor import init_sys_monitor
from app.services.topic_tracker import init_topic_tracker
from app.services.subscription_manager import init_subscription_manager
from app.websocket import init_socketio, start_background_stats_pusher


def create_production_app():
    """Create and configure the production Flask application."""
    config_name = os.environ.get("FLASK_ENV", "production")
    config = get_config(config_name)

    app = create_app(config_name)

    # Initialize MQTT client
    mqtt_client = init_mqtt_client(config)
    app.mqtt_client = mqtt_client

    # Initialize SysMonitor for $SYS topic subscription
    sys_monitor = init_sys_monitor(mqtt_client)
    app.sys_monitor = sys_monitor

    # Initialize TopicTracker for topic discovery
    topic_tracker = init_topic_tracker(mqtt_client)
    app.topic_tracker = topic_tracker

    # Initialize SubscriptionManager for per-client topic subscriptions
    subscription_manager = init_subscription_manager(mqtt_client)
    app.subscription_manager = subscription_manager

    # Initialize Flask-SocketIO for WebSocket support
    socketio = init_socketio(app)
    app.socketio = socketio

    # Start background stats pusher
    start_background_stats_pusher()

    # Serve static files from Vue.js build
    static_folder = os.path.join(os.path.dirname(__file__), "static")

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path):
        """Serve the Vue.js frontend application."""
        # If path is empty or doesn't exist as a file, serve index.html
        # This enables Vue Router history mode
        file_path = os.path.join(static_folder, path)
        if path and os.path.isfile(file_path):
            return send_from_directory(static_folder, path)
        return send_file(os.path.join(static_folder, "index.html"))

    return app, socketio


# Create the WSGI application instance and SocketIO
application, socketio = create_production_app()
app = application  # Alias for gunicorn
EOF

# Change ownership of app directory to non-root user
RUN chown -R dashboard:dashboard /app

# Switch to non-root user
USER dashboard

# Expose the application port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:5000/health || exit 1

# Entrypoint script for proper initialization
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command: run with Gunicorn + eventlet for WebSocket support
# Use eventlet worker class for Flask-SocketIO compatibility
# Single worker is required for WebSocket state management
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--worker-class", "eventlet", "--workers", "1", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-", "wsgi:app"]
