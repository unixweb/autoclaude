"""
System Topics Monitor Service

This module provides a service that subscribes to Mosquitto $SYS/# topics
to collect and cache broker statistics in real-time.
"""

import logging
import threading
from datetime import datetime, timezone
from typing import Callable, Optional

from app.models.broker_stats import BrokerStats
from app.mqtt_client import MQTTClient, get_mqtt_client

logger = logging.getLogger(__name__)


# Mapping of $SYS topic suffixes to BrokerStats attributes
TOPIC_MAPPINGS: dict[str, tuple[str, type]] = {
    # Broker information
    "$SYS/broker/version": ("version", str),
    "$SYS/broker/uptime": ("uptime", int),
    # Client statistics
    "$SYS/broker/clients/connected": ("clients_connected", int),
    "$SYS/broker/clients/disconnected": ("clients_disconnected", int),
    "$SYS/broker/clients/total": ("clients_total", int),
    "$SYS/broker/clients/maximum": ("clients_maximum", int),
    "$SYS/broker/clients/expired": ("clients_expired", int),
    # Message statistics
    "$SYS/broker/messages/received": ("messages_received", int),
    "$SYS/broker/messages/sent": ("messages_sent", int),
    "$SYS/broker/messages/stored": ("messages_stored", int),
    "$SYS/broker/messages/inflight": ("messages_inflight", int),
    "$SYS/broker/messages/dropped": ("messages_dropped", int),
    # Publish statistics
    "$SYS/broker/publish/messages/received": ("publish_messages_received", int),
    "$SYS/broker/publish/messages/sent": ("publish_messages_sent", int),
    "$SYS/broker/publish/messages/dropped": ("publish_messages_dropped", int),
    # Byte statistics
    "$SYS/broker/bytes/received": ("bytes_received", int),
    "$SYS/broker/bytes/sent": ("bytes_sent", int),
    # Subscription statistics
    "$SYS/broker/subscriptions/count": ("subscriptions_count", int),
    # Retained messages
    "$SYS/broker/retained messages/count": ("retained_messages_count", int),
    # Load statistics (messages per interval)
    "$SYS/broker/load/messages/received/1min": ("load_messages_received_1min", float),
    "$SYS/broker/load/messages/received/5min": ("load_messages_received_5min", float),
    "$SYS/broker/load/messages/received/15min": ("load_messages_received_15min", float),
    "$SYS/broker/load/messages/sent/1min": ("load_messages_sent_1min", float),
    "$SYS/broker/load/messages/sent/5min": ("load_messages_sent_5min", float),
    "$SYS/broker/load/messages/sent/15min": ("load_messages_sent_15min", float),
    "$SYS/broker/load/bytes/received/1min": ("load_bytes_received_1min", float),
    "$SYS/broker/load/bytes/received/5min": ("load_bytes_received_5min", float),
    "$SYS/broker/load/bytes/received/15min": ("load_bytes_received_15min", float),
    "$SYS/broker/load/bytes/sent/1min": ("load_bytes_sent_1min", float),
    "$SYS/broker/load/bytes/sent/5min": ("load_bytes_sent_5min", float),
    "$SYS/broker/load/bytes/sent/15min": ("load_bytes_sent_15min", float),
    "$SYS/broker/load/connections/1min": ("load_connections_1min", float),
    "$SYS/broker/load/connections/5min": ("load_connections_5min", float),
    "$SYS/broker/load/connections/15min": ("load_connections_15min", float),
    "$SYS/broker/load/publish/received/1min": ("load_publish_received_1min", float),
    "$SYS/broker/load/publish/received/5min": ("load_publish_received_5min", float),
    "$SYS/broker/load/publish/received/15min": ("load_publish_received_15min", float),
    "$SYS/broker/load/publish/sent/1min": ("load_publish_sent_1min", float),
    "$SYS/broker/load/publish/sent/5min": ("load_publish_sent_5min", float),
    "$SYS/broker/load/publish/sent/15min": ("load_publish_sent_15min", float),
    "$SYS/broker/load/sockets/1min": ("load_sockets_1min", float),
    "$SYS/broker/load/sockets/5min": ("load_sockets_5min", float),
    "$SYS/broker/load/sockets/15min": ("load_sockets_15min", float),
    # Heap memory usage
    "$SYS/broker/heap/current": ("heap_current", int),
    "$SYS/broker/heap/maximum": ("heap_maximum", int),
}


class SysMonitor:
    """
    Service for monitoring Mosquitto broker statistics via $SYS topics.

    This service subscribes to the $SYS/# topic hierarchy and maintains
    an up-to-date cache of broker statistics.
    """

    def __init__(self, mqtt_client: Optional[MQTTClient] = None):
        """
        Initialize the SysMonitor service.

        Args:
            mqtt_client: MQTT client instance. If None, uses the global client.
        """
        self._mqtt_client = mqtt_client
        self._stats = BrokerStats()
        self._lock = threading.Lock()
        self._subscribed = False
        self._update_callbacks: list[Callable[[BrokerStats], None]] = []

    @property
    def mqtt_client(self) -> MQTTClient:
        """Get the MQTT client, using global if not set."""
        if self._mqtt_client is None:
            self._mqtt_client = get_mqtt_client()
        return self._mqtt_client

    @property
    def is_subscribed(self) -> bool:
        """Check if the service is subscribed to $SYS topics."""
        with self._lock:
            return self._subscribed

    def get_stats(self) -> BrokerStats:
        """
        Get the current broker statistics.

        Returns:
            Current BrokerStats instance (copy to prevent modification).
        """
        with self._lock:
            # Return a copy to prevent external modification
            return BrokerStats(
                version=self._stats.version,
                uptime=self._stats.uptime,
                clients_connected=self._stats.clients_connected,
                clients_disconnected=self._stats.clients_disconnected,
                clients_total=self._stats.clients_total,
                clients_maximum=self._stats.clients_maximum,
                clients_expired=self._stats.clients_expired,
                messages_received=self._stats.messages_received,
                messages_sent=self._stats.messages_sent,
                messages_stored=self._stats.messages_stored,
                messages_inflight=self._stats.messages_inflight,
                messages_dropped=self._stats.messages_dropped,
                publish_messages_received=self._stats.publish_messages_received,
                publish_messages_sent=self._stats.publish_messages_sent,
                publish_messages_dropped=self._stats.publish_messages_dropped,
                bytes_received=self._stats.bytes_received,
                bytes_sent=self._stats.bytes_sent,
                subscriptions_count=self._stats.subscriptions_count,
                retained_messages_count=self._stats.retained_messages_count,
                load_messages_received_1min=self._stats.load_messages_received_1min,
                load_messages_received_5min=self._stats.load_messages_received_5min,
                load_messages_received_15min=self._stats.load_messages_received_15min,
                load_messages_sent_1min=self._stats.load_messages_sent_1min,
                load_messages_sent_5min=self._stats.load_messages_sent_5min,
                load_messages_sent_15min=self._stats.load_messages_sent_15min,
                load_bytes_received_1min=self._stats.load_bytes_received_1min,
                load_bytes_received_5min=self._stats.load_bytes_received_5min,
                load_bytes_received_15min=self._stats.load_bytes_received_15min,
                load_bytes_sent_1min=self._stats.load_bytes_sent_1min,
                load_bytes_sent_5min=self._stats.load_bytes_sent_5min,
                load_bytes_sent_15min=self._stats.load_bytes_sent_15min,
                load_connections_1min=self._stats.load_connections_1min,
                load_connections_5min=self._stats.load_connections_5min,
                load_connections_15min=self._stats.load_connections_15min,
                load_publish_received_1min=self._stats.load_publish_received_1min,
                load_publish_received_5min=self._stats.load_publish_received_5min,
                load_publish_received_15min=self._stats.load_publish_received_15min,
                load_publish_sent_1min=self._stats.load_publish_sent_1min,
                load_publish_sent_5min=self._stats.load_publish_sent_5min,
                load_publish_sent_15min=self._stats.load_publish_sent_15min,
                load_sockets_1min=self._stats.load_sockets_1min,
                load_sockets_5min=self._stats.load_sockets_5min,
                load_sockets_15min=self._stats.load_sockets_15min,
                heap_current=self._stats.heap_current,
                heap_maximum=self._stats.heap_maximum,
                last_updated=self._stats.last_updated,
            )

    def subscribe(self) -> bool:
        """
        Subscribe to $SYS/# topics to receive broker statistics.

        Returns:
            True if subscription was successful, False otherwise.
        """
        if self._subscribed:
            logger.debug("Already subscribed to $SYS topics")
            return True

        if not self.mqtt_client.is_connected:
            logger.warning("Cannot subscribe to $SYS topics: MQTT client not connected")
            return False

        try:
            success = self.mqtt_client.subscribe(
                topic="$SYS/#",
                callback=self._on_sys_message,
                qos=0,
            )

            if success:
                with self._lock:
                    self._subscribed = True
                logger.info("Subscribed to $SYS/# topics for broker monitoring")
            else:
                logger.error("Failed to subscribe to $SYS/# topics")

            return success

        except Exception as e:
            logger.error(f"Error subscribing to $SYS topics: {e}")
            return False

    def unsubscribe(self) -> bool:
        """
        Unsubscribe from $SYS/# topics.

        Returns:
            True if unsubscription was successful, False otherwise.
        """
        if not self._subscribed:
            return True

        try:
            success = self.mqtt_client.unsubscribe("$SYS/#")

            if success:
                with self._lock:
                    self._subscribed = False
                logger.info("Unsubscribed from $SYS/# topics")

            return success

        except Exception as e:
            logger.error(f"Error unsubscribing from $SYS topics: {e}")
            return False

    def add_update_callback(
        self, callback: Callable[[BrokerStats], None]
    ) -> None:
        """
        Register a callback to be called when stats are updated.

        Args:
            callback: Function to call with updated BrokerStats.
        """
        with self._lock:
            self._update_callbacks.append(callback)

    def remove_update_callback(
        self, callback: Callable[[BrokerStats], None]
    ) -> None:
        """
        Remove a previously registered update callback.

        Args:
            callback: The callback function to remove.
        """
        with self._lock:
            if callback in self._update_callbacks:
                self._update_callbacks.remove(callback)

    def _on_sys_message(self, topic: str, payload: str) -> None:
        """
        Handle incoming $SYS topic messages.

        Args:
            topic: The MQTT topic.
            payload: The message payload.
        """
        mapping = TOPIC_MAPPINGS.get(topic)
        if mapping is None:
            # Unknown topic, ignore silently
            return

        attr_name, value_type = mapping

        try:
            # Parse the value according to expected type
            if value_type == int:
                value = int(payload)
            elif value_type == float:
                value = float(payload)
            else:
                value = str(payload)

            # Update the stats
            with self._lock:
                setattr(self._stats, attr_name, value)
                self._stats.last_updated = datetime.now(timezone.utc)

                # Get callbacks to notify
                callbacks = list(self._update_callbacks)
                current_stats = self.get_stats()

            # Notify callbacks outside the lock
            for callback in callbacks:
                try:
                    callback(current_stats)
                except Exception as e:
                    logger.error(f"Error in stats update callback: {e}")

        except ValueError as e:
            logger.debug(f"Failed to parse $SYS topic {topic} value '{payload}': {e}")
        except Exception as e:
            logger.error(f"Error processing $SYS message from {topic}: {e}")


# Global SysMonitor instance
_sys_monitor: Optional[SysMonitor] = None


def get_sys_monitor() -> SysMonitor:
    """
    Get the global SysMonitor instance.

    Returns:
        The global SysMonitor instance.
    """
    global _sys_monitor
    if _sys_monitor is None:
        _sys_monitor = SysMonitor()
    return _sys_monitor


def init_sys_monitor(mqtt_client: Optional[MQTTClient] = None) -> SysMonitor:
    """
    Initialize and start the global SysMonitor service.

    This function creates the SysMonitor instance and subscribes to $SYS topics.

    Args:
        mqtt_client: Optional MQTT client instance. Uses global if not provided.

    Returns:
        The initialized SysMonitor instance.
    """
    global _sys_monitor
    _sys_monitor = SysMonitor(mqtt_client)

    # Subscribe to $SYS topics
    if _sys_monitor.mqtt_client.is_connected:
        _sys_monitor.subscribe()
    else:
        logger.warning(
            "MQTT client not connected during SysMonitor initialization. "
            "Stats subscription will be attempted on reconnection."
        )

    return _sys_monitor
