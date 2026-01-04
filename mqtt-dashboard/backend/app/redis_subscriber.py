"""
Redis Subscriber for Dashboard

Subscribes to Redis channels and forwards messages to WebSocket clients.
"""

import logging
from typing import Optional

from app.redis_client import RedisClient, get_redis_client
from app.redis_channels import RedisChannels, MessageTypes

logger = logging.getLogger(__name__)


class DashboardRedisSubscriber:
    """
    Subscribes to Redis channels from MQTT bridge.
    Forwards messages to WebSocket handlers.
    """

    def __init__(self, redis_client: Optional[RedisClient] = None):
        """Initialize subscriber."""
        self.redis_client = redis_client or get_redis_client()
        self._stats_callback = None
        self._status_callback = None
        self._message_callback = None

    def start(self) -> None:
        """Start subscribing to Redis channels."""
        import threading

        def _subscribe_in_thread():
            """Subscribe to channels in a background thread."""
            logger.info("Starting Redis subscriptions for dashboard...")

            # Subscribe to broker stats
            self.redis_client.subscribe(
                RedisChannels.BROKER_STATS,
                self._handle_stats_update,
            )

            # Subscribe to broker status
            self.redis_client.subscribe(
                RedisChannels.BROKER_STATUS,
                self._handle_status_update,
            )

            # Subscribe to MQTT messages
            self.redis_client.subscribe(
                RedisChannels.MQTT_MESSAGES,
                self._handle_mqtt_message,
            )

            logger.info("Redis subscriptions active")

        # Start subscriptions in a separate thread to avoid blocking app startup
        thread = threading.Thread(target=_subscribe_in_thread, daemon=True)
        thread.start()
        logger.info("Redis subscriber initialization started in background")

    def set_stats_callback(self, callback):
        """Set callback for stats updates."""
        self._stats_callback = callback

    def set_status_callback(self, callback):
        """Set callback for status updates."""
        self._status_callback = callback

    def set_message_callback(self, callback):
        """Set callback for MQTT messages."""
        self._message_callback = callback

    def _handle_stats_update(self, message: dict) -> None:
        """Handle broker stats update from Redis."""
        if message.get("type") == MessageTypes.STATS_UPDATE:
            if self._stats_callback:
                self._stats_callback(message.get("data", {}))

    def _handle_status_update(self, message: dict) -> None:
        """Handle broker status update from Redis."""
        if message.get("type") == MessageTypes.STATUS_CHANGE:
            if self._status_callback:
                self._status_callback(message)

    def _handle_mqtt_message(self, message: dict) -> None:
        """Handle MQTT message from Redis (not used - kept for compatibility)."""
        if message.get("type") == MessageTypes.MESSAGE_RECEIVED:
            # Messages now come directly via MQTT, not Redis
            # This handler is kept for future use if needed
            if self._message_callback:
                self._message_callback(message)


# Global subscriber instance
_subscriber: Optional[DashboardRedisSubscriber] = None


def get_redis_subscriber() -> DashboardRedisSubscriber:
    """Get global Redis subscriber instance."""
    global _subscriber
    if _subscriber is None:
        _subscriber = DashboardRedisSubscriber()
    return _subscriber


def init_redis_subscriber(redis_client: Optional[RedisClient] = None) -> DashboardRedisSubscriber:
    """Initialize and start Redis subscriber.

    Args:
        redis_client: Optional RedisClient instance to use. If not provided,
                      will use the global singleton.
    """
    global _subscriber
    _subscriber = DashboardRedisSubscriber(redis_client=redis_client)
    _subscriber.start()
    return _subscriber
