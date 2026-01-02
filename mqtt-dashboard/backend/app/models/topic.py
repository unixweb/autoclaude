"""
Topic Model

This module defines the data model for MQTT topic information
tracked by monitoring message traffic.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


@dataclass
class TopicInfo:
    """
    Data model for MQTT topic information.

    Topics are tracked by monitoring message traffic and include metadata
    about the last message and activity statistics.
    """

    # Topic name
    topic: str

    # Message statistics
    message_count: int = 0
    last_payload: Optional[str] = None
    last_qos: Optional[int] = None
    last_retained: Optional[bool] = None

    # Timestamps
    first_seen: datetime = field(default_factory=_utc_now)
    last_seen: datetime = field(default_factory=_utc_now)

    def to_dict(self) -> dict:
        """
        Convert the topic info to a dictionary.

        Returns:
            Dictionary representation of the topic information.
        """
        return {
            "topic": self.topic,
            "message_count": self.message_count,
            "last_payload": self.last_payload,
            "last_qos": self.last_qos,
            "last_retained": self.last_retained,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }

    def to_summary_dict(self) -> dict:
        """
        Convert to a summary dictionary with key information only.

        Returns:
            Dictionary with essential topic information.
        """
        return {
            "topic": self.topic,
            "message_count": self.message_count,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }

    def update_message(
        self,
        payload: Optional[str] = None,
        qos: Optional[int] = None,
        retained: Optional[bool] = None,
    ) -> None:
        """
        Update topic information with a new message.

        Args:
            payload: Message payload (optional).
            qos: Quality of Service level (optional).
            retained: Whether the message is retained (optional).
        """
        self.message_count += 1
        self.last_seen = _utc_now()

        if payload is not None:
            self.last_payload = payload
        if qos is not None:
            self.last_qos = qos
        if retained is not None:
            self.last_retained = retained
