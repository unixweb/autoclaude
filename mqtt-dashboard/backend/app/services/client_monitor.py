"""
Client Monitor Service

This module provides a service for monitoring MQTT client connections
by leveraging the SysMonitor service's cached broker statistics.
"""

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional

from app.models.broker_stats import BrokerStats
from app.services.sys_monitor import SysMonitor, get_sys_monitor

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


@dataclass
class ClientStats:
    """
    Data model for MQTT client statistics.

    These statistics are derived from Mosquitto's $SYS topics for client counts.
    """

    # Current client counts
    connected: Optional[int] = None
    disconnected: Optional[int] = None
    total: Optional[int] = None
    maximum: Optional[int] = None
    expired: Optional[int] = None

    # Connection rate metrics (derived from load stats)
    connections_1min: Optional[float] = None
    connections_5min: Optional[float] = None
    connections_15min: Optional[float] = None

    # Timestamp of last update
    last_updated: datetime = field(default_factory=_utc_now)

    def to_dict(self) -> dict:
        """
        Convert client stats to a dictionary.

        Returns:
            Dictionary representation of client statistics.
        """
        return {
            "connected": self.connected,
            "disconnected": self.disconnected,
            "total": self.total,
            "maximum": self.maximum,
            "expired": self.expired,
            "connection_rate": {
                "1min": self.connections_1min,
                "5min": self.connections_5min,
                "15min": self.connections_15min,
            },
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }

    def to_count_dict(self) -> dict:
        """
        Convert to a simplified count dictionary.

        Returns:
            Dictionary with essential count statistics.
        """
        return {
            "connected": self.connected,
            "disconnected": self.disconnected,
            "total": self.total,
            "maximum": self.maximum,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }


class ClientMonitor:
    """
    Service for monitoring MQTT client connections.

    This service provides an interface for accessing client-related statistics
    from the underlying SysMonitor service. It caches client stats and can
    track historical connection data.
    """

    def __init__(self, sys_monitor: Optional[SysMonitor] = None):
        """
        Initialize the ClientMonitor service.

        Args:
            sys_monitor: SysMonitor instance. If None, uses the global instance.
        """
        self._sys_monitor = sys_monitor
        self._lock = threading.Lock()
        self._update_callbacks: list[Callable[[ClientStats], None]] = []
        self._last_stats: Optional[ClientStats] = None

    @property
    def sys_monitor(self) -> SysMonitor:
        """Get the SysMonitor, using global if not set."""
        if self._sys_monitor is None:
            self._sys_monitor = get_sys_monitor()
        return self._sys_monitor

    def _extract_client_stats(self, broker_stats: BrokerStats) -> ClientStats:
        """
        Extract client statistics from broker stats.

        Args:
            broker_stats: Full broker statistics from SysMonitor.

        Returns:
            ClientStats with extracted client information.
        """
        return ClientStats(
            connected=broker_stats.clients_connected,
            disconnected=broker_stats.clients_disconnected,
            total=broker_stats.clients_total,
            maximum=broker_stats.clients_maximum,
            expired=broker_stats.clients_expired,
            connections_1min=broker_stats.load_connections_1min,
            connections_5min=broker_stats.load_connections_5min,
            connections_15min=broker_stats.load_connections_15min,
            last_updated=broker_stats.last_updated,
        )

    def get_client_stats(self) -> ClientStats:
        """
        Get the current client statistics.

        Returns:
            Current ClientStats instance.
        """
        broker_stats = self.sys_monitor.get_stats()
        client_stats = self._extract_client_stats(broker_stats)

        with self._lock:
            self._last_stats = client_stats

        return client_stats

    def get_connected_count(self) -> Optional[int]:
        """
        Get the count of currently connected clients.

        Returns:
            Number of connected clients, or None if not available.
        """
        broker_stats = self.sys_monitor.get_stats()
        return broker_stats.clients_connected

    def get_active_count(self) -> Optional[int]:
        """
        Get the count of active clients (connected clients).

        Active clients are those currently connected to the broker.

        Returns:
            Number of active/connected clients, or None if not available.
        """
        return self.get_connected_count()

    def get_total_count(self) -> Optional[int]:
        """
        Get the total client count (connected + disconnected persistent).

        Returns:
            Total number of tracked clients, or None if not available.
        """
        broker_stats = self.sys_monitor.get_stats()
        return broker_stats.clients_total

    def get_client_list(self) -> dict:
        """
        Get client information as a list-like structure.

        Note: Mosquitto's $SYS topics do not expose individual client IDs.
        This method returns aggregate statistics about clients with
        categorization for display purposes.

        Returns:
            Dictionary with client categories and counts.
        """
        stats = self.get_client_stats()

        # Build a structured response showing client distribution
        client_list = {
            "summary": {
                "total_tracked": stats.total,
                "currently_connected": stats.connected,
                "persistent_disconnected": stats.disconnected,
                "expired_sessions": stats.expired,
                "peak_connections": stats.maximum,
            },
            "categories": [
                {
                    "name": "Connected",
                    "description": "Clients currently connected to the broker",
                    "count": stats.connected,
                    "status": "online",
                },
                {
                    "name": "Disconnected (Persistent)",
                    "description": "Persistent clients that are currently disconnected",
                    "count": stats.disconnected,
                    "status": "offline",
                },
                {
                    "name": "Expired",
                    "description": "Clients whose sessions have expired and been removed",
                    "count": stats.expired,
                    "status": "expired",
                },
            ],
            "connection_activity": {
                "rate_1min": stats.connections_1min,
                "rate_5min": stats.connections_5min,
                "rate_15min": stats.connections_15min,
            },
            "last_updated": stats.last_updated.isoformat() if stats.last_updated else None,
        }

        return client_list

    def add_update_callback(
        self, callback: Callable[[ClientStats], None]
    ) -> None:
        """
        Register a callback to be called when client stats are updated.

        Args:
            callback: Function to call with updated ClientStats.
        """
        with self._lock:
            self._update_callbacks.append(callback)

        # Also register with the underlying sys_monitor
        def broker_stats_callback(broker_stats: BrokerStats) -> None:
            client_stats = self._extract_client_stats(broker_stats)
            try:
                callback(client_stats)
            except Exception as e:
                logger.error(f"Error in client stats update callback: {e}")

        # Store the wrapper for potential removal later
        self.sys_monitor.add_update_callback(broker_stats_callback)

    def remove_update_callback(
        self, callback: Callable[[ClientStats], None]
    ) -> None:
        """
        Remove a previously registered update callback.

        Args:
            callback: The callback function to remove.
        """
        with self._lock:
            if callback in self._update_callbacks:
                self._update_callbacks.remove(callback)


# Global ClientMonitor instance
_client_monitor: Optional[ClientMonitor] = None


def get_client_monitor() -> ClientMonitor:
    """
    Get the global ClientMonitor instance.

    Returns:
        The global ClientMonitor instance.
    """
    global _client_monitor
    if _client_monitor is None:
        _client_monitor = ClientMonitor()
    return _client_monitor


def init_client_monitor(sys_monitor: Optional[SysMonitor] = None) -> ClientMonitor:
    """
    Initialize the global ClientMonitor service.

    Args:
        sys_monitor: Optional SysMonitor instance. Uses global if not provided.

    Returns:
        The initialized ClientMonitor instance.
    """
    global _client_monitor
    _client_monitor = ClientMonitor(sys_monitor)
    logger.info("ClientMonitor service initialized")
    return _client_monitor
