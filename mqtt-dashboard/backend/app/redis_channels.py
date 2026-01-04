"""
Redis Channel Schema

Defines standardized channel names for pub/sub communication between
MQTT client service and dashboard application.
"""


class RedisChannels:
    """Redis pub/sub channel names."""

    # Broker statistics from $SYS topics (published every 5s)
    BROKER_STATS = "mqtt:broker:stats"

    # Broker connection status changes (connected/disconnected)
    BROKER_STATUS = "mqtt:broker:status"

    # Connected clients list (published every 10s)
    CLIENT_LIST = "mqtt:clients"

    # Active topics list (published every 10s)
    TOPIC_LIST = "mqtt:topics"

    # NOTE: User topic messages now come directly via MQTT, not Redis
    # The mqtt-bridge only handles $SYS topics for stats


class MessageTypes:
    """Message type identifiers for structured messages."""

    # Broker stats update
    STATS_UPDATE = "stats_update"

    # Status change (connected/disconnected)
    STATUS_CHANGE = "status_change"

    # Client list update
    CLIENTS_UPDATE = "clients_update"

    # Topic list update
    TOPICS_UPDATE = "topics_update"
