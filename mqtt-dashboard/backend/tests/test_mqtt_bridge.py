"""Tests for MQTT-Redis bridge."""

import pytest
from unittest.mock import Mock, patch
from app.mqtt_bridge import MQTTBridge


class TestMQTTBridge:
    """Test MQTTBridge class."""

    @patch('app.mqtt_bridge.RedisClient')
    @patch('app.mqtt_bridge.MQTTClient')
    def test_bridge_publishes_stats_to_redis(self, mock_mqtt, mock_redis):
        """Test that broker stats are published to Redis."""
        redis_client = Mock()
        mqtt_client = Mock()
        mock_redis.return_value = redis_client
        mock_mqtt.return_value = mqtt_client

        bridge = MQTTBridge(
            mqtt_host='localhost',
            mqtt_port=1883,
            redis_host='localhost',
            redis_port=6379,
        )

        # Simulate $SYS message
        bridge._handle_sys_message('$SYS/broker/version', 'mosquitto 2.0.18')

        # Should publish to Redis
        assert redis_client.publish.called

    @patch('app.mqtt_bridge.RedisClient')
    @patch('app.mqtt_bridge.MQTTClient')
    def test_bridge_handles_commands_from_redis(self, mock_mqtt, mock_redis):
        """Test that commands from Redis are sent to MQTT."""
        redis_client = Mock()
        mqtt_client = Mock()
        mock_redis.return_value = redis_client
        mock_mqtt.return_value = mqtt_client

        bridge = MQTTBridge(
            mqtt_host='localhost',
            mqtt_port=1883,
            redis_host='localhost',
            redis_port=6379,
        )

        # Simulate publish command from Redis
        command = {
            'type': 'cmd_publish',
            'topic': 'test/topic',
            'payload': 'test message',
            'qos': 0,
        }
        bridge._handle_command(command)

        # Should publish to MQTT
        mqtt_client.publish.assert_called_once_with(
            'test/topic',
            'test message',
            qos=0,
            retain=False,
        )
