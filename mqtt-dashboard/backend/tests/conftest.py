"""
Pytest configuration and fixtures for MQTT Dashboard tests.

This module provides common test fixtures including Flask app, test client,
and mocked MQTT client instances.
"""

import pytest
from unittest.mock import Mock, MagicMock
import paho.mqtt.client as mqtt

from app import create_app
from app.config import TestingConfig
from app.mqtt_client import MQTTClient
from app.models.broker_stats import BrokerStats
from app.services.sys_monitor import SysMonitor


@pytest.fixture
def app():
    """
    Create and configure a Flask application instance for testing.

    Returns:
        Flask application configured for testing.
    """
    test_app = create_app("testing")
    test_app.config.update({
        "TESTING": True,
    })

    yield test_app


@pytest.fixture
def client(app):
    """
    Create a Flask test client.

    Args:
        app: Flask application fixture.

    Returns:
        Flask test client for making HTTP requests.
    """
    return app.test_client()


@pytest.fixture
def mock_mqtt_client():
    """
    Create a mock MQTT client for testing.

    Returns:
        Mock MQTTClient instance with common methods stubbed.
    """
    mock_client = Mock(spec=MQTTClient)
    mock_client.config = TestingConfig()
    mock_client.is_connected = True
    mock_client._connected = True
    mock_client._client = Mock(spec=mqtt.Client)
    mock_client._message_callbacks = {}

    # Mock common methods
    mock_client.connect.return_value = True
    mock_client.disconnect.return_value = None
    mock_client.publish.return_value = True
    mock_client.subscribe.return_value = True
    mock_client.unsubscribe.return_value = True

    return mock_client


@pytest.fixture
def mock_sys_monitor(mock_mqtt_client):
    """
    Create a mock SysMonitor instance for testing.

    Args:
        mock_mqtt_client: Mock MQTT client fixture.

    Returns:
        Mock SysMonitor instance with sample broker stats.
    """
    monitor = Mock(spec=SysMonitor)
    monitor._mqtt_client = mock_mqtt_client
    monitor._subscribed = True
    monitor.is_subscribed = True

    # Create sample broker stats
    sample_stats = BrokerStats(
        version="mosquitto version 2.0.18",
        uptime=3600,
        clients_connected=5,
        clients_disconnected=2,
        clients_total=7,
        clients_maximum=10,
        clients_expired=1,
        messages_received=1000,
        messages_sent=800,
        messages_stored=50,
        bytes_received=102400,
        bytes_sent=81920,
        subscriptions_count=15,
        retained_messages_count=3,
        load_messages_received_1min=10.5,
        load_messages_sent_1min=8.2,
    )

    monitor.get_stats.return_value = sample_stats
    monitor.subscribe.return_value = True
    monitor.unsubscribe.return_value = True

    return monitor


@pytest.fixture
def disconnected_mqtt_client():
    """
    Create a disconnected mock MQTT client for testing error conditions.

    Returns:
        Mock MQTTClient instance in disconnected state.
    """
    mock_client = Mock(spec=MQTTClient)
    mock_client.config = TestingConfig()
    mock_client.is_connected = False
    mock_client._connected = False
    mock_client._client = None

    mock_client.connect.return_value = False
    mock_client.publish.return_value = False
    mock_client.subscribe.return_value = False

    return mock_client


@pytest.fixture
def sample_broker_stats():
    """
    Create a sample BrokerStats instance for testing.

    Returns:
        BrokerStats instance with sample data.
    """
    return BrokerStats(
        version="mosquitto version 2.0.18",
        uptime=7200,
        clients_connected=10,
        clients_disconnected=5,
        clients_total=15,
        clients_maximum=20,
        clients_expired=2,
        messages_received=5000,
        messages_sent=4500,
        messages_stored=100,
        messages_inflight=5,
        messages_dropped=2,
        publish_messages_received=4800,
        publish_messages_sent=4300,
        bytes_received=512000,
        bytes_sent=460800,
        subscriptions_count=25,
        retained_messages_count=10,
        load_messages_received_1min=15.5,
        load_messages_received_5min=12.3,
        load_messages_received_15min=10.1,
        load_messages_sent_1min=14.2,
        load_messages_sent_5min=11.5,
        load_messages_sent_15min=9.8,
        load_bytes_received_1min=1024.0,
        load_bytes_sent_1min=920.0,
        load_connections_1min=0.5,
        load_connections_5min=0.3,
        load_connections_15min=0.2,
        heap_current=2048000,
        heap_maximum=4096000,
    )
