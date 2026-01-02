"""
Broker Statistics Model

This module defines the data model for Mosquitto broker statistics
collected from $SYS topics.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


@dataclass
class BrokerStats:
    """
    Data model for Mosquitto broker statistics.

    These statistics are collected from the $SYS/broker/# topic hierarchy.
    See: https://mosquitto.org/man/mosquitto-8.html for topic documentation.
    """

    # Broker information
    version: Optional[str] = None
    uptime: Optional[int] = None  # Uptime in seconds

    # Client statistics
    clients_connected: Optional[int] = None
    clients_disconnected: Optional[int] = None
    clients_total: Optional[int] = None
    clients_maximum: Optional[int] = None
    clients_expired: Optional[int] = None

    # Message statistics
    messages_received: Optional[int] = None
    messages_sent: Optional[int] = None
    messages_stored: Optional[int] = None
    messages_inflight: Optional[int] = None
    messages_dropped: Optional[int] = None

    # Publish statistics
    publish_messages_received: Optional[int] = None
    publish_messages_sent: Optional[int] = None
    publish_messages_dropped: Optional[int] = None

    # Byte statistics
    bytes_received: Optional[int] = None
    bytes_sent: Optional[int] = None

    # Subscription statistics
    subscriptions_count: Optional[int] = None

    # Retained messages
    retained_messages_count: Optional[int] = None

    # Load statistics (messages per interval)
    load_messages_received_1min: Optional[float] = None
    load_messages_received_5min: Optional[float] = None
    load_messages_received_15min: Optional[float] = None
    load_messages_sent_1min: Optional[float] = None
    load_messages_sent_5min: Optional[float] = None
    load_messages_sent_15min: Optional[float] = None
    load_bytes_received_1min: Optional[float] = None
    load_bytes_received_5min: Optional[float] = None
    load_bytes_received_15min: Optional[float] = None
    load_bytes_sent_1min: Optional[float] = None
    load_bytes_sent_5min: Optional[float] = None
    load_bytes_sent_15min: Optional[float] = None
    load_connections_1min: Optional[float] = None
    load_connections_5min: Optional[float] = None
    load_connections_15min: Optional[float] = None
    load_publish_received_1min: Optional[float] = None
    load_publish_received_5min: Optional[float] = None
    load_publish_received_15min: Optional[float] = None
    load_publish_sent_1min: Optional[float] = None
    load_publish_sent_5min: Optional[float] = None
    load_publish_sent_15min: Optional[float] = None
    load_sockets_1min: Optional[float] = None
    load_sockets_5min: Optional[float] = None
    load_sockets_15min: Optional[float] = None

    # Heap memory usage
    heap_current: Optional[int] = None
    heap_maximum: Optional[int] = None

    # Timestamp of last update
    last_updated: datetime = field(default_factory=_utc_now)

    def to_dict(self) -> dict:
        """
        Convert the broker stats to a dictionary.

        Returns:
            Dictionary representation of the broker statistics.
        """
        return {
            "broker": {
                "version": self.version,
                "uptime": self.uptime,
            },
            "clients": {
                "connected": self.clients_connected,
                "disconnected": self.clients_disconnected,
                "total": self.clients_total,
                "maximum": self.clients_maximum,
                "expired": self.clients_expired,
            },
            "messages": {
                "received": self.messages_received,
                "sent": self.messages_sent,
                "stored": self.messages_stored,
                "inflight": self.messages_inflight,
                "dropped": self.messages_dropped,
            },
            "publish": {
                "received": self.publish_messages_received,
                "sent": self.publish_messages_sent,
                "dropped": self.publish_messages_dropped,
            },
            "bytes": {
                "received": self.bytes_received,
                "sent": self.bytes_sent,
            },
            "subscriptions": {
                "count": self.subscriptions_count,
            },
            "retained": {
                "count": self.retained_messages_count,
            },
            "load": {
                "messages_received": {
                    "1min": self.load_messages_received_1min,
                    "5min": self.load_messages_received_5min,
                    "15min": self.load_messages_received_15min,
                },
                "messages_sent": {
                    "1min": self.load_messages_sent_1min,
                    "5min": self.load_messages_sent_5min,
                    "15min": self.load_messages_sent_15min,
                },
                "bytes_received": {
                    "1min": self.load_bytes_received_1min,
                    "5min": self.load_bytes_received_5min,
                    "15min": self.load_bytes_received_15min,
                },
                "bytes_sent": {
                    "1min": self.load_bytes_sent_1min,
                    "5min": self.load_bytes_sent_5min,
                    "15min": self.load_bytes_sent_15min,
                },
                "connections": {
                    "1min": self.load_connections_1min,
                    "5min": self.load_connections_5min,
                    "15min": self.load_connections_15min,
                },
                "publish_received": {
                    "1min": self.load_publish_received_1min,
                    "5min": self.load_publish_received_5min,
                    "15min": self.load_publish_received_15min,
                },
                "publish_sent": {
                    "1min": self.load_publish_sent_1min,
                    "5min": self.load_publish_sent_5min,
                    "15min": self.load_publish_sent_15min,
                },
                "sockets": {
                    "1min": self.load_sockets_1min,
                    "5min": self.load_sockets_5min,
                    "15min": self.load_sockets_15min,
                },
            },
            "heap": {
                "current": self.heap_current,
                "maximum": self.heap_maximum,
            },
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }

    def to_summary_dict(self) -> dict:
        """
        Convert to a summary dictionary with key metrics only.

        Returns:
            Dictionary with essential broker statistics.
        """
        return {
            "version": self.version,
            "uptime": self.uptime,
            "clients_connected": self.clients_connected,
            "clients_total": self.clients_total,
            "messages_received": self.messages_received,
            "messages_sent": self.messages_sent,
            "bytes_received": self.bytes_received,
            "bytes_sent": self.bytes_sent,
            "subscriptions": self.subscriptions_count,
            "retained_messages": self.retained_messages_count,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }
