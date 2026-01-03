"""
Broker API Routes

This module provides REST API endpoints for monitoring the Mosquitto MQTT broker
status, statistics, and version information.
"""

from flask import Blueprint, jsonify

from app.mqtt_client import get_mqtt_client
from app.services.sys_monitor import get_sys_monitor

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
    Get comprehensive broker statistics from $SYS topics.

    Returns:
        JSON response with detailed broker statistics including
        clients, messages, bytes, load metrics, and heap usage.

    Response format:
        {
            "broker": {"version": "...", "uptime": ...},
            "clients": {...},
            "messages": {...},
            "bytes": {...},
            "load": {...},
            "heap": {...},
            "last_updated": "..."
        }
    """
    mqtt_client = get_mqtt_client()

    if not mqtt_client.is_connected:
        return jsonify({
            "error": "Not connected to MQTT broker",
            "code": "BROKER_DISCONNECTED",
        }), 503

    sys_monitor = get_sys_monitor()

    if not sys_monitor.is_subscribed:
        return jsonify({
            "error": "Not subscribed to broker statistics",
            "code": "SYS_NOT_SUBSCRIBED",
        }), 503

    stats = sys_monitor.get_stats()
    return jsonify(stats.to_dict()), 200


@broker_bp.route("/stats/summary")
def get_broker_stats_summary():
    """
    Get a summary of key broker statistics.

    Returns a lighter-weight response with only the most essential
    metrics for dashboard overview displays.

    Response format:
        {
            "version": "...",
            "uptime": ...,
            "clients_connected": ...,
            "clients_total": ...,
            "messages_received": ...,
            "messages_sent": ...,
            "bytes_received": ...,
            "bytes_sent": ...,
            "subscriptions": ...,
            "retained_messages": ...,
            "last_updated": "..."
        }
    """
    mqtt_client = get_mqtt_client()

    if not mqtt_client.is_connected:
        return jsonify({
            "error": "Not connected to MQTT broker",
            "code": "BROKER_DISCONNECTED",
        }), 503

    sys_monitor = get_sys_monitor()

    if not sys_monitor.is_subscribed:
        return jsonify({
            "error": "Not subscribed to broker statistics",
            "code": "SYS_NOT_SUBSCRIBED",
        }), 503

    stats = sys_monitor.get_stats()
    return jsonify(stats.to_summary_dict()), 200


@broker_bp.route("/version")
def get_broker_version():
    """
    Get Mosquitto broker version and uptime information.

    Returns:
        JSON response with broker version and uptime details.

    Response format:
        {
            "version": "mosquitto version 2.0.18",
            "uptime": 12345,
            "uptime_formatted": "3h 25m 45s"
        }
    """
    mqtt_client = get_mqtt_client()

    if not mqtt_client.is_connected:
        return jsonify({
            "error": "Not connected to MQTT broker",
            "code": "BROKER_DISCONNECTED",
        }), 503

    sys_monitor = get_sys_monitor()

    if not sys_monitor.is_subscribed:
        return jsonify({
            "error": "Not subscribed to broker statistics",
            "code": "SYS_NOT_SUBSCRIBED",
        }), 503

    stats = sys_monitor.get_stats()

    # Format uptime into human-readable string
    uptime_formatted = None
    if stats.uptime is not None:
        uptime = stats.uptime
        days, remainder = divmod(uptime, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")
        uptime_formatted = " ".join(parts)

    return jsonify({
        "version": stats.version,
        "uptime": stats.uptime,
        "uptime_formatted": uptime_formatted,
    }), 200
