"""
MQTT Client Module

This module provides a wrapper around the paho-mqtt client for connecting
to the Mosquitto broker and managing subscriptions.
"""

import threading
import time
from typing import Callable, Optional

import paho.mqtt.client as mqtt

from app.config import Config


class MQTTClient:
    """
    MQTT Client wrapper for Mosquitto broker communication.

    This class provides a thread-safe interface for connecting to the MQTT broker,
    publishing messages, and managing subscriptions.
    """

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the MQTT client.

        Args:
            config: Configuration object. If None, uses default Config.
        """
        self.config = config or Config()
        self._client: Optional[mqtt.Client] = None
        self._connected = False
        self._lock = threading.Lock()
        self._message_callbacks: dict[str, list[Callable]] = {}
        self._reconnect_thread: Optional[threading.Thread] = None
        self._stop_reconnect = threading.Event()

    @property
    def is_connected(self) -> bool:
        """Check if the client is currently connected to the broker."""
        with self._lock:
            return self._connected

    def connect(self) -> bool:
        """
        Connect to the MQTT broker.

        Returns:
            True if connection was successful, False otherwise.
        """
        try:
            # Create client with protocol version 5
            self._client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=self.config.MQTT_CLIENT_ID,
                protocol=mqtt.MQTTv5,
            )

            # Set up callbacks
            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect
            self._client.on_message = self._on_message

            # Configure authentication if provided
            if self.config.MQTT_USERNAME and self.config.MQTT_PASSWORD:
                self._client.username_pw_set(
                    self.config.MQTT_USERNAME,
                    self.config.MQTT_PASSWORD,
                )

            # Configure TLS if enabled
            if self.config.MQTT_USE_TLS:
                self._client.tls_set()

            # Connect to broker
            self._client.connect(
                host=self.config.MQTT_BROKER_HOST,
                port=self.config.MQTT_BROKER_PORT,
                keepalive=self.config.MQTT_KEEPALIVE,
            )

            # Start the network loop in a background thread
            self._client.loop_start()

            # Wait for connection to be established
            timeout = 10
            start_time = time.time()
            while not self._connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)

            return self._connected

        except Exception:
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        self._stop_reconnect.set()
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            self._reconnect_thread.join(timeout=2)

        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None

        with self._lock:
            self._connected = False

    def publish(
        self,
        topic: str,
        payload: str,
        qos: int = 0,
        retain: bool = False,
    ) -> bool:
        """
        Publish a message to a topic.

        Args:
            topic: The MQTT topic to publish to.
            payload: The message payload.
            qos: Quality of Service level (0, 1, or 2).
            retain: Whether to retain the message on the broker.

        Returns:
            True if publish was successful, False otherwise.
        """
        if not self.is_connected or not self._client:
            return False

        try:
            result = self._client.publish(topic, payload, qos=qos, retain=retain)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception:
            return False

    def subscribe(
        self,
        topic: str,
        callback: Callable[[str, str], None],
        qos: int = 0,
    ) -> bool:
        """
        Subscribe to a topic with a callback.

        Args:
            topic: The MQTT topic pattern to subscribe to.
            callback: Function to call when a message is received.
                     Signature: callback(topic: str, payload: str)
            qos: Quality of Service level (0, 1, or 2).

        Returns:
            True if subscription was successful, False otherwise.
        """
        if not self.is_connected or not self._client:
            return False

        try:
            # Register the callback
            with self._lock:
                if topic not in self._message_callbacks:
                    self._message_callbacks[topic] = []
                self._message_callbacks[topic].append(callback)

            # Subscribe to the topic
            result = self._client.subscribe(topic, qos=qos)
            return result[0] == mqtt.MQTT_ERR_SUCCESS
        except Exception:
            return False

    def unsubscribe(self, topic: str) -> bool:
        """
        Unsubscribe from a topic.

        Args:
            topic: The MQTT topic to unsubscribe from.

        Returns:
            True if unsubscription was successful, False otherwise.
        """
        if not self.is_connected or not self._client:
            return False

        try:
            # Remove callbacks for this topic
            with self._lock:
                self._message_callbacks.pop(topic, None)

            result = self._client.unsubscribe(topic)
            return result[0] == mqtt.MQTT_ERR_SUCCESS
        except Exception:
            return False

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata,
        flags,
        reason_code,
        properties,
    ) -> None:
        """Handle connection established event."""
        with self._lock:
            self._connected = reason_code == 0 or reason_code.is_failure is False

        if self._connected:
            # Resubscribe to all topics after reconnection
            with self._lock:
                topics = list(self._message_callbacks.keys())
            for topic in topics:
                self._client.subscribe(topic)

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata,
        disconnect_flags,
        reason_code,
        properties,
    ) -> None:
        """Handle disconnection event."""
        with self._lock:
            self._connected = False

        # Start reconnection thread if not already running
        if not self._stop_reconnect.is_set():
            self._start_reconnect()

    def _on_message(
        self,
        client: mqtt.Client,
        userdata,
        message: mqtt.MQTTMessage,
    ) -> None:
        """Handle incoming message event."""
        topic = message.topic
        try:
            payload = message.payload.decode("utf-8")
        except UnicodeDecodeError:
            payload = message.payload.hex()

        # Find and call matching callbacks
        with self._lock:
            callbacks_to_call = []
            for pattern, callbacks in self._message_callbacks.items():
                if self._topic_matches(pattern, topic):
                    callbacks_to_call.extend(callbacks)

        for callback in callbacks_to_call:
            try:
                callback(topic, payload)
            except Exception:
                pass

    def _topic_matches(self, pattern: str, topic: str) -> bool:
        """
        Check if a topic matches a subscription pattern.

        Args:
            pattern: Subscription pattern (may include + and # wildcards).
            topic: Actual topic to match.

        Returns:
            True if the topic matches the pattern.
        """
        pattern_parts = pattern.split("/")
        topic_parts = topic.split("/")

        i = 0
        for i, part in enumerate(pattern_parts):
            if part == "#":
                return True
            if i >= len(topic_parts):
                return False
            if part != "+" and part != topic_parts[i]:
                return False

        return i + 1 == len(topic_parts)

    def _start_reconnect(self) -> None:
        """Start the reconnection thread."""
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            return

        self._reconnect_thread = threading.Thread(
            target=self._reconnect_loop,
            daemon=True,
        )
        self._reconnect_thread.start()

    def _reconnect_loop(self) -> None:
        """Attempt to reconnect to the broker periodically."""
        while not self._stop_reconnect.is_set():
            if not self._connected and self._client:
                try:
                    self._client.reconnect()
                except Exception:
                    pass

            # Wait before next attempt
            self._stop_reconnect.wait(self.config.MQTT_RECONNECT_DELAY)


# Global MQTT client instance
_mqtt_client: Optional[MQTTClient] = None


def get_mqtt_client() -> MQTTClient:
    """
    Get the global MQTT client instance.

    Returns:
        The global MQTTClient instance.
    """
    global _mqtt_client
    if _mqtt_client is None:
        _mqtt_client = MQTTClient()
    return _mqtt_client


def init_mqtt_client(config: Config) -> MQTTClient:
    """
    Initialize and connect the global MQTT client.

    Args:
        config: Configuration object with MQTT settings.

    Returns:
        The initialized and connected MQTTClient instance.
    """
    global _mqtt_client
    _mqtt_client = MQTTClient(config)
    _mqtt_client.connect()
    return _mqtt_client
