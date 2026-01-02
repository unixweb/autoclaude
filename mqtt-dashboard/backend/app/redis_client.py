"""Redis client for pub/sub communication between MQTT service and dashboard.

This module provides a thread-safe Redis pub/sub client for decoupling
the MQTT client service from the dashboard application.

Key features:
- Singleton pattern for global access
- Thread-safe pub/sub operations
- JSON message serialization
- Automatic reconnection handling
- Channel subscription with callbacks
"""

import json
import logging
import threading
from typing import Any, Callable, Dict, Optional

import redis

logger = logging.getLogger(__name__)


class RedisClient:
    """Thread-safe Redis pub/sub client.

    This client provides publish/subscribe capabilities for communication
    between the MQTT bridge service and the dashboard application.

    Example usage:
        # Initialize the client
        client = RedisClient(host='localhost', port=6379)

        # Publish a message
        client.publish('mqtt-events', {'event': 'message', 'topic': 'test'})

        # Subscribe to messages
        def on_message(data):
            print(f"Received: {data}")

        client.subscribe('mqtt-events', on_message)
    """

    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        decode_responses: bool = True
    ):
        """Initialize Redis client.

        Args:
            host: Redis server hostname
            port: Redis server port
            db: Redis database number
            password: Optional Redis password
            decode_responses: Whether to decode responses to strings
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password

        # Create Redis connection
        self._redis = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password if password else None,
            decode_responses=decode_responses,
            socket_connect_timeout=5,
            socket_keepalive=True,
            health_check_interval=30
        )

        # Pub/Sub instance
        self._pubsub = self._redis.pubsub(ignore_subscribe_messages=True)

        # Thread for listening to messages
        self._listener_thread: Optional[threading.Thread] = None
        self._running = False

        # Store subscriptions
        self._subscriptions: Dict[str, Callable[[Any], None]] = {}
        self._subscription_lock = threading.Lock()

        logger.info(f"Redis client initialized: {host}:{port}")

    def publish(self, channel: str, message: Any) -> None:
        """Publish a message to a Redis channel.

        Messages are automatically serialized to JSON.

        Args:
            channel: Channel name to publish to
            message: Message data (will be JSON-serialized)

        Raises:
            redis.RedisError: If publishing fails
        """
        try:
            # Serialize message to JSON
            if isinstance(message, (dict, list)):
                payload = json.dumps(message)
            elif isinstance(message, str):
                payload = message
            else:
                payload = json.dumps(str(message))

            # Publish to channel
            self._redis.publish(channel, payload)
            logger.debug(f"Published to {channel}: {payload[:100]}")

        except redis.RedisError as e:
            logger.error(f"Failed to publish to {channel}: {e}")
            raise
        except TypeError as e:
            logger.error(f"Failed to serialize message: {e}")
            raise

    def subscribe(self, channel: str, callback: Callable[[Any], None]) -> None:
        """Subscribe to a Redis channel with a callback.

        The callback will be invoked for each message received on the channel.
        Messages are automatically deserialized from JSON.

        Args:
            channel: Channel name to subscribe to
            callback: Function to call with received messages
        """
        with self._subscription_lock:
            # Store callback
            self._subscriptions[channel] = callback

            # Subscribe to channel
            self._pubsub.subscribe(channel)
            logger.info(f"Subscribed to channel: {channel}")

            # Start listener thread if not running
            if not self._running:
                self._start_subscriber_thread()

    def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a Redis channel.

        Args:
            channel: Channel name to unsubscribe from
        """
        with self._subscription_lock:
            if channel in self._subscriptions:
                del self._subscriptions[channel]
                self._pubsub.unsubscribe(channel)
                logger.info(f"Unsubscribed from channel: {channel}")

                # Stop listener if no more subscriptions
                if not self._subscriptions and self._running:
                    self._stop_listener()

    def _start_subscriber_thread(self) -> None:
        """Start the background listener thread."""
        with self._subscription_lock:
            if self._listener_thread is None or not self._listener_thread.is_alive():
                self._running = True
                self._listener_thread = threading.Thread(
                    target=self._subscriber_loop,
                    daemon=True,
                    name='RedisSubscriber'
                )
                self._listener_thread.start()
                logger.info("Redis subscriber thread started")

    def _stop_listener(self) -> None:
        """Stop the background listener thread."""
        self._running = False
        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=5)
            logger.info("Redis subscriber thread stopped")

    def _subscriber_loop(self) -> None:
        """Background loop for listening to subscribed channels."""
        logger.info("Redis listener loop started")

        try:
            while self._running:
                try:
                    # Get message from pub/sub (blocking with timeout)
                    message = self._pubsub.get_message(timeout=1.0)

                    if message and message['type'] == 'message':
                        channel = message['channel']
                        data = message['data']

                        # Get callback for this channel
                        with self._subscription_lock:
                            callback = self._subscriptions.get(channel)

                        if callback:
                            try:
                                # Try to deserialize JSON
                                try:
                                    parsed_data = json.loads(data)
                                except (json.JSONDecodeError, TypeError):
                                    # Not JSON, use raw data
                                    parsed_data = data

                                # Invoke callback
                                callback(parsed_data)

                            except Exception as e:
                                logger.error(
                                    f"Error in callback for {channel}: {e}",
                                    exc_info=True
                                )

                except redis.RedisError as e:
                    logger.error(f"Redis error in listener: {e}")
                    # Brief pause before retry
                    threading.Event().wait(1)

        except Exception as e:
            logger.error(f"Fatal error in listener loop: {e}", exc_info=True)
        finally:
            logger.info("Redis listener loop stopped")

    def is_connected(self) -> bool:
        """Check if connected to Redis.

        Returns:
            True if connected, False otherwise
        """
        try:
            self._redis.ping()
            return True
        except Exception:
            return False

    def disconnect(self) -> None:
        """Close the Redis connection and stop listener."""
        logger.info("Closing Redis client")
        self._stop_listener()
        self._pubsub.close()
        self._redis.close()

    def ping(self) -> bool:
        """Test Redis connection.

        Returns:
            True if connection is alive, False otherwise
        """
        try:
            return self._redis.ping()
        except redis.RedisError as e:
            logger.error(f"Redis ping failed: {e}")
            return False

    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.disconnect()
        except Exception:
            pass


# Global singleton instance
_redis_client: Optional[RedisClient] = None
_client_lock = threading.Lock()


def init_redis_client(
    host: str = 'localhost',
    port: int = 6379,
    db: int = 0,
    password: Optional[str] = None
) -> RedisClient:
    """Initialize the global Redis client singleton.

    Args:
        host: Redis server hostname
        port: Redis server port
        db: Redis database number
        password: Optional Redis password

    Returns:
        Initialized RedisClient instance
    """
    global _redis_client
    # Lock assumed to be held by caller
    _redis_client = RedisClient(
        host=host,
        port=port,
        db=db,
        password=password
    )
    logger.info(f"Initialized Redis client: {host}:{port}")
    return _redis_client


def get_redis_client() -> RedisClient:
    """Get the global Redis client singleton.

    Returns:
        RedisClient instance

    Raises:
        RuntimeError: If client not initialized
    """
    global _redis_client

    with _client_lock:
        if _redis_client is None:
            return init_redis_client()
        return _redis_client


def close_redis_client() -> None:
    """Close the global Redis client."""
    global _redis_client

    with _client_lock:
        if _redis_client is not None:
            _redis_client.disconnect()
            _redis_client = None
            logger.info("Global Redis client closed")
