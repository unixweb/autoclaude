"""
MQTT-Redis Bridge

Bridges MQTT broker and Redis pub/sub for dashboard communication.
Runs as standalone service, maintains single MQTT connection.
"""

import logging
import threading
import time
from typing import Optional

from app.config import Config
from app.mqtt_client import MQTTClient
from app.redis_client import RedisClient
from app.redis_channels import RedisChannels, MessageTypes
from app.models.broker_stats import BrokerStats

logger = logging.getLogger(__name__)


class MQTTBridge:
    """
    Bridge between MQTT broker and Redis pub/sub.

    Subscribes to MQTT broker ($SYS topics and user topics),
    publishes messages to Redis for dashboard consumption.
    Listens for commands from Redis, executes via MQTT.
    """

    def __init__(
        self,
        mqtt_host: str,
        mqtt_port: int,
        redis_host: str,
        redis_port: int,
        mqtt_username: Optional[str] = None,
        mqtt_password: Optional[str] = None,
        redis_password: Optional[str] = None,
    ):
        """Initialize bridge with MQTT and Redis connections."""
        # Create config for MQTT
        config = Config()
        config.MQTT_BROKER_HOST = mqtt_host
        config.MQTT_BROKER_PORT = mqtt_port
        config.MQTT_USERNAME = mqtt_username or ""
        config.MQTT_PASSWORD = mqtt_password or ""
        config.MQTT_CLIENT_ID = "mqtt-bridge-service"

        # Initialize clients
        self.mqtt_client = MQTTClient(config)
        self.redis_client = RedisClient(
            host=redis_host,
            port=redis_port,
            password=redis_password,
        )

        # Stats cache
        self._stats = BrokerStats()
        self._last_stats_publish = 0
        self.stats_publish_interval = 5  # Publish stats every 5s
        self._stats_lock = threading.Lock()

        # Track topic callbacks for cleanup
        self._topic_callbacks = {}  # topic -> callback mapping

    def start(self) -> bool:
        """Start the bridge service."""
        logger.info("Starting MQTT-Redis bridge...")

        # Connect to MQTT
        if not self.mqtt_client.connect():
            logger.error("Failed to connect to MQTT broker")
            return False

        logger.info("Connected to MQTT broker")

        # Subscribe to $SYS topics
        self.mqtt_client.subscribe("$SYS/#", self._handle_sys_message, qos=0)
        logger.info("Subscribed to $SYS/# topics")

        # Subscribe to commands channel on Redis
        self.redis_client.subscribe(RedisChannels.COMMANDS, self._handle_command)
        logger.info("Subscribed to Redis command channel")

        # Publish initial status
        self._publish_status(connected=True)

        logger.info("MQTT-Redis bridge started successfully")
        return True

    def _handle_sys_message(self, topic: str, payload: str) -> None:
        """Handle message from $SYS topics."""
        with self._stats_lock:
            # Update stats cache
            self._update_stats_from_sys(topic, payload)

            # Publish stats periodically
            now = time.time()
            if now - self._last_stats_publish >= self.stats_publish_interval:
                self._publish_stats()
                self._last_stats_publish = now

    def _update_stats_from_sys(self, topic: str, payload: str) -> None:
        """Update stats cache from $SYS topic."""
        # Helper function to parse numeric values that may have units
        def parse_int(value: str) -> int:
            """Parse integer, stripping common suffixes like 'seconds'."""
            return int(value.split()[0])

        def parse_float(value: str) -> float:
            """Parse float, stripping common suffixes."""
            return float(value.split()[0])

        # Comprehensive topic map for all broker statistics
        topic_map = {
            # Broker information
            "$SYS/broker/version": ("version", str),
            "$SYS/broker/uptime": ("uptime", parse_int),

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
            "$SYS/broker/store/messages/count": ("messages_stored", int),  # Alternative
            "$SYS/broker/messages/inflight": ("messages_inflight", int),

            # Publish statistics
            "$SYS/broker/publish/messages/received": ("publish_messages_received", int),
            "$SYS/broker/publish/messages/sent": ("publish_messages_sent", int),
            "$SYS/broker/publish/messages/dropped": ("publish_messages_dropped", int),

            # Byte statistics
            "$SYS/broker/bytes/received": ("bytes_received", int),
            "$SYS/broker/bytes/sent": ("bytes_sent", int),
            "$SYS/broker/publish/bytes/received": ("bytes_received", int),  # Some brokers use this
            "$SYS/broker/publish/bytes/sent": ("bytes_sent", int),

            # Subscription statistics
            "$SYS/broker/subscriptions/count": ("subscriptions_count", int),

            # Retained messages
            "$SYS/broker/retained messages/count": ("retained_messages_count", int),

            # Load statistics - messages
            "$SYS/broker/load/messages/received/1min": ("load_messages_received_1min", parse_float),
            "$SYS/broker/load/messages/received/5min": ("load_messages_received_5min", parse_float),
            "$SYS/broker/load/messages/received/15min": ("load_messages_received_15min", parse_float),
            "$SYS/broker/load/messages/sent/1min": ("load_messages_sent_1min", parse_float),
            "$SYS/broker/load/messages/sent/5min": ("load_messages_sent_5min", parse_float),
            "$SYS/broker/load/messages/sent/15min": ("load_messages_sent_15min", parse_float),

            # Load statistics - bytes
            "$SYS/broker/load/bytes/received/1min": ("load_bytes_received_1min", parse_float),
            "$SYS/broker/load/bytes/received/5min": ("load_bytes_received_5min", parse_float),
            "$SYS/broker/load/bytes/received/15min": ("load_bytes_received_15min", parse_float),
            "$SYS/broker/load/bytes/sent/1min": ("load_bytes_sent_1min", parse_float),
            "$SYS/broker/load/bytes/sent/5min": ("load_bytes_sent_5min", parse_float),
            "$SYS/broker/load/bytes/sent/15min": ("load_bytes_sent_15min", parse_float),

            # Load statistics - connections
            "$SYS/broker/load/connections/1min": ("load_connections_1min", parse_float),
            "$SYS/broker/load/connections/5min": ("load_connections_5min", parse_float),
            "$SYS/broker/load/connections/15min": ("load_connections_15min", parse_float),

            # Load statistics - publish
            "$SYS/broker/load/publish/received/1min": ("load_publish_received_1min", parse_float),
            "$SYS/broker/load/publish/received/5min": ("load_publish_received_5min", parse_float),
            "$SYS/broker/load/publish/received/15min": ("load_publish_received_15min", parse_float),
            "$SYS/broker/load/publish/sent/1min": ("load_publish_sent_1min", parse_float),
            "$SYS/broker/load/publish/sent/5min": ("load_publish_sent_5min", parse_float),
            "$SYS/broker/load/publish/sent/15min": ("load_publish_sent_15min", parse_float),

            # Load statistics - sockets
            "$SYS/broker/load/sockets/1min": ("load_sockets_1min", parse_float),
            "$SYS/broker/load/sockets/5min": ("load_sockets_5min", parse_float),
            "$SYS/broker/load/sockets/15min": ("load_sockets_15min", parse_float),

            # Heap memory
            "$SYS/broker/heap/current": ("heap_current", int),
            "$SYS/broker/heap/maximum": ("heap_maximum", int),
        }

        if topic in topic_map:
            attr_name, converter = topic_map[topic]
            try:
                value = converter(payload)
                setattr(self._stats, attr_name, value)
            except (ValueError, TypeError, IndexError) as e:
                logger.debug(f"Failed to parse {topic} with payload '{payload}': {e}")

    def _publish_stats(self) -> None:
        """Publish broker stats to Redis."""
        message = {
            "type": MessageTypes.STATS_UPDATE,
            "data": self._stats.to_dict(),
        }
        self.redis_client.publish(RedisChannels.BROKER_STATS, message)

    def _publish_status(self, connected: bool) -> None:
        """Publish broker connection status to Redis."""
        message = {
            "type": MessageTypes.STATUS_CHANGE,
            "connected": connected,
            "timestamp": time.time(),
        }
        self.redis_client.publish(RedisChannels.BROKER_STATUS, message)

    def _handle_command(self, command: dict) -> None:
        """Handle command from Redis."""
        cmd_type = command.get("type")

        if cmd_type == MessageTypes.CMD_PUBLISH:
            topic = command.get("topic", "")
            if not topic:
                logger.error("Publish command missing topic")
                return

            payload = command.get("payload", "")
            qos = command.get("qos", 0)

            # Validate QoS
            if qos not in (0, 1, 2):
                logger.error(f"Invalid QoS value: {qos}, must be 0, 1, or 2")
                return

            retain = command.get("retain", False)

            success = self.mqtt_client.publish(topic, payload, qos=qos, retain=retain)
            if success:
                logger.info(f"Published to {topic}")
            else:
                logger.error(f"Failed to publish to {topic}")

        elif cmd_type == MessageTypes.CMD_SUBSCRIBE:
            topic = command.get("topic", "")
            qos = command.get("qos", 0)

            # Check if already subscribed
            if topic in self._topic_callbacks:
                logger.warning(f"Already subscribed to {topic}")
                return

            # Create and store callback
            def callback(t, p):
                self._forward_mqtt_message(t, p)

            self._topic_callbacks[topic] = callback
            self.mqtt_client.subscribe(topic, callback, qos=qos)
            logger.info(f"Subscribed to {topic}")

        elif cmd_type == MessageTypes.CMD_UNSUBSCRIBE:
            topic = command.get("topic", "")
            if not topic:
                logger.error("Unsubscribe command missing topic")
                return

            if topic in self._topic_callbacks:
                del self._topic_callbacks[topic]

            self.mqtt_client.unsubscribe(topic)
            logger.info(f"Unsubscribed from {topic}")

    def _forward_mqtt_message(self, topic: str, payload: str) -> None:
        """Forward MQTT message to Redis."""
        message = {
            "type": MessageTypes.MESSAGE_RECEIVED,
            "topic": topic,
            "payload": payload,
            "timestamp": time.time(),
        }
        self.redis_client.publish(RedisChannels.MQTT_MESSAGES, message)

    def run(self) -> None:
        """Run the bridge (blocking)."""
        try:
            logger.info("Bridge running... Press Ctrl+C to stop")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down bridge...")
            self.stop()

    def stop(self) -> None:
        """Stop the bridge service."""
        try:
            self._publish_status(connected=False)
        except Exception as e:
            logger.warning(f"Failed to publish final status: {e}")

        try:
            # Unsubscribe from dynamic topics
            for topic in list(self._topic_callbacks.keys()):
                try:
                    self.mqtt_client.unsubscribe(topic)
                except Exception as e:
                    logger.warning(f"Failed to unsubscribe from {topic}: {e}")
        except Exception as e:
            logger.warning(f"Error during topic cleanup: {e}")

        try:
            self.mqtt_client.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting MQTT client: {e}")

        try:
            self.redis_client.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting Redis client: {e}")

        logger.info("Bridge stopped")
