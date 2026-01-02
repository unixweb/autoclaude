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
    PIP_DISABLE_PIP_VERSION_CHECK=1

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

# Update Flask app to serve static files
# Create a simple wrapper that serves static files
RUN cat > /app/wsgi.py << 'EOF'
"""
WSGI entry point for the MQTT Dashboard.

This module configures the Flask application to serve the Vue.js frontend
static files and provides the WSGI application instance for Gunicorn.
"""

import os
from flask import send_from_directory, send_file

from app import create_app
from app.config import get_config
from app.mqtt_client import init_mqtt_client


def create_production_app():
    """Create and configure the production Flask application."""
    config_name = os.environ.get("FLASK_ENV", "production")
    config = get_config(config_name)

    app = create_app(config_name)

    # Initialize MQTT client
    mqtt_client = init_mqtt_client(config)
    app.mqtt_client = mqtt_client

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

    return app


# Create the WSGI application instance
application = create_production_app()
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

# Default command: run with Gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-", "wsgi:app"]
