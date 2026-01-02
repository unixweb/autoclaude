"""
WebSocket Support Module

This module provides Flask-SocketIO integration for pushing real-time metrics
to the frontend. It enables WebSocket connections for live broker statistics
updates and subscription to specific metric channels.
"""

import logging
import threading
from datetime import datetime, timezone
from typing import Optional

from flask import Flask
from flask_socketio import SocketIO, emit, join_room, leave_room

from app.models.broker_stats import BrokerStats
from app.services.sys_monitor import get_sys_monitor

logger = logging.getLogger(__name__)

# Global SocketIO instance
socketio: Optional[SocketIO] = None

# Metric channels that clients can subscribe to
METRIC_CHANNELS = {
    "broker_stats": "Full broker statistics",
    "broker_summary": "Summary broker statistics (lightweight)",
    "clients": "Client connection statistics",
    "messages": "Message throughput statistics",
    "bytes": "Byte transfer statistics",
    "load": "Load metrics (1min/5min/15min)",
}

# Update interval in seconds
STATS_PUSH_INTERVAL = 5.0

# Connected clients tracking
_connected_clients: dict[str, dict] = {}
_clients_lock = threading.Lock()


def init_socketio(app: Flask) -> SocketIO:
    """
    Initialize Flask-SocketIO with the Flask application.

    Args:
        app: Flask application instance.

    Returns:
        Configured SocketIO instance.
    """
    global socketio

    # Get async mode from config (default to threading for compatibility)
    async_mode = app.config.get("SOCKETIO_ASYNC_MODE", "threading")

    socketio = SocketIO(
        app,
        cors_allowed_origins=app.config.get("CORS_ORIGINS", "*"),
        async_mode=async_mode,
        logger=False,
        engineio_logger=False,
        ping_timeout=60,
        ping_interval=25,
    )

    _register_event_handlers(socketio)

    logger.info(f"Flask-SocketIO initialized with async_mode={async_mode}")

    return socketio


def get_socketio() -> Optional[SocketIO]:
    """
    Get the global SocketIO instance.

    Returns:
        The global SocketIO instance, or None if not initialized.
    """
    return socketio


def _register_event_handlers(sio: SocketIO) -> None:
    """
    Register WebSocket event handlers.

    Args:
        sio: SocketIO instance to register handlers on.
    """

    @sio.on("connect")
    def handle_connect():
        """Handle client connection."""
        from flask import request

        client_id = request.sid
        client_ip = request.remote_addr

        with _clients_lock:
            _connected_clients[client_id] = {
                "connected_at": datetime.now(timezone.utc).isoformat(),
                "ip": client_ip,
                "subscriptions": set(),
            }

        logger.info(f"WebSocket client connected: {client_id} from {client_ip}")

        # Send initial connection acknowledgment with available channels
        emit("connected", {
            "client_id": client_id,
            "available_channels": list(METRIC_CHANNELS.keys()),
            "push_interval_seconds": STATS_PUSH_INTERVAL,
        })

    @sio.on("disconnect")
    def handle_disconnect():
        """Handle client disconnection."""
        from flask import request

        client_id = request.sid

        with _clients_lock:
            if client_id in _connected_clients:
                client_info = _connected_clients.pop(client_id)
                subscriptions = client_info.get("subscriptions", set())
                logger.info(
                    f"WebSocket client disconnected: {client_id}, "
                    f"was subscribed to: {list(subscriptions)}"
                )
            else:
                logger.info(f"WebSocket client disconnected: {client_id}")

    @sio.on("subscribe")
    def handle_subscribe(data):
        """
        Handle client subscription to metric channels.

        Args:
            data: Dictionary with 'channels' key containing list of channel names.
        """
        from flask import request

        client_id = request.sid

        if not isinstance(data, dict):
            emit("error", {"message": "Invalid subscription data format"})
            return

        channels = data.get("channels", [])

        if not isinstance(channels, list):
            channels = [channels]

        subscribed = []
        invalid = []

        for channel in channels:
            if channel in METRIC_CHANNELS:
                join_room(channel)
                with _clients_lock:
                    if client_id in _connected_clients:
                        _connected_clients[client_id]["subscriptions"].add(channel)
                subscribed.append(channel)
                logger.debug(f"Client {client_id} subscribed to {channel}")
            else:
                invalid.append(channel)

        emit("subscribed", {
            "channels": subscribed,
            "invalid_channels": invalid,
        })

        # Send immediate data for newly subscribed channels
        if subscribed:
            _send_initial_data_for_channels(subscribed)

    @sio.on("unsubscribe")
    def handle_unsubscribe(data):
        """
        Handle client unsubscription from metric channels.

        Args:
            data: Dictionary with 'channels' key containing list of channel names.
        """
        from flask import request

        client_id = request.sid

        if not isinstance(data, dict):
            emit("error", {"message": "Invalid unsubscription data format"})
            return

        channels = data.get("channels", [])

        if not isinstance(channels, list):
            channels = [channels]

        unsubscribed = []

        for channel in channels:
            if channel in METRIC_CHANNELS:
                leave_room(channel)
                with _clients_lock:
                    if client_id in _connected_clients:
                        _connected_clients[client_id]["subscriptions"].discard(channel)
                unsubscribed.append(channel)
                logger.debug(f"Client {client_id} unsubscribed from {channel}")

        emit("unsubscribed", {"channels": unsubscribed})

    @sio.on("get_channels")
    def handle_get_channels():
        """Send list of available metric channels."""
        emit("channels", {
            "channels": METRIC_CHANNELS,
            "push_interval_seconds": STATS_PUSH_INTERVAL,
        })

    @sio.on("ping_broker")
    def handle_ping_broker():
        """Check broker connection status and send response."""
        from app.mqtt_client import get_mqtt_client

        mqtt_client = get_mqtt_client()
        sys_monitor = get_sys_monitor()

        emit("broker_status", {
            "connected": mqtt_client.is_connected if mqtt_client else False,
            "sys_monitor_subscribed": sys_monitor.is_subscribed if sys_monitor else False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })


def _send_initial_data_for_channels(channels: list[str]) -> None:
    """
    Send initial data for newly subscribed channels.

    Args:
        channels: List of channel names to send data for.
    """
    try:
        sys_monitor = get_sys_monitor()
        stats = sys_monitor.get_stats()

        for channel in channels:
            data = _prepare_channel_data(channel, stats)
            if data:
                emit(f"{channel}_update", data)

    except Exception as e:
        logger.error(f"Error sending initial channel data: {e}")


def _prepare_channel_data(channel: str, stats: BrokerStats) -> Optional[dict]:
    """
    Prepare data payload for a specific metric channel.

    Args:
        channel: The metric channel name.
        stats: Current broker statistics.

    Returns:
        Dictionary with channel-specific data, or None if channel unknown.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    if channel == "broker_stats":
        return {
            "data": stats.to_dict(),
            "timestamp": timestamp,
        }

    elif channel == "broker_summary":
        return {
            "data": stats.to_summary_dict(),
            "timestamp": timestamp,
        }

    elif channel == "clients":
        return {
            "data": {
                "connected": stats.clients_connected,
                "disconnected": stats.clients_disconnected,
                "total": stats.clients_total,
                "maximum": stats.clients_maximum,
                "expired": stats.clients_expired,
                "connection_rate": {
                    "1min": stats.load_connections_1min,
                    "5min": stats.load_connections_5min,
                    "15min": stats.load_connections_15min,
                },
            },
            "timestamp": timestamp,
        }

    elif channel == "messages":
        return {
            "data": {
                "received": stats.messages_received,
                "sent": stats.messages_sent,
                "stored": stats.messages_stored,
                "inflight": stats.messages_inflight,
                "dropped": stats.messages_dropped,
                "publish_received": stats.publish_messages_received,
                "publish_sent": stats.publish_messages_sent,
                "publish_dropped": stats.publish_messages_dropped,
                "rate": {
                    "received_1min": stats.load_messages_received_1min,
                    "received_5min": stats.load_messages_received_5min,
                    "received_15min": stats.load_messages_received_15min,
                    "sent_1min": stats.load_messages_sent_1min,
                    "sent_5min": stats.load_messages_sent_5min,
                    "sent_15min": stats.load_messages_sent_15min,
                },
            },
            "timestamp": timestamp,
        }

    elif channel == "bytes":
        return {
            "data": {
                "received": stats.bytes_received,
                "sent": stats.bytes_sent,
                "rate": {
                    "received_1min": stats.load_bytes_received_1min,
                    "received_5min": stats.load_bytes_received_5min,
                    "received_15min": stats.load_bytes_received_15min,
                    "sent_1min": stats.load_bytes_sent_1min,
                    "sent_5min": stats.load_bytes_sent_5min,
                    "sent_15min": stats.load_bytes_sent_15min,
                },
            },
            "timestamp": timestamp,
        }

    elif channel == "load":
        return {
            "data": {
                "messages": {
                    "received": {
                        "1min": stats.load_messages_received_1min,
                        "5min": stats.load_messages_received_5min,
                        "15min": stats.load_messages_received_15min,
                    },
                    "sent": {
                        "1min": stats.load_messages_sent_1min,
                        "5min": stats.load_messages_sent_5min,
                        "15min": stats.load_messages_sent_15min,
                    },
                },
                "bytes": {
                    "received": {
                        "1min": stats.load_bytes_received_1min,
                        "5min": stats.load_bytes_received_5min,
                        "15min": stats.load_bytes_received_15min,
                    },
                    "sent": {
                        "1min": stats.load_bytes_sent_1min,
                        "5min": stats.load_bytes_sent_5min,
                        "15min": stats.load_bytes_sent_15min,
                    },
                },
                "connections": {
                    "1min": stats.load_connections_1min,
                    "5min": stats.load_connections_5min,
                    "15min": stats.load_connections_15min,
                },
                "publish": {
                    "received": {
                        "1min": stats.load_publish_received_1min,
                        "5min": stats.load_publish_received_5min,
                        "15min": stats.load_publish_received_15min,
                    },
                    "sent": {
                        "1min": stats.load_publish_sent_1min,
                        "5min": stats.load_publish_sent_5min,
                        "15min": stats.load_publish_sent_15min,
                    },
                },
                "sockets": {
                    "1min": stats.load_sockets_1min,
                    "5min": stats.load_sockets_5min,
                    "15min": stats.load_sockets_15min,
                },
            },
            "timestamp": timestamp,
        }

    return None


def broadcast_stats() -> None:
    """
    Broadcast current broker statistics to all subscribed clients.

    This function is called periodically by the background task to push
    real-time updates to connected WebSocket clients.
    """
    if socketio is None:
        return

    try:
        sys_monitor = get_sys_monitor()

        if not sys_monitor.is_subscribed:
            return

        stats = sys_monitor.get_stats()

        # Broadcast to each channel
        for channel in METRIC_CHANNELS:
            data = _prepare_channel_data(channel, stats)
            if data:
                socketio.emit(f"{channel}_update", data, room=channel)

    except Exception as e:
        logger.error(f"Error broadcasting stats: {e}")


def start_background_stats_pusher() -> threading.Thread:
    """
    Start a background thread that periodically pushes broker stats.

    Returns:
        The background thread instance.
    """

    def stats_pusher_loop():
        """Background loop that pushes stats at regular intervals."""
        import time

        logger.info(
            f"Starting background stats pusher (interval: {STATS_PUSH_INTERVAL}s)"
        )

        while True:
            try:
                time.sleep(STATS_PUSH_INTERVAL)
                broadcast_stats()
            except Exception as e:
                logger.error(f"Error in stats pusher loop: {e}")

    thread = threading.Thread(target=stats_pusher_loop, daemon=True)
    thread.start()

    return thread


def get_connected_client_count() -> int:
    """
    Get the number of currently connected WebSocket clients.

    Returns:
        Number of connected clients.
    """
    with _clients_lock:
        return len(_connected_clients)


def get_connected_clients_info() -> list[dict]:
    """
    Get information about all connected WebSocket clients.

    Returns:
        List of dictionaries containing client information.
    """
    with _clients_lock:
        return [
            {
                "client_id": client_id,
                "connected_at": info["connected_at"],
                "ip": info["ip"],
                "subscriptions": list(info["subscriptions"]),
            }
            for client_id, info in _connected_clients.items()
        ]
