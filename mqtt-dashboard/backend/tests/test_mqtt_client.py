"""
Unit tests for MQTT Client.

This module tests the MQTTClient wrapper including connection handling,
message publishing, subscriptions, and topic pattern matching.
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch, call
import paho.mqtt.client as mqtt

from app.mqtt_client import MQTTClient
from app.config import TestingConfig


class TestMQTTClientConnection:
    """Tests for MQTT client connection handling."""

    def test_mqtt_client_initialization(self):
        """Test MQTT client initialization."""
        config = TestingConfig()
        client = MQTTClient(config)

        assert client.config == config
        assert client.is_connected is False
        assert client._client is None

    def test_mqtt_client_default_config(self):
        """Test MQTT client with default config."""
        client = MQTTClient()
        assert client.config is not None

    @patch("app.mqtt_client.mqtt.Client")
    def test_connect_success(self, mock_client_class):
        """Test successful connection to MQTT broker."""
        mock_paho_client = Mock()
        mock_paho_client.connect.return_value = None
        mock_paho_client.loop_start.return_value = None
        mock_client_class.return_value = mock_paho_client

        config = TestingConfig()
        client = MQTTClient(config)

        # Simulate successful connection callback
        def simulate_connect(*args, **kwargs):
            # Trigger the on_connect callback
            reason_code = Mock()
            reason_code.is_failure = False
            client._on_connect(mock_paho_client, None, None, 0, None)

        mock_paho_client.connect.side_effect = simulate_connect

        result = client.connect()

        assert result is True
        assert client.is_connected is True
        mock_paho_client.connect.assert_called_once()
        mock_paho_client.loop_start.assert_called_once()

    @patch("app.mqtt_client.mqtt.Client")
    def test_connect_with_authentication(self, mock_client_class):
        """Test connection with username and password."""
        mock_paho_client = Mock()
        mock_client_class.return_value = mock_paho_client

        config = TestingConfig()
        config.MQTT_USERNAME = "testuser"
        config.MQTT_PASSWORD = "testpass"

        client = MQTTClient(config)

        # Simulate successful connection
        def simulate_connect(*args, **kwargs):
            reason_code = Mock()
            reason_code.is_failure = False
            client._on_connect(mock_paho_client, None, None, 0, None)

        mock_paho_client.connect.side_effect = simulate_connect

        client.connect()

        mock_paho_client.username_pw_set.assert_called_once_with("testuser", "testpass")

    @patch("app.mqtt_client.mqtt.Client")
    def test_connect_with_tls(self, mock_client_class):
        """Test connection with TLS enabled."""
        mock_paho_client = Mock()
        mock_client_class.return_value = mock_paho_client

        config = TestingConfig()
        config.MQTT_USE_TLS = True

        client = MQTTClient(config)

        # Simulate successful connection
        def simulate_connect(*args, **kwargs):
            reason_code = Mock()
            reason_code.is_failure = False
            client._on_connect(mock_paho_client, None, None, 0, None)

        mock_paho_client.connect.side_effect = simulate_connect

        client.connect()

        mock_paho_client.tls_set.assert_called_once()

    @patch("app.mqtt_client.mqtt.Client")
    def test_connect_failure(self, mock_client_class):
        """Test connection failure."""
        mock_paho_client = Mock()
        mock_paho_client.connect.side_effect = Exception("Connection failed")
        mock_client_class.return_value = mock_paho_client

        config = TestingConfig()
        client = MQTTClient(config)

        result = client.connect()

        assert result is False
        assert client.is_connected is False

    def test_disconnect(self):
        """Test disconnection from MQTT broker."""
        mock_paho_client = Mock()
        config = TestingConfig()
        client = MQTTClient(config)
        client._client = mock_paho_client
        client._connected = True

        client.disconnect()

        assert client.is_connected is False
        mock_paho_client.loop_stop.assert_called_once()
        mock_paho_client.disconnect.assert_called_once()
        assert client._client is None


class TestMQTTClientPublish:
    """Tests for MQTT client message publishing."""

    def test_publish_success(self):
        """Test successful message publishing."""
        mock_paho_client = Mock()
        mock_result = Mock()
        mock_result.rc = mqtt.MQTT_ERR_SUCCESS
        mock_paho_client.publish.return_value = mock_result

        config = TestingConfig()
        client = MQTTClient(config)
        client._client = mock_paho_client
        client._connected = True

        result = client.publish("test/topic", "test payload", qos=1, retain=True)

        assert result is True
        mock_paho_client.publish.assert_called_once_with(
            "test/topic", "test payload", qos=1, retain=True
        )

    def test_publish_not_connected(self):
        """Test publishing when not connected."""
        config = TestingConfig()
        client = MQTTClient(config)
        client._connected = False

        result = client.publish("test/topic", "payload")

        assert result is False

    def test_publish_failure(self):
        """Test publishing failure."""
        mock_paho_client = Mock()
        mock_result = Mock()
        mock_result.rc = mqtt.MQTT_ERR_NO_CONN
        mock_paho_client.publish.return_value = mock_result

        config = TestingConfig()
        client = MQTTClient(config)
        client._client = mock_paho_client
        client._connected = True

        result = client.publish("test/topic", "payload")

        assert result is False

    def test_publish_exception(self):
        """Test publishing when exception occurs."""
        mock_paho_client = Mock()
        mock_paho_client.publish.side_effect = Exception("Publish error")

        config = TestingConfig()
        client = MQTTClient(config)
        client._client = mock_paho_client
        client._connected = True

        result = client.publish("test/topic", "payload")

        assert result is False


class TestMQTTClientSubscribe:
    """Tests for MQTT client subscription handling."""

    def test_subscribe_success(self):
        """Test successful subscription."""
        mock_paho_client = Mock()
        mock_paho_client.subscribe.return_value = (mqtt.MQTT_ERR_SUCCESS, 1)

        config = TestingConfig()
        client = MQTTClient(config)
        client._client = mock_paho_client
        client._connected = True

        callback = Mock()
        result = client.subscribe("test/topic", callback, qos=1)

        assert result is True
        mock_paho_client.subscribe.assert_called_once_with("test/topic", qos=1)
        assert "test/topic" in client._message_callbacks
        assert callback in client._message_callbacks["test/topic"]

    def test_subscribe_not_connected(self):
        """Test subscription when not connected."""
        config = TestingConfig()
        client = MQTTClient(config)
        client._connected = False

        callback = Mock()
        result = client.subscribe("test/topic", callback)

        assert result is False

    def test_subscribe_multiple_callbacks(self):
        """Test multiple callbacks for same topic."""
        mock_paho_client = Mock()
        mock_paho_client.subscribe.return_value = (mqtt.MQTT_ERR_SUCCESS, 1)

        config = TestingConfig()
        client = MQTTClient(config)
        client._client = mock_paho_client
        client._connected = True

        callback1 = Mock()
        callback2 = Mock()

        client.subscribe("test/topic", callback1)
        client.subscribe("test/topic", callback2)

        assert len(client._message_callbacks["test/topic"]) == 2

    def test_unsubscribe_success(self):
        """Test successful unsubscription."""
        mock_paho_client = Mock()
        mock_paho_client.subscribe.return_value = (mqtt.MQTT_ERR_SUCCESS, 1)
        mock_paho_client.unsubscribe.return_value = (mqtt.MQTT_ERR_SUCCESS, 1)

        config = TestingConfig()
        client = MQTTClient(config)
        client._client = mock_paho_client
        client._connected = True

        callback = Mock()
        client.subscribe("test/topic", callback)
        result = client.unsubscribe("test/topic")

        assert result is True
        mock_paho_client.unsubscribe.assert_called_once_with("test/topic")
        assert "test/topic" not in client._message_callbacks


class TestMQTTClientTopicMatching:
    """Tests for MQTT topic pattern matching."""

    def test_topic_matches_exact(self):
        """Test exact topic matching."""
        config = TestingConfig()
        client = MQTTClient(config)

        assert client._topic_matches("test/topic", "test/topic") is True
        assert client._topic_matches("test/topic", "test/other") is False

    def test_topic_matches_single_level_wildcard(self):
        """Test single-level wildcard (+) matching."""
        config = TestingConfig()
        client = MQTTClient(config)

        # + matches single level
        assert client._topic_matches("test/+/sensor", "test/room1/sensor") is True
        assert client._topic_matches("test/+/sensor", "test/room2/sensor") is True
        assert client._topic_matches("test/+", "test/room1") is True

        # + does not match multiple levels
        assert client._topic_matches("test/+/sensor", "test/room1/temp/sensor") is False

        # + matches empty level (valid in MQTT)
        assert client._topic_matches("test/+/sensor", "test//sensor") is True

    def test_topic_matches_multi_level_wildcard(self):
        """Test multi-level wildcard (#) matching."""
        config = TestingConfig()
        client = MQTTClient(config)

        # # matches everything after it
        assert client._topic_matches("test/#", "test/room1") is True
        assert client._topic_matches("test/#", "test/room1/temp") is True
        assert client._topic_matches("test/#", "test/room1/temp/sensor") is True
        assert client._topic_matches("#", "any/topic/here") is True

        # # must be at the end
        assert client._topic_matches("test/#/sensor", "test/room1/sensor") is True

    def test_topic_matches_combined_wildcards(self):
        """Test combined wildcard patterns."""
        config = TestingConfig()
        client = MQTTClient(config)

        # Combination of + and #
        assert client._topic_matches("test/+/#", "test/room1/temp") is True
        assert client._topic_matches("test/+/#", "test/room1/temp/sensor") is True
        assert client._topic_matches("+/room1/#", "test/room1/temp") is True

    def test_topic_matches_edge_cases(self):
        """Test edge cases in topic matching."""
        config = TestingConfig()
        client = MQTTClient(config)

        # Empty topic parts
        assert client._topic_matches("test//sensor", "test//sensor") is True

        # Pattern longer than topic
        assert client._topic_matches("test/room1/temp", "test/room1") is False

        # Topic longer than pattern (without wildcard)
        assert client._topic_matches("test/room1", "test/room1/temp") is False


class TestMQTTClientCallbacks:
    """Tests for MQTT client callback handling."""

    def test_on_message_callback(self):
        """Test message callback invocation."""
        config = TestingConfig()
        client = MQTTClient(config)
        client._connected = True

        callback = Mock()
        client._message_callbacks["test/topic"] = [callback]

        # Simulate incoming message
        mock_message = Mock()
        mock_message.topic = "test/topic"
        mock_message.payload = b"test payload"

        client._on_message(None, None, mock_message)

        callback.assert_called_once_with("test/topic", "test payload")

    def test_on_message_wildcard_callback(self):
        """Test message callback with wildcard subscription."""
        config = TestingConfig()
        client = MQTTClient(config)
        client._connected = True

        callback = Mock()
        client._message_callbacks["test/+/sensor"] = [callback]

        # Simulate incoming message matching pattern
        mock_message = Mock()
        mock_message.topic = "test/room1/sensor"
        mock_message.payload = b"25.5"

        client._on_message(None, None, mock_message)

        callback.assert_called_once_with("test/room1/sensor", "25.5")

    def test_on_message_binary_payload(self):
        """Test message callback with binary payload."""
        config = TestingConfig()
        client = MQTTClient(config)
        client._connected = True

        callback = Mock()
        client._message_callbacks["test/topic"] = [callback]

        # Simulate incoming binary message
        mock_message = Mock()
        mock_message.topic = "test/topic"
        mock_message.payload = b"\x00\x01\x02\xff"

        client._on_message(None, None, mock_message)

        # Binary payload should be converted to hex string
        callback.assert_called_once()
        args = callback.call_args[0]
        assert args[0] == "test/topic"
        assert args[1] == "000102ff"

    def test_on_message_multiple_callbacks(self):
        """Test multiple callbacks for matching patterns."""
        config = TestingConfig()
        client = MQTTClient(config)
        client._connected = True

        callback1 = Mock()
        callback2 = Mock()
        client._message_callbacks["test/+"] = [callback1]
        client._message_callbacks["#"] = [callback2]

        # Simulate incoming message
        mock_message = Mock()
        mock_message.topic = "test/room1"
        mock_message.payload = b"data"

        client._on_message(None, None, mock_message)

        # Both callbacks should be called
        callback1.assert_called_once_with("test/room1", "data")
        callback2.assert_called_once_with("test/room1", "data")

    def test_on_message_callback_exception(self):
        """Test that callback exceptions are handled gracefully."""
        config = TestingConfig()
        client = MQTTClient(config)
        client._connected = True

        callback_error = Mock(side_effect=Exception("Callback error"))
        callback_ok = Mock()
        client._message_callbacks["test/topic"] = [callback_error, callback_ok]

        # Simulate incoming message
        mock_message = Mock()
        mock_message.topic = "test/topic"
        mock_message.payload = b"data"

        # Should not raise exception
        client._on_message(None, None, mock_message)

        # Both callbacks should be called despite error
        callback_error.assert_called_once()
        callback_ok.assert_called_once()

    def test_on_connect_resubscribes(self):
        """Test that on_connect resubscribes to all topics."""
        mock_paho_client = Mock()
        config = TestingConfig()
        client = MQTTClient(config)
        client._client = mock_paho_client

        # Set up existing subscriptions
        callback1 = Mock()
        callback2 = Mock()
        client._message_callbacks = {
            "test/topic1": [callback1],
            "test/topic2": [callback2],
        }

        # Simulate connection
        reason_code = Mock()
        reason_code.is_failure = False
        client._on_connect(mock_paho_client, None, None, 0, None)

        assert client.is_connected is True
        # Should resubscribe to all topics
        assert mock_paho_client.subscribe.call_count == 2

    def test_on_disconnect_sets_flag(self):
        """Test that on_disconnect sets connected flag to False."""
        config = TestingConfig()
        client = MQTTClient(config)
        client._connected = True
        client._stop_reconnect.set()  # Prevent reconnect thread

        client._on_disconnect(None, None, None, None, None)

        assert client.is_connected is False


class TestMQTTClientGlobalFunctions:
    """Tests for global MQTT client functions."""

    @patch("app.mqtt_client._mqtt_client", None)
    def test_get_mqtt_client_creates_instance(self):
        """Test that get_mqtt_client creates instance if None."""
        from app.mqtt_client import get_mqtt_client

        client = get_mqtt_client()
        assert client is not None
        assert isinstance(client, MQTTClient)

    @patch("app.mqtt_client._mqtt_client", None)
    def test_init_mqtt_client(self):
        """Test init_mqtt_client function."""
        from app.mqtt_client import init_mqtt_client

        config = TestingConfig()

        with patch.object(MQTTClient, "connect", return_value=True):
            client = init_mqtt_client(config)

            assert client is not None
            assert client.config == config
