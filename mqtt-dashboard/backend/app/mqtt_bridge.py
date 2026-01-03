"""
MQTT-Redis Bridge

Bridges MQTT broker and Redis pub/sub for dashboard communication.
Runs as standalone service, maintains single MQTT connection.
"""

import logging
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
        # Update stats cache
        self._update_stats_from_sys(topic, payload)

        # Publish stats periodically
        now = time.time()
        if now - self._last_stats_publish >= self.stats_publish_interval:
            self._publish_stats()
            self._last_stats_publish = now

    def _update_stats_from_sys(self, topic: str, payload: str) -> None:
        """Update stats cache from $SYS topic."""
        # Map topic to stats attribute
        topic_map = {
            "$SYS/broker/version": ("version", str),
            "$SYS/broker/uptime": ("uptime", int),
            "$SYS/broker/clients/connected": ("clients_connected", int),
            "$SYS/broker/clients/total": ("clients_total", int),
            "$SYS/broker/messages/received": ("messages_received", int),
            "$SYS/broker/messages/sent": ("messages_sent", int),
            "$SYS/broker/bytes/received": ("bytes_received", int),
            "$SYS/broker/bytes/sent": ("bytes_sent", int),
        }

        if topic in topic_map:
            attr_name, attr_type = topic_map[topic]
            try:
                value = attr_type(payload)
                setattr(self._stats, attr_name, value)
            except (ValueError, TypeError):
                pass

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
            payload = command.get("payload", "")
            qos = command.get("qos", 0)
            retain = command.get("retain", False)

            self.mqtt_client.publish(topic, payload, qos=qos, retain=retain)
            logger.info(f"Published to {topic}")

        elif cmd_type == MessageTypes.CMD_SUBSCRIBE:
            topic = command.get("topic", "")
            qos = command.get("qos", 0)

            # Subscribe and forward messages to Redis
            self.mqtt_client.subscribe(
                topic,
                lambda t, p: self._forward_mqtt_message(t, p),
                qos=qos,
            )
            logger.info(f"Subscribed to {topic}")

        elif cmd_type == MessageTypes.CMD_UNSUBSCRIBE:
            topic = command.get("topic", "")
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
        self._publish_status(connected=False)
        self.mqtt_client.disconnect()
        self.redis_client.disconnect()
        logger.info("Bridge stopped")
