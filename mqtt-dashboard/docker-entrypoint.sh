#!/bin/bash
set -e

# MQTT Dashboard Docker Entrypoint Script
# =========================================
# This script handles the initialization and startup of the MQTT Dashboard container.
#
# Features:
# - Waits for Mosquitto broker to be ready before starting
# - Logs startup information for debugging
# - Handles graceful shutdown on SIGTERM/SIGINT
# - Validates environment configuration

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
MQTT_BROKER_HOST="${MQTT_BROKER_HOST:-mosquitto}"
MQTT_BROKER_PORT="${MQTT_BROKER_PORT:-1883}"
MQTT_MAX_WAIT="${MQTT_MAX_WAIT:-60}"  # Maximum wait time in seconds
MQTT_RETRY_INTERVAL="${MQTT_RETRY_INTERVAL:-2}"  # Retry interval in seconds

# Color codes for logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# PID of the gunicorn process
GUNICORN_PID=""

# -----------------------------------------------------------------------------
# Logging Functions
# -----------------------------------------------------------------------------
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# -----------------------------------------------------------------------------
# Signal Handlers
# -----------------------------------------------------------------------------
# Graceful shutdown handler for SIGTERM and SIGINT
graceful_shutdown() {
    log_info "Received shutdown signal, performing graceful shutdown..."

    if [ -n "$GUNICORN_PID" ]; then
        log_info "Stopping Gunicorn (PID: $GUNICORN_PID)..."
        kill -TERM "$GUNICORN_PID" 2>/dev/null || true

        # Wait for gunicorn to stop (max 10 seconds)
        for i in {1..10}; do
            if ! kill -0 "$GUNICORN_PID" 2>/dev/null; then
                log_success "Gunicorn stopped gracefully"
                break
            fi
            sleep 1
        done

        # Force kill if still running
        if kill -0 "$GUNICORN_PID" 2>/dev/null; then
            log_warn "Gunicorn did not stop gracefully, forcing shutdown..."
            kill -KILL "$GUNICORN_PID" 2>/dev/null || true
        fi
    fi

    log_info "Dashboard shutdown complete"
    exit 0
}

# Register signal handlers
trap graceful_shutdown SIGTERM SIGINT

# -----------------------------------------------------------------------------
# Validation Functions
# -----------------------------------------------------------------------------
# Validate required environment variables
validate_environment() {
    log_info "Validating environment configuration..."

    # Check if MQTT broker host is set
    if [ -z "$MQTT_BROKER_HOST" ]; then
        log_error "MQTT_BROKER_HOST is not set"
        exit 1
    fi

    # Validate port is a number
    if ! [[ "$MQTT_BROKER_PORT" =~ ^[0-9]+$ ]]; then
        log_error "MQTT_BROKER_PORT must be a number, got: $MQTT_BROKER_PORT"
        exit 1
    fi

    # Validate port range
    if [ "$MQTT_BROKER_PORT" -lt 1 ] || [ "$MQTT_BROKER_PORT" -gt 65535 ]; then
        log_error "MQTT_BROKER_PORT must be between 1 and 65535, got: $MQTT_BROKER_PORT"
        exit 1
    fi

    log_success "Environment configuration is valid"
}

# -----------------------------------------------------------------------------
# MQTT Broker Readiness Check
# -----------------------------------------------------------------------------
# Wait for MQTT broker to be ready
wait_for_mqtt() {
    log_info "Waiting for MQTT broker at $MQTT_BROKER_HOST:$MQTT_BROKER_PORT..."

    local elapsed=0
    local connected=false

    while [ $elapsed -lt $MQTT_MAX_WAIT ]; do
        # Try to establish a TCP connection to the broker
        if timeout 2 bash -c "echo > /dev/tcp/$MQTT_BROKER_HOST/$MQTT_BROKER_PORT" 2>/dev/null; then
            connected=true
            break
        fi

        log_info "Broker not ready yet, retrying in ${MQTT_RETRY_INTERVAL}s... (${elapsed}s/${MQTT_MAX_WAIT}s elapsed)"
        sleep $MQTT_RETRY_INTERVAL
        elapsed=$((elapsed + MQTT_RETRY_INTERVAL))
    done

    if [ "$connected" = true ]; then
        log_success "MQTT broker is ready at $MQTT_BROKER_HOST:$MQTT_BROKER_PORT"
        return 0
    else
        log_error "MQTT broker at $MQTT_BROKER_HOST:$MQTT_BROKER_PORT is not reachable after ${MQTT_MAX_WAIT}s"
        log_warn "Starting dashboard anyway - will retry connection in background"
        return 1
    fi
}

# -----------------------------------------------------------------------------
# Startup Information
# -----------------------------------------------------------------------------
# Display startup information
log_startup_info() {
    log_info "============================================"
    log_info "MQTT Dashboard Starting"
    log_info "============================================"
    log_info "Configuration:"
    log_info "  - Flask Environment: ${FLASK_ENV:-production}"
    log_info "  - Debug Mode: ${FLASK_DEBUG:-0}"
    log_info "  - MQTT Broker: $MQTT_BROKER_HOST:$MQTT_BROKER_PORT"
    log_info "  - MQTT Client ID: ${MQTT_CLIENT_ID:-mqtt-dashboard}"
    log_info "  - MQTT Keepalive: ${MQTT_KEEPALIVE:-60}s"

    if [ -n "$MQTT_USERNAME" ]; then
        log_info "  - MQTT Authentication: Enabled (username: $MQTT_USERNAME)"
    else
        log_info "  - MQTT Authentication: Disabled"
    fi

    if [ "${MQTT_USE_TLS:-false}" = "true" ]; then
        log_info "  - MQTT TLS: Enabled"
        log_info "  - TLS Insecure: ${MQTT_TLS_INSECURE:-false}"
    else
        log_info "  - MQTT TLS: Disabled"
    fi

    log_info "  - SocketIO Async Mode: ${SOCKETIO_ASYNC_MODE:-eventlet}"
    log_info "============================================"
}

# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------
main() {
    # Log startup information
    log_startup_info

    # Validate environment
    validate_environment

    # Wait for MQTT broker (continue even if it fails)
    wait_for_mqtt || true

    # Start Gunicorn with the provided command or default
    log_info "Starting Gunicorn server..."

    # Execute the CMD from Dockerfile or provided arguments
    if [ $# -eq 0 ]; then
        # Default command from Dockerfile
        exec gunicorn \
            --bind 0.0.0.0:5000 \
            --worker-class eventlet \
            --workers 1 \
            --timeout 60 \
            --access-logfile - \
            --error-logfile - \
            wsgi:app &
    else
        # Custom command provided
        exec "$@" &
    fi

    GUNICORN_PID=$!
    log_success "Gunicorn started with PID: $GUNICORN_PID"
    log_info "Dashboard is ready to accept connections on port 5000"

    # Wait for the background process
    wait $GUNICORN_PID
}

# Run main function
main "$@"
