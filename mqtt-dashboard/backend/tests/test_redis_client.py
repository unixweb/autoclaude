"""Tests for Redis client pub/sub abstraction."""

import pytest
from unittest.mock import Mock, patch
from app.redis_client import RedisClient, get_redis_client, init_redis_client


class TestRedisClient:
    """Test RedisClient class."""

    def test_singleton_pattern(self):
        """Test that get_redis_client returns singleton."""
        client1 = get_redis_client()
        client2 = get_redis_client()
        assert client1 is client2

    @patch('app.redis_client.redis.Redis')
    def test_publish_message(self, mock_redis_class):
        """Test publishing message to channel."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis

        client = RedisClient(host='localhost', port=6379)
        client.publish('test-channel', {'data': 'value'})

        mock_redis.publish.assert_called_once()

    @patch('app.redis_client.redis.Redis')
    def test_subscribe_callback(self, mock_redis_class):
        """Test subscribing to channel with callback."""
        mock_redis = Mock()
        mock_redis_class.return_value = mock_redis

        callback = Mock()
        client = RedisClient(host='localhost', port=6379)
        client.subscribe('test-channel', callback)

        assert 'test-channel' in client._subscriptions
