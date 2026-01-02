"""
Clients API Routes

This module provides REST API endpoints for monitoring MQTT client
connections and statistics.
"""

from flask import Blueprint, jsonify

from app.mqtt_client import get_mqtt_client
from app.services.client_monitor import get_client_monitor
from app.services.sys_monitor import get_sys_monitor

clients_bp = Blueprint("clients", __name__)


@clients_bp.route("")
def get_clients():
    """
    Get list of connected clients and client categories.

    Note: Mosquitto's $SYS topics provide aggregate statistics, not individual
    client identifiers. This endpoint returns categorized client counts and
    connection activity information.

    Returns:
        JSON response with client categories and statistics.

    Response format:
        {
            "summary": {
                "total_tracked": 10,
                "currently_connected": 5,
                "persistent_disconnected": 3,
                "expired_sessions": 2,
                "peak_connections": 8
            },
            "categories": [
                {
                    "name": "Connected",
                    "description": "Clients currently connected to the broker",
                    "count": 5,
                    "status": "online"
                },
                ...
            ],
            "connection_activity": {
                "rate_1min": 0.5,
                "rate_5min": 0.3,
                "rate_15min": 0.2
            },
            "last_updated": "2024-01-02T12:00:00Z"
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

    client_monitor = get_client_monitor()
    client_list = client_monitor.get_client_list()

    return jsonify(client_list), 200


@clients_bp.route("/count")
def get_clients_count():
    """
    Get client count statistics.

    Returns count of connected, disconnected, total, and maximum clients
    with historical peak information.

    Returns:
        JSON response with client count statistics.

    Response format:
        {
            "connected": 5,
            "disconnected": 3,
            "total": 8,
            "maximum": 10,
            "last_updated": "2024-01-02T12:00:00Z"
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

    client_monitor = get_client_monitor()
    stats = client_monitor.get_client_stats()

    return jsonify(stats.to_count_dict()), 200


@clients_bp.route("/active")
def get_active_clients():
    """
    Get the count of active (currently connected) clients.

    Active clients are those that are currently connected to the broker.
    This is a convenience endpoint for quick status checks.

    Returns:
        JSON response with active client count.

    Response format:
        {
            "active": 5,
            "connection_rate": {
                "1min": 0.5,
                "5min": 0.3,
                "15min": 0.2
            },
            "last_updated": "2024-01-02T12:00:00Z"
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

    client_monitor = get_client_monitor()
    stats = client_monitor.get_client_stats()

    return jsonify({
        "active": stats.connected,
        "connection_rate": {
            "1min": stats.connections_1min,
            "5min": stats.connections_5min,
            "15min": stats.connections_15min,
        },
        "last_updated": stats.last_updated.isoformat() if stats.last_updated else None,
    }), 200


@clients_bp.route("/stats")
def get_clients_stats():
    """
    Get detailed client statistics.

    Returns comprehensive client statistics including counts,
    connection rates, and historical data.

    Returns:
        JSON response with detailed client statistics.

    Response format:
        {
            "connected": 5,
            "disconnected": 3,
            "total": 8,
            "maximum": 10,
            "expired": 2,
            "connection_rate": {
                "1min": 0.5,
                "5min": 0.3,
                "15min": 0.2
            },
            "last_updated": "2024-01-02T12:00:00Z"
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

    client_monitor = get_client_monitor()
    stats = client_monitor.get_client_stats()

    return jsonify(stats.to_dict()), 200
