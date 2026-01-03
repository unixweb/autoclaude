"""Tests for Redis channel schema."""

from app.redis_channels import RedisChannels


class TestRedisChannels:
    """Test channel naming schema."""

    def test_channel_names_are_strings(self):
        """All channel names should be strings."""
        assert isinstance(RedisChannels.BROKER_STATS, str)
        assert isinstance(RedisChannels.MQTT_MESSAGES, str)
        assert isinstance(RedisChannels.BROKER_STATUS, str)

    def test_channel_names_are_unique(self):
        """All channel names should be unique."""
        channels = [
            RedisChannels.BROKER_STATS,
            RedisChannels.MQTT_MESSAGES,
            RedisChannels.BROKER_STATUS,
            RedisChannels.CLIENT_LIST,
            RedisChannels.TOPIC_LIST,
        ]
        assert len(channels) == len(set(channels))
