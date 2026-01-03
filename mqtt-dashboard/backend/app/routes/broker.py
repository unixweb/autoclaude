"""
Broker API Routes

This module provides REST API endpoints for monitoring the Mosquitto MQTT broker
status, statistics, and version information.
"""

from flask import Blueprint, jsonify

broker_bp = Blueprint("broker", __name__)


@broker_bp.route("/status")
def get_broker_status():
    """Get the current broker connection status from Redis."""
    from app.redis_client import get_redis_client
    from app.redis_channels import RedisChannels

    redis_client = get_redis_client()

    # Last status is cached in Redis, we subscribe to updates
    # For now, return connected if Redis is connected
    # (Bridge service publishes actual MQTT status)

    status = {
        "connected": redis_client.is_connected(),
        "broker": {
            "host": "via mqtt-bridge",
            "port": 1883,
        },
    }

    return jsonify(status), 200


@broker_bp.route("/stats")
def get_broker_stats():
    """
    Get broker statistics.

    Note: Real-time stats are pushed via WebSocket from mqtt-bridge service.
    This endpoint returns a status message.
    """
    return jsonify({
        "message": "Stats are pushed via WebSocket from mqtt-bridge service",
        "websocket_endpoint": "/socket.io/",
    }), 200


@broker_bp.route("/stats/summary")
def get_broker_stats_summary():
    """
    Get broker statistics summary.

    Note: Real-time stats are pushed via WebSocket from mqtt-bridge service.
    This endpoint returns a status message.
    """
    return jsonify({
        "message": "Stats are pushed via WebSocket from mqtt-bridge service",
        "websocket_endpoint": "/socket.io/",
    }), 200


@broker_bp.route("/version")
def get_broker_version():
    """
    Get broker version.

    Note: Version info is available via WebSocket from mqtt-bridge service.
    This endpoint returns a status message.
    """
    return jsonify({
        "message": "Version info available via WebSocket from mqtt-bridge service",
        "websocket_endpoint": "/socket.io/",
    }), 200
