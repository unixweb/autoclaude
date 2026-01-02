"""
Subscription Manager Service

This module provides a service that manages per-client MQTT topic subscriptions
and forwards received messages to WebSocket clients in real-time.
"""

import logging
import threading
from collections import defaultdict
from datetime import datetime, timezone
from typing import Callable, Optional, Set

from app.mqtt_client import MQTTClient, get_mqtt_client

logger = logging.getLogger(__name__)


class SubscriptionManager:
    """
    Service for managing per-client MQTT topic subscriptions.

    This service allows WebSocket clients to subscribe to specific MQTT topics
    and receive messages in real-time. It supports multiple clients subscribing
    to the same topic and handles MQTT wildcard patterns (# and +).
    """

    def __init__(self, mqtt_client: Optional[MQTTClient] = None):
        """
        Initialize the SubscriptionManager service.

        Args:
            mqtt_client: MQTT client instance. If None, uses the global client.
        """
        self._mqtt_client = mqtt_client
        self._lock = threading.Lock()

        # Track which clients are subscribed to which topics
        # {client_id: set(topic_patterns)}
        self._client_subscriptions: dict[str, Set[str]] = defaultdict(set)

        # Track which topics have which clients
        # {topic_pattern: set(client_ids)}
        self._topic_clients: dict[str, Set[str]] = defaultdict(set)

        # Track MQTT subscriptions we've made
        # {topic_pattern: callback_function}
        self._mqtt_subscriptions: dict[str, Callable] = {}

        # Callback for sending messages to clients
        self._message_callback: Optional[Callable] = None

    @property
    def mqtt_client(self) -> MQTTClient:
        """Get the MQTT client, using global if not set."""
        if self._mqtt_client is None:
            self._mqtt_client = get_mqtt_client()
        return self._mqtt_client

    def set_message_callback(self, callback: Callable[[str, str, str], None]) -> None:
        """
        Set the callback for forwarding messages to WebSocket clients.

        Args:
            callback: Function to call with (client_id, topic, payload).
        """
        with self._lock:
            self._message_callback = callback

    def subscribe_client(self, client_id: str, topic: str) -> bool:
        """
        Subscribe a WebSocket client to an MQTT topic.

        Args:
            client_id: WebSocket client ID (session ID).
            topic: MQTT topic pattern to subscribe to (may include wildcards).

        Returns:
            True if subscription was successful, False otherwise.
        """
        if not self.mqtt_client.is_connected:
            logger.warning(
                f"Cannot subscribe client {client_id} to {topic}: "
                "MQTT client not connected"
            )
            return False

        with self._lock:
            # Check if this is the first client subscribing to this topic
            is_new_topic = topic not in self._topic_clients or not self._topic_clients[topic]

            # Add client to topic subscribers
            self._topic_clients[topic].add(client_id)
            self._client_subscriptions[client_id].add(topic)

        # If this is the first subscription to this topic, subscribe to MQTT
        if is_new_topic:
            if not self._subscribe_to_mqtt_topic(topic):
                # Rollback if MQTT subscription failed
                with self._lock:
                    self._topic_clients[topic].discard(client_id)
                    self._client_subscriptions[client_id].discard(topic)
                    if not self._topic_clients[topic]:
                        del self._topic_clients[topic]
                    if not self._client_subscriptions[client_id]:
                        del self._client_subscriptions[client_id]
                return False

        logger.info(f"Client {client_id} subscribed to topic: {topic}")
        return True

    def unsubscribe_client(self, client_id: str, topic: str) -> bool:
        """
        Unsubscribe a WebSocket client from an MQTT topic.

        Args:
            client_id: WebSocket client ID (session ID).
            topic: MQTT topic pattern to unsubscribe from.

        Returns:
            True if unsubscription was successful, False otherwise.
        """
        with self._lock:
            # Remove client from topic subscribers
            if topic in self._topic_clients:
                self._topic_clients[topic].discard(client_id)

                # If no more clients for this topic, unsubscribe from MQTT
                if not self._topic_clients[topic]:
                    del self._topic_clients[topic]
                    should_unsubscribe_mqtt = True
                else:
                    should_unsubscribe_mqtt = False
            else:
                should_unsubscribe_mqtt = False

            # Remove topic from client's subscriptions
            if client_id in self._client_subscriptions:
                self._client_subscriptions[client_id].discard(topic)
                if not self._client_subscriptions[client_id]:
                    del self._client_subscriptions[client_id]

        # Unsubscribe from MQTT if no more clients need this topic
        if should_unsubscribe_mqtt:
            self._unsubscribe_from_mqtt_topic(topic)

        logger.info(f"Client {client_id} unsubscribed from topic: {topic}")
        return True

    def unsubscribe_client_all(self, client_id: str) -> None:
        """
        Unsubscribe a WebSocket client from all topics.

        This should be called when a client disconnects.

        Args:
            client_id: WebSocket client ID (session ID).
        """
        with self._lock:
            # Get all topics this client was subscribed to
            topics = list(self._client_subscriptions.get(client_id, set()))

        # Unsubscribe from each topic
        for topic in topics:
            self.unsubscribe_client(client_id, topic)

        logger.info(f"Client {client_id} unsubscribed from all topics")

    def get_client_subscriptions(self, client_id: str) -> list[str]:
        """
        Get all topics a client is subscribed to.

        Args:
            client_id: WebSocket client ID (session ID).

        Returns:
            List of topic patterns the client is subscribed to.
        """
        with self._lock:
            return list(self._client_subscriptions.get(client_id, set()))

    def get_topic_subscribers(self, topic: str) -> list[str]:
        """
        Get all clients subscribed to a specific topic.

        Args:
            topic: MQTT topic pattern.

        Returns:
            List of client IDs subscribed to this topic.
        """
        with self._lock:
            return list(self._topic_clients.get(topic, set()))

    def get_all_subscriptions(self) -> dict[str, list[str]]:
        """
        Get all active subscriptions.

        Returns:
            Dictionary mapping client IDs to lists of topic patterns.
        """
        with self._lock:
            return {
                client_id: list(topics)
                for client_id, topics in self._client_subscriptions.items()
            }

    def _subscribe_to_mqtt_topic(self, topic: str) -> bool:
        """
        Subscribe to an MQTT topic.

        Args:
            topic: MQTT topic pattern to subscribe to.

        Returns:
            True if subscription was successful, False otherwise.
        """
        # Create a callback for this topic
        def on_message(msg_topic: str, payload: str) -> None:
            self._on_mqtt_message(topic, msg_topic, payload)

        try:
            success = self.mqtt_client.subscribe(
                topic=topic,
                callback=on_message,
                qos=0,
            )

            if success:
                with self._lock:
                    self._mqtt_subscriptions[topic] = on_message
                logger.info(f"Subscribed to MQTT topic: {topic}")
            else:
                logger.error(f"Failed to subscribe to MQTT topic: {topic}")

            return success

        except Exception as e:
            logger.error(f"Error subscribing to MQTT topic {topic}: {e}")
            return False

    def _unsubscribe_from_mqtt_topic(self, topic: str) -> bool:
        """
        Unsubscribe from an MQTT topic.

        Args:
            topic: MQTT topic pattern to unsubscribe from.

        Returns:
            True if unsubscription was successful, False otherwise.
        """
        try:
            success = self.mqtt_client.unsubscribe(topic)

            if success:
                with self._lock:
                    self._mqtt_subscriptions.pop(topic, None)
                logger.info(f"Unsubscribed from MQTT topic: {topic}")
            else:
                logger.error(f"Failed to unsubscribe from MQTT topic: {topic}")

            return success

        except Exception as e:
            logger.error(f"Error unsubscribing from MQTT topic {topic}: {e}")
            return False

    def _on_mqtt_message(self, subscription_topic: str, msg_topic: str, payload: str) -> None:
        """
        Handle incoming MQTT message and forward to subscribed clients.

        Args:
            subscription_topic: The topic pattern that matched.
            msg_topic: The actual message topic.
            payload: The message payload.
        """
        # Get all clients subscribed to this topic pattern
        with self._lock:
            clients = list(self._topic_clients.get(subscription_topic, set()))
            callback = self._message_callback

        if not callback:
            logger.warning("No message callback set for forwarding messages")
            return

        # Forward message to each subscribed client
        timestamp = datetime.now(timezone.utc).isoformat()

        for client_id in clients:
            try:
                callback(
                    client_id,
                    msg_topic,
                    payload,
                    timestamp,
                    subscription_topic,
                )
            except Exception as e:
                logger.error(
                    f"Error forwarding message to client {client_id}: {e}"
                )


# Global SubscriptionManager instance
_subscription_manager: Optional[SubscriptionManager] = None


def get_subscription_manager() -> SubscriptionManager:
    """
    Get the global SubscriptionManager instance.

    Returns:
        The global SubscriptionManager instance.
    """
    global _subscription_manager
    if _subscription_manager is None:
        _subscription_manager = SubscriptionManager()
    return _subscription_manager


def init_subscription_manager(
    mqtt_client: Optional[MQTTClient] = None,
) -> SubscriptionManager:
    """
    Initialize the global SubscriptionManager service.

    Args:
        mqtt_client: Optional MQTT client instance. Uses global if not provided.

    Returns:
        The initialized SubscriptionManager instance.
    """
    global _subscription_manager
    _subscription_manager = SubscriptionManager(mqtt_client=mqtt_client)
    logger.info("SubscriptionManager service initialized")
    return _subscription_manager
