"""
Redis Channel Schema

Defines standardized channel names for pub/sub communication between
MQTT client service and dashboard application.
"""


class RedisChannels:
    """Redis pub/sub channel names."""

    # Broker statistics from $SYS topics (published every 5s)
    BROKER_STATS = "mqtt:broker:stats"

    # MQTT messages from subscribed topics (real-time)
    MQTT_MESSAGES = "mqtt:messages"

    # Broker connection status changes (connected/disconnected)
    BROKER_STATUS = "mqtt:broker:status"

    # Connected clients list (published every 10s)
    CLIENT_LIST = "mqtt:clients"

    # Active topics list (published every 10s)
    TOPIC_LIST = "mqtt:topics"

    # Command channel: dashboard -> MQTT service (publish, subscribe)
    COMMANDS = "mqtt:commands"


class MessageTypes:
    """Message type identifiers for structured messages."""

    # Broker stats update
    STATS_UPDATE = "stats_update"

    # Status change (connected/disconnected)
    STATUS_CHANGE = "status_change"

    # MQTT message received
    MESSAGE_RECEIVED = "message_received"

    # Client list update
    CLIENTS_UPDATE = "clients_update"

    # Topic list update
    TOPICS_UPDATE = "topics_update"

    # Command: publish message
    CMD_PUBLISH = "cmd_publish"

    # Command: subscribe to topic
    CMD_SUBSCRIBE = "cmd_subscribe"

    # Command: unsubscribe from topic
    CMD_UNSUBSCRIBE = "cmd_unsubscribe"
