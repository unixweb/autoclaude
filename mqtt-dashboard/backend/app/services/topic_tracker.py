"""
Topic Tracker Service

This module provides a service that tracks active MQTT topics by monitoring
message traffic on a wildcard subscription.
"""

import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from app.models.topic import TopicInfo
from app.mqtt_client import MQTTClient, get_mqtt_client

logger = logging.getLogger(__name__)


class TopicTracker:
    """
    Service for tracking active MQTT topics.

    This service subscribes to a wildcard pattern to capture all topic activity
    and maintains a cache of recently active topics with their metadata.
    """

    # Default configuration
    DEFAULT_INACTIVE_TIMEOUT = 3600  # 1 hour in seconds
    DEFAULT_MAX_PAYLOAD_SIZE = 1024  # Maximum payload size to store

    def __init__(
        self,
        mqtt_client: Optional[MQTTClient] = None,
        inactive_timeout: int = DEFAULT_INACTIVE_TIMEOUT,
        max_payload_size: int = DEFAULT_MAX_PAYLOAD_SIZE,
        track_sys_topics: bool = False,
    ):
        """
        Initialize the TopicTracker service.

        Args:
            mqtt_client: MQTT client instance. If None, uses the global client.
            inactive_timeout: Seconds after which inactive topics are pruned.
            max_payload_size: Maximum payload size to store (in bytes).
            track_sys_topics: Whether to track $SYS topics (default: False).
        """
        self._mqtt_client = mqtt_client
        self._topics: dict[str, TopicInfo] = {}
        self._lock = threading.Lock()
        self._subscribed = False
        self._update_callbacks: list[Callable[[TopicInfo], None]] = []
        self._inactive_timeout = inactive_timeout
        self._max_payload_size = max_payload_size
        self._track_sys_topics = track_sys_topics

    @property
    def mqtt_client(self) -> MQTTClient:
        """Get the MQTT client, using global if not set."""
        if self._mqtt_client is None:
            self._mqtt_client = get_mqtt_client()
        return self._mqtt_client

    @property
    def is_subscribed(self) -> bool:
        """Check if the service is subscribed to topics."""
        with self._lock:
            return self._subscribed

    def get_topics(self, include_inactive: bool = False) -> list[TopicInfo]:
        """
        Get list of tracked topics.

        Args:
            include_inactive: Whether to include inactive topics (default: False).

        Returns:
            List of TopicInfo objects, sorted by last_seen (most recent first).
        """
        with self._lock:
            if not include_inactive:
                # Filter out inactive topics
                self._prune_inactive_topics()

            # Return a copy of topics sorted by last_seen
            topics = list(self._topics.values())

        # Sort by last_seen descending (most recent first)
        topics.sort(key=lambda t: t.last_seen, reverse=True)
        return topics

    def get_topic(self, topic_name: str) -> Optional[TopicInfo]:
        """
        Get information for a specific topic.

        Args:
            topic_name: The topic name to lookup.

        Returns:
            TopicInfo for the topic, or None if not found.
        """
        with self._lock:
            topic_info = self._topics.get(topic_name)
            return topic_info

    def get_topic_count(self) -> int:
        """
        Get the count of currently tracked topics.

        Returns:
            Number of active topics being tracked.
        """
        with self._lock:
            self._prune_inactive_topics()
            return len(self._topics)

    def subscribe(self) -> bool:
        """
        Subscribe to wildcard topic to capture all message activity.

        Returns:
            True if subscription was successful, False otherwise.
        """
        if self._subscribed:
            logger.debug("Already subscribed to topic tracking")
            return True

        if not self.mqtt_client.is_connected:
            logger.warning("Cannot subscribe for topic tracking: MQTT client not connected")
            return False

        try:
            # Subscribe to all topics (excluding $SYS by default)
            # Use '#' wildcard to match all topics at all levels
            success = self.mqtt_client.subscribe(
                topic="#",
                callback=self._on_topic_message,
                qos=0,
            )

            if success:
                with self._lock:
                    self._subscribed = True
                logger.info("Subscribed to # for topic tracking")
            else:
                logger.error("Failed to subscribe for topic tracking")

            return success

        except Exception as e:
            logger.error(f"Error subscribing for topic tracking: {e}")
            return False

    def unsubscribe(self) -> bool:
        """
        Unsubscribe from topic tracking.

        Returns:
            True if unsubscription was successful, False otherwise.
        """
        if not self._subscribed:
            return True

        try:
            success = self.mqtt_client.unsubscribe("#")

            if success:
                with self._lock:
                    self._subscribed = False
                logger.info("Unsubscribed from topic tracking")

            return success

        except Exception as e:
            logger.error(f"Error unsubscribing from topic tracking: {e}")
            return False

    def clear_topics(self) -> None:
        """Clear all tracked topics."""
        with self._lock:
            self._topics.clear()
        logger.info("Cleared all tracked topics")

    def add_update_callback(
        self, callback: Callable[[TopicInfo], None]
    ) -> None:
        """
        Register a callback to be called when a topic is updated.

        Args:
            callback: Function to call with updated TopicInfo.
        """
        with self._lock:
            self._update_callbacks.append(callback)

    def remove_update_callback(
        self, callback: Callable[[TopicInfo], None]
    ) -> None:
        """
        Remove a previously registered update callback.

        Args:
            callback: The callback function to remove.
        """
        with self._lock:
            if callback in self._update_callbacks:
                self._update_callbacks.remove(callback)

    def _on_topic_message(self, topic: str, payload: str) -> None:
        """
        Handle incoming messages from subscribed topics.

        Args:
            topic: The MQTT topic.
            payload: The message payload.
        """
        # Filter out $SYS topics unless explicitly tracking them
        if not self._track_sys_topics and topic.startswith("$SYS/"):
            return

        # Truncate payload if too large
        truncated_payload = payload
        if len(payload) > self._max_payload_size:
            truncated_payload = payload[:self._max_payload_size] + "..."

        with self._lock:
            # Get or create topic info
            if topic in self._topics:
                topic_info = self._topics[topic]
                topic_info.update_message(payload=truncated_payload)
            else:
                topic_info = TopicInfo(
                    topic=topic,
                    message_count=1,
                    last_payload=truncated_payload,
                )
                self._topics[topic] = topic_info

            # Get callbacks to notify
            callbacks = list(self._update_callbacks)

        # Notify callbacks outside the lock
        for callback in callbacks:
            try:
                callback(topic_info)
            except Exception as e:
                logger.error(f"Error in topic update callback: {e}")

    def _prune_inactive_topics(self) -> None:
        """
        Remove topics that haven't been seen recently.

        This method should be called while holding self._lock.
        """
        if self._inactive_timeout <= 0:
            return

        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(seconds=self._inactive_timeout)

        # Find topics to remove
        topics_to_remove = [
            topic_name
            for topic_name, topic_info in self._topics.items()
            if topic_info.last_seen < cutoff_time
        ]

        # Remove inactive topics
        for topic_name in topics_to_remove:
            del self._topics[topic_name]

        if topics_to_remove:
            logger.debug(f"Pruned {len(topics_to_remove)} inactive topics")


# Global TopicTracker instance
_topic_tracker: Optional[TopicTracker] = None


def get_topic_tracker() -> TopicTracker:
    """
    Get the global TopicTracker instance.

    Returns:
        The global TopicTracker instance.
    """
    global _topic_tracker
    if _topic_tracker is None:
        _topic_tracker = TopicTracker()
    return _topic_tracker


def init_topic_tracker(
    mqtt_client: Optional[MQTTClient] = None,
    inactive_timeout: int = TopicTracker.DEFAULT_INACTIVE_TIMEOUT,
    max_payload_size: int = TopicTracker.DEFAULT_MAX_PAYLOAD_SIZE,
    track_sys_topics: bool = False,
) -> TopicTracker:
    """
    Initialize and start the global TopicTracker service.

    This function creates the TopicTracker instance and subscribes to topics.

    Args:
        mqtt_client: Optional MQTT client instance. Uses global if not provided.
        inactive_timeout: Seconds after which inactive topics are pruned.
        max_payload_size: Maximum payload size to store (in bytes).
        track_sys_topics: Whether to track $SYS topics (default: False).

    Returns:
        The initialized TopicTracker instance.
    """
    global _topic_tracker
    _topic_tracker = TopicTracker(
        mqtt_client=mqtt_client,
        inactive_timeout=inactive_timeout,
        max_payload_size=max_payload_size,
        track_sys_topics=track_sys_topics,
    )

    # Subscribe to topics
    if _topic_tracker.mqtt_client.is_connected:
        _topic_tracker.subscribe()
    else:
        logger.warning(
            "MQTT client not connected during TopicTracker initialization. "
            "Topic tracking will be attempted on reconnection."
        )

    return _topic_tracker
