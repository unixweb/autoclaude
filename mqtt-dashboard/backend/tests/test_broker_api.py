"""
Unit tests for Broker API endpoints.

This module tests the REST API endpoints for broker status, statistics,
and version information.
"""

import pytest
from unittest.mock import patch, Mock
from datetime import datetime, timezone

from app.models.broker_stats import BrokerStats


class TestBrokerStatus:
    """Tests for GET /api/broker/status endpoint."""

    @patch("app.routes.broker.get_mqtt_client")
    @patch("app.routes.broker.get_sys_monitor")
    def test_broker_status_connected(self, mock_get_monitor, mock_get_client, client, mock_mqtt_client, mock_sys_monitor):
        """Test broker status endpoint when connected."""
        mock_get_client.return_value = mock_mqtt_client
        mock_get_monitor.return_value = mock_sys_monitor

        response = client.get("/api/broker/status")
        assert response.status_code == 200

        data = response.get_json()
        assert data["connected"] is True
        assert data["broker"]["host"] == mock_mqtt_client.config.MQTT_BROKER_HOST
        assert data["broker"]["port"] == mock_mqtt_client.config.MQTT_BROKER_PORT
        assert data["sys_monitor"]["subscribed"] is True

    @patch("app.routes.broker.get_mqtt_client")
    @patch("app.routes.broker.get_sys_monitor")
    def test_broker_status_disconnected(self, mock_get_monitor, mock_get_client, client, disconnected_mqtt_client):
        """Test broker status endpoint when disconnected."""
        mock_monitor = Mock()
        mock_monitor.is_subscribed = False

        mock_get_client.return_value = disconnected_mqtt_client
        mock_get_monitor.return_value = mock_monitor

        response = client.get("/api/broker/status")
        assert response.status_code == 200

        data = response.get_json()
        assert data["connected"] is False
        assert data["sys_monitor"]["subscribed"] is False


class TestBrokerStats:
    """Tests for GET /api/broker/stats endpoint."""

    @patch("app.routes.broker.get_mqtt_client")
    @patch("app.routes.broker.get_sys_monitor")
    def test_broker_stats_success(self, mock_get_monitor, mock_get_client, client, mock_mqtt_client, sample_broker_stats):
        """Test successful retrieval of broker statistics."""
        mock_monitor = Mock()
        mock_monitor.is_subscribed = True
        mock_monitor.get_stats.return_value = sample_broker_stats

        mock_get_client.return_value = mock_mqtt_client
        mock_get_monitor.return_value = mock_monitor

        response = client.get("/api/broker/stats")
        assert response.status_code == 200

        data = response.get_json()
        assert data["broker"]["version"] == "mosquitto version 2.0.18"
        assert data["broker"]["uptime"] == 7200
        assert data["clients"]["connected"] == 10
        assert data["clients"]["total"] == 15
        assert data["messages"]["received"] == 5000
        assert data["bytes"]["received"] == 512000

    @patch("app.routes.broker.get_mqtt_client")
    def test_broker_stats_disconnected(self, mock_get_client, client, disconnected_mqtt_client):
        """Test broker stats endpoint when broker is disconnected."""
        mock_get_client.return_value = disconnected_mqtt_client

        response = client.get("/api/broker/stats")
        assert response.status_code == 503

        data = response.get_json()
        assert "error" in data
        assert data["code"] == "BROKER_DISCONNECTED"

    @patch("app.routes.broker.get_mqtt_client")
    @patch("app.routes.broker.get_sys_monitor")
    def test_broker_stats_not_subscribed(self, mock_get_monitor, mock_get_client, client, mock_mqtt_client):
        """Test broker stats endpoint when sys monitor not subscribed."""
        mock_monitor = Mock()
        mock_monitor.is_subscribed = False

        mock_get_client.return_value = mock_mqtt_client
        mock_get_monitor.return_value = mock_monitor

        response = client.get("/api/broker/stats")
        assert response.status_code == 503

        data = response.get_json()
        assert "error" in data
        assert data["code"] == "SYS_NOT_SUBSCRIBED"


class TestBrokerStatsSummary:
    """Tests for GET /api/broker/stats/summary endpoint."""

    @patch("app.routes.broker.get_mqtt_client")
    @patch("app.routes.broker.get_sys_monitor")
    def test_broker_stats_summary_success(self, mock_get_monitor, mock_get_client, client, mock_mqtt_client, sample_broker_stats):
        """Test successful retrieval of broker statistics summary."""
        mock_monitor = Mock()
        mock_monitor.is_subscribed = True
        mock_monitor.get_stats.return_value = sample_broker_stats

        mock_get_client.return_value = mock_mqtt_client
        mock_get_monitor.return_value = mock_monitor

        response = client.get("/api/broker/stats/summary")
        assert response.status_code == 200

        data = response.get_json()
        assert data["version"] == "mosquitto version 2.0.18"
        assert data["uptime"] == 7200
        assert data["clients_connected"] == 10
        assert data["clients_total"] == 15
        assert data["messages_received"] == 5000
        assert data["messages_sent"] == 4500

    @patch("app.routes.broker.get_mqtt_client")
    def test_broker_stats_summary_disconnected(self, mock_get_client, client, disconnected_mqtt_client):
        """Test summary endpoint when broker is disconnected."""
        mock_get_client.return_value = disconnected_mqtt_client

        response = client.get("/api/broker/stats/summary")
        assert response.status_code == 503

        data = response.get_json()
        assert data["code"] == "BROKER_DISCONNECTED"


class TestBrokerVersion:
    """Tests for GET /api/broker/version endpoint."""

    @patch("app.routes.broker.get_mqtt_client")
    @patch("app.routes.broker.get_sys_monitor")
    def test_broker_version_success(self, mock_get_monitor, mock_get_client, client, mock_mqtt_client):
        """Test successful retrieval of broker version."""
        stats = BrokerStats(
            version="mosquitto version 2.0.18",
            uptime=3665  # 1h 1m 5s
        )

        mock_monitor = Mock()
        mock_monitor.is_subscribed = True
        mock_monitor.get_stats.return_value = stats

        mock_get_client.return_value = mock_mqtt_client
        mock_get_monitor.return_value = mock_monitor

        response = client.get("/api/broker/version")
        assert response.status_code == 200

        data = response.get_json()
        assert data["version"] == "mosquitto version 2.0.18"
        assert data["uptime"] == 3665
        assert "1h" in data["uptime_formatted"]
        assert "1m" in data["uptime_formatted"]
        assert "5s" in data["uptime_formatted"]

    @patch("app.routes.broker.get_mqtt_client")
    @patch("app.routes.broker.get_sys_monitor")
    def test_broker_version_uptime_formatting(self, mock_get_monitor, mock_get_client, client, mock_mqtt_client):
        """Test uptime formatting for different durations."""
        test_cases = [
            (45, "45s"),  # Seconds only
            (125, "2m 5s"),  # Minutes and seconds
            (3665, "1h 1m 5s"),  # Hours, minutes, seconds
            (90061, "1d 1h 1m 1s"),  # Days, hours, minutes, seconds
        ]

        for uptime, expected_format in test_cases:
            stats = BrokerStats(
                version="mosquitto version 2.0.18",
                uptime=uptime
            )

            mock_monitor = Mock()
            mock_monitor.is_subscribed = True
            mock_monitor.get_stats.return_value = stats

            mock_get_client.return_value = mock_mqtt_client
            mock_get_monitor.return_value = mock_monitor

            response = client.get("/api/broker/version")
            assert response.status_code == 200

            data = response.get_json()
            assert data["uptime_formatted"] == expected_format

    @patch("app.routes.broker.get_mqtt_client")
    @patch("app.routes.broker.get_sys_monitor")
    def test_broker_version_null_uptime(self, mock_get_monitor, mock_get_client, client, mock_mqtt_client):
        """Test version endpoint when uptime is None."""
        stats = BrokerStats(version="mosquitto version 2.0.18", uptime=None)

        mock_monitor = Mock()
        mock_monitor.is_subscribed = True
        mock_monitor.get_stats.return_value = stats

        mock_get_client.return_value = mock_mqtt_client
        mock_get_monitor.return_value = mock_monitor

        response = client.get("/api/broker/version")
        assert response.status_code == 200

        data = response.get_json()
        assert data["uptime"] is None
        assert data["uptime_formatted"] is None

    @patch("app.routes.broker.get_mqtt_client")
    def test_broker_version_disconnected(self, mock_get_client, client, disconnected_mqtt_client):
        """Test version endpoint when broker is disconnected."""
        mock_get_client.return_value = disconnected_mqtt_client

        response = client.get("/api/broker/version")
        assert response.status_code == 503

        data = response.get_json()
        assert data["code"] == "BROKER_DISCONNECTED"
