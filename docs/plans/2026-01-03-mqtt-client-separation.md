# MQTT Client Separation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Separate MQTT client into standalone process communicating with dashboard via Redis pub/sub to eliminate threading conflicts and improve reliability.

**Architecture:** Dashboard Flask app handles HTTP/WebSocket, standalone MQTT client service handles broker communication. Redis pub/sub bridges the two: MQTT service publishes broker stats/messages to Redis channels, dashboard subscribes and forwards to WebSocket clients. Single MQTT connection, clean separation of concerns.

**Tech Stack:** Redis (pub/sub), Python redis library, Docker Compose multi-service, existing Flask/paho-mqtt stack

---

## Problem Summary

Current architecture runs MQTT client inside Gunicorn workers with threading, causing:
- Multiple simultaneous connections with same client ID
- MQTT keepalive failures (loop stops sending packets)
- Unstable broker connections
- Threading conflicts between Flask, SocketIO, and paho-mqtt

Root cause: Gunicorn threads each initialize MQTT client, creating connection churn.

Solution: Separate MQTT client as independent process, communicate via Redis.

---

## Task 1: Add Redis Infrastructure

**Files:**
- Modify: `docker-compose.yml`
- Modify: `.env.example`
- Modify: `mqtt-dashboard/backend/requirements.txt`

**Step 1: Add Redis service to docker-compose.yml**

Add after mosquitto service (line 239):

```yaml
  # ---------------------------------------------------------------------------
  # Redis (Message Broker for MQTT-Dashboard Communication)
  # ---------------------------------------------------------------------------
  # Redis serves as pub/sub broker between MQTT client service and dashboard
  redis:
    image: redis:7-alpine
    container_name: app_redis
    restart: unless-stopped

    ports:
      - "${REDIS_PORT:-6379}:6379"

    volumes:
      - redis_data:/data

    networks:
      - app_network

    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s

    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
```

**Step 2: Add Redis volume to docker-compose.yml**

Add to volumes section (after mosquitto_logs, line 342):

```yaml
  # Redis persistent data
  redis_data:
    driver: local
```

**Step 3: Add Redis environment variables to .env.example**

Add after MQTT_WSS_PORT (around line 210):

```bash
# =============================================================================
# Redis Configuration (Message Broker)
# =============================================================================
# Redis is used for pub/sub communication between MQTT client and dashboard

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=
# Leave empty for no password (development)
# For production, set a strong password
```

**Step 4: Add redis Python library to requirements.txt**

Add after paho-mqtt line:

```
# Redis client for pub/sub
redis>=5.0.0
```

**Step 5: Verify Redis starts**

```bash
docker compose up -d redis
docker compose logs redis --tail 20
```

Expected: "Ready to accept connections" message

**Step 6: Commit infrastructure**

```bash
git add docker-compose.yml .env.example mqtt-dashboard/backend/requirements.txt
git commit -m "feat: add Redis infrastructure for MQTT-dashboard communication"
```

---

## Task 2: Create Redis Pub/Sub Abstraction Layer

**Files:**
- Create: `mqtt-dashboard/backend/app/redis_client.py`
- Create: `tests/test_redis_client.py`

**Step 1: Write test for Redis connection**

Create `tests/test_redis_client.py`:

```python
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
```

**Step 2: Run test to verify it fails**

```bash
cd mqtt-dashboard/backend
pytest tests/test_redis_client.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'app.redis_client'"

**Step 3: Implement RedisClient class**

Create `mqtt-dashboard/backend/app/redis_client.py`:

```python
"""
Redis Client Module

Provides pub/sub abstraction for communication between MQTT client service
and dashboard web application.
"""

import json
import logging
import threading
from typing import Any, Callable, Optional

import redis

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Redis pub/sub client for inter-service communication.

    Provides thread-safe publish and subscribe operations for JSON messages.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0,
    ):
        """
        Initialize Redis client.

        Args:
            host: Redis server hostname
            port: Redis server port
            password: Optional password for authentication
            db: Database number (default: 0)
        """
        self.host = host
        self.port = port
        self.password = password
        self.db = db

        # Create Redis connection
        self._redis = redis.Redis(
            host=host,
            port=port,
            password=password if password else None,
            db=db,
            decode_responses=True,
        )

        # Pub/sub instance
        self._pubsub = self._redis.pubsub()
        self._subscriptions: dict[str, Callable] = {}
        self._subscriber_thread: Optional[threading.Thread] = None
        self._stop_subscriber = threading.Event()

    def is_connected(self) -> bool:
        """Check if connected to Redis."""
        try:
            self._redis.ping()
            return True
        except Exception:
            return False

    def publish(self, channel: str, message: dict[str, Any]) -> bool:
        """
        Publish JSON message to channel.

        Args:
            channel: Redis channel name
            message: Dictionary to publish as JSON

        Returns:
            True if published successfully
        """
        try:
            payload = json.dumps(message)
            self._redis.publish(channel, payload)
            return True
        except Exception as e:
            logger.error(f"Failed to publish to {channel}: {e}")
            return False

    def subscribe(self, channel: str, callback: Callable[[dict], None]) -> bool:
        """
        Subscribe to channel with callback.

        Args:
            channel: Redis channel name
            callback: Function called with decoded JSON message

        Returns:
            True if subscribed successfully
        """
        try:
            self._subscriptions[channel] = callback
            self._pubsub.subscribe(channel)

            # Start subscriber thread if not running
            if self._subscriber_thread is None or not self._subscriber_thread.is_alive():
                self._start_subscriber_thread()

            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to {channel}: {e}")
            return False

    def unsubscribe(self, channel: str) -> bool:
        """Unsubscribe from channel."""
        try:
            if channel in self._subscriptions:
                del self._subscriptions[channel]
                self._pubsub.unsubscribe(channel)
            return True
        except Exception as e:
            logger.error(f"Failed to unsubscribe from {channel}: {e}")
            return False

    def _start_subscriber_thread(self) -> None:
        """Start background thread for message processing."""
        self._stop_subscriber.clear()
        self._subscriber_thread = threading.Thread(
            target=self._subscriber_loop,
            daemon=True,
        )
        self._subscriber_thread.start()

    def _subscriber_loop(self) -> None:
        """Background loop processing subscribed messages."""
        logger.info("Redis subscriber loop started")

        for message in self._pubsub.listen():
            if self._stop_subscriber.is_set():
                break

            if message["type"] == "message":
                channel = message["channel"]
                if channel in self._subscriptions:
                    try:
                        data = json.loads(message["data"])
                        self._subscriptions[channel](data)
                    except Exception as e:
                        logger.error(f"Error processing message from {channel}: {e}")

        logger.info("Redis subscriber loop stopped")

    def disconnect(self) -> None:
        """Disconnect from Redis."""
        self._stop_subscriber.set()
        if self._subscriber_thread and self._subscriber_thread.is_alive():
            self._subscriber_thread.join(timeout=2)

        self._pubsub.close()
        self._redis.close()


# Global Redis client instance
_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """
    Get the global Redis client instance.

    Returns:
        The global RedisClient instance.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client


def init_redis_client(
    host: str = "localhost",
    port: int = 6379,
    password: Optional[str] = None,
) -> RedisClient:
    """
    Initialize and connect the global Redis client.

    Args:
        host: Redis server hostname
        port: Redis server port
        password: Optional password

    Returns:
        The initialized RedisClient instance.
    """
    global _redis_client
    _redis_client = RedisClient(host=host, port=port, password=password)
    return _redis_client
```

**Step 4: Run tests**

```bash
pytest tests/test_redis_client.py -v
```

Expected: PASS (all tests green)

**Step 5: Commit Redis client**

```bash
git add mqtt-dashboard/backend/app/redis_client.py tests/test_redis_client.py
git commit -m "feat: add Redis pub/sub client abstraction layer"
```

---

## Task 3: Define Redis Channel Schema

**Files:**
- Create: `mqtt-dashboard/backend/app/redis_channels.py`
- Create: `tests/test_redis_channels.py`

**Step 1: Write test for channel constants**

Create `tests/test_redis_channels.py`:

```python
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
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_redis_channels.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'app.redis_channels'"

**Step 3: Implement channel schema**

Create `mqtt-dashboard/backend/app/redis_channels.py`:

```python
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
```

**Step 4: Run tests**

```bash
pytest tests/test_redis_channels.py -v
```

Expected: PASS

**Step 5: Commit channel schema**

```bash
git add mqtt-dashboard/backend/app/redis_channels.py tests/test_redis_channels.py
git commit -m "feat: define Redis channel schema for MQTT-dashboard communication"
```

---

## Task 4: Create Standalone MQTT Client Service

**Files:**
- Create: `mqtt-dashboard/backend/mqtt_service.py`
- Create: `mqtt-dashboard/backend/app/mqtt_bridge.py`
- Create: `tests/test_mqtt_bridge.py`

**Step 1: Write test for MQTT bridge**

Create `tests/test_mqtt_bridge.py`:

```python
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
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_mqtt_bridge.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'app.mqtt_bridge'"

**Step 3: Implement MQTT-Redis bridge**

Create `mqtt-dashboard/backend/app/mqtt_bridge.py`:

```python
"""
MQTT-Redis Bridge

Bridges MQTT broker and Redis pub/sub for dashboard communication.
Runs as standalone service, maintains single MQTT connection.
"""

import logging
import time
from typing import Optional

from app.config import Config
from app.mqtt_client import MQTTClient
from app.redis_client import RedisClient
from app.redis_channels import RedisChannels, MessageTypes
from app.models.broker_stats import BrokerStats

logger = logging.getLogger(__name__)


class MQTTBridge:
    """
    Bridge between MQTT broker and Redis pub/sub.

    Subscribes to MQTT broker ($SYS topics and user topics),
    publishes messages to Redis for dashboard consumption.
    Listens for commands from Redis, executes via MQTT.
    """

    def __init__(
        self,
        mqtt_host: str,
        mqtt_port: int,
        redis_host: str,
        redis_port: int,
        mqtt_username: Optional[str] = None,
        mqtt_password: Optional[str] = None,
        redis_password: Optional[str] = None,
    ):
        """Initialize bridge with MQTT and Redis connections."""
        # Create config for MQTT
        config = Config()
        config.MQTT_BROKER_HOST = mqtt_host
        config.MQTT_BROKER_PORT = mqtt_port
        config.MQTT_USERNAME = mqtt_username or ""
        config.MQTT_PASSWORD = mqtt_password or ""
        config.MQTT_CLIENT_ID = "mqtt-bridge-service"

        # Initialize clients
        self.mqtt_client = MQTTClient(config)
        self.redis_client = RedisClient(
            host=redis_host,
            port=redis_port,
            password=redis_password,
        )

        # Stats cache
        self._stats = BrokerStats()
        self._last_stats_publish = 0
        self.stats_publish_interval = 5  # Publish stats every 5s

    def start(self) -> bool:
        """Start the bridge service."""
        logger.info("Starting MQTT-Redis bridge...")

        # Connect to MQTT
        if not self.mqtt_client.connect():
            logger.error("Failed to connect to MQTT broker")
            return False

        logger.info("Connected to MQTT broker")

        # Subscribe to $SYS topics
        self.mqtt_client.subscribe("$SYS/#", self._handle_sys_message, qos=0)
        logger.info("Subscribed to $SYS/# topics")

        # Subscribe to commands channel on Redis
        self.redis_client.subscribe(RedisChannels.COMMANDS, self._handle_command)
        logger.info("Subscribed to Redis command channel")

        # Publish initial status
        self._publish_status(connected=True)

        logger.info("MQTT-Redis bridge started successfully")
        return True

    def _handle_sys_message(self, topic: str, payload: str) -> None:
        """Handle message from $SYS topics."""
        # Update stats cache
        self._update_stats_from_sys(topic, payload)

        # Publish stats periodically
        now = time.time()
        if now - self._last_stats_publish >= self.stats_publish_interval:
            self._publish_stats()
            self._last_stats_publish = now

    def _update_stats_from_sys(self, topic: str, payload: str) -> None:
        """Update stats cache from $SYS topic."""
        # Map topic to stats attribute
        topic_map = {
            "$SYS/broker/version": ("version", str),
            "$SYS/broker/uptime": ("uptime", int),
            "$SYS/broker/clients/connected": ("clients_connected", int),
            "$SYS/broker/clients/total": ("clients_total", int),
            "$SYS/broker/messages/received": ("messages_received", int),
            "$SYS/broker/messages/sent": ("messages_sent", int),
            "$SYS/broker/bytes/received": ("bytes_received", int),
            "$SYS/broker/bytes/sent": ("bytes_sent", int),
        }

        if topic in topic_map:
            attr_name, attr_type = topic_map[topic]
            try:
                value = attr_type(payload)
                setattr(self._stats, attr_name, value)
            except (ValueError, TypeError):
                pass

    def _publish_stats(self) -> None:
        """Publish broker stats to Redis."""
        message = {
            "type": MessageTypes.STATS_UPDATE,
            "data": self._stats.to_dict(),
        }
        self.redis_client.publish(RedisChannels.BROKER_STATS, message)

    def _publish_status(self, connected: bool) -> None:
        """Publish broker connection status to Redis."""
        message = {
            "type": MessageTypes.STATUS_CHANGE,
            "connected": connected,
            "timestamp": time.time(),
        }
        self.redis_client.publish(RedisChannels.BROKER_STATUS, message)

    def _handle_command(self, command: dict) -> None:
        """Handle command from Redis."""
        cmd_type = command.get("type")

        if cmd_type == MessageTypes.CMD_PUBLISH:
            topic = command.get("topic", "")
            payload = command.get("payload", "")
            qos = command.get("qos", 0)
            retain = command.get("retain", False)

            self.mqtt_client.publish(topic, payload, qos=qos, retain=retain)
            logger.info(f"Published to {topic}")

        elif cmd_type == MessageTypes.CMD_SUBSCRIBE:
            topic = command.get("topic", "")
            qos = command.get("qos", 0)

            # Subscribe and forward messages to Redis
            self.mqtt_client.subscribe(
                topic,
                lambda t, p: self._forward_mqtt_message(t, p),
                qos=qos,
            )
            logger.info(f"Subscribed to {topic}")

        elif cmd_type == MessageTypes.CMD_UNSUBSCRIBE:
            topic = command.get("topic", "")
            self.mqtt_client.unsubscribe(topic)
            logger.info(f"Unsubscribed from {topic}")

    def _forward_mqtt_message(self, topic: str, payload: str) -> None:
        """Forward MQTT message to Redis."""
        message = {
            "type": MessageTypes.MESSAGE_RECEIVED,
            "topic": topic,
            "payload": payload,
            "timestamp": time.time(),
        }
        self.redis_client.publish(RedisChannels.MQTT_MESSAGES, message)

    def run(self) -> None:
        """Run the bridge (blocking)."""
        try:
            logger.info("Bridge running... Press Ctrl+C to stop")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down bridge...")
            self.stop()

    def stop(self) -> None:
        """Stop the bridge service."""
        self._publish_status(connected=False)
        self.mqtt_client.disconnect()
        self.redis_client.disconnect()
        logger.info("Bridge stopped")
```

**Step 4: Create service entry point**

Create `mqtt-dashboard/backend/mqtt_service.py`:

```python
#!/usr/bin/env python3
"""
MQTT Bridge Service Entry Point

Standalone service that maintains MQTT connection and bridges to Redis.
"""

import logging
import os
import sys

from app.mqtt_bridge import MQTTBridge

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for MQTT bridge service."""
    # Get configuration from environment
    mqtt_host = os.environ.get("MQTT_BROKER_HOST", "mosquitto")
    mqtt_port = int(os.environ.get("MQTT_BROKER_PORT", "1883"))
    mqtt_username = os.environ.get("MQTT_USERNAME")
    mqtt_password = os.environ.get("MQTT_PASSWORD")

    redis_host = os.environ.get("REDIS_HOST", "redis")
    redis_port = int(os.environ.get("REDIS_PORT", "6379"))
    redis_password = os.environ.get("REDIS_PASSWORD")

    logger.info("=" * 60)
    logger.info("MQTT Bridge Service Starting")
    logger.info("=" * 60)
    logger.info(f"MQTT Broker: {mqtt_host}:{mqtt_port}")
    logger.info(f"Redis Server: {redis_host}:{redis_port}")
    logger.info("=" * 60)

    # Create and start bridge
    bridge = MQTTBridge(
        mqtt_host=mqtt_host,
        mqtt_port=mqtt_port,
        mqtt_username=mqtt_username,
        mqtt_password=mqtt_password,
        redis_host=redis_host,
        redis_port=redis_port,
        redis_password=redis_password,
    )

    if not bridge.start():
        logger.error("Failed to start bridge")
        sys.exit(1)

    # Run forever
    bridge.run()


if __name__ == "__main__":
    main()
```

**Step 5: Run tests**

```bash
pytest tests/test_mqtt_bridge.py -v
```

Expected: PASS

**Step 6: Commit MQTT bridge service**

```bash
chmod +x mqtt-dashboard/backend/mqtt_service.py
git add mqtt-dashboard/backend/mqtt_service.py mqtt-dashboard/backend/app/mqtt_bridge.py tests/test_mqtt_bridge.py
git commit -m "feat: create standalone MQTT-Redis bridge service"
```

---

## Task 5: Add MQTT Bridge Service to Docker Compose

**Files:**
- Modify: `docker-compose.yml`
- Create: `mqtt-dashboard/Dockerfile.mqtt-service`

**Step 1: Create Dockerfile for MQTT service**

Create `mqtt-dashboard/Dockerfile.mqtt-service`:

```dockerfile
# MQTT Bridge Service Docker Image
# Standalone service for MQTT broker communication
# =====================================================

FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 mqttservice \
    && useradd --uid 1000 --gid mqttservice --shell /bin/bash --create-home mqttservice

# Copy requirements and install dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./

# Change ownership
RUN chown -R mqttservice:mqttservice /app

# Switch to non-root user
USER mqttservice

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "from app.redis_client import RedisClient; r = RedisClient(); exit(0 if r.is_connected() else 1)"

# Run the bridge service
CMD ["python", "mqtt_service.py"]
```

**Step 2: Add mqtt-bridge service to docker-compose.yml**

Add after mqtt-dashboard service (around line 305):

```yaml
  # ---------------------------------------------------------------------------
  # MQTT Bridge Service (Standalone MQTT Client)
  # ---------------------------------------------------------------------------
  # Dedicated service that maintains MQTT connection and bridges to Redis.
  # Eliminates threading conflicts in dashboard workers.
  mqtt-bridge:
    build:
      context: ./mqtt-dashboard
      dockerfile: Dockerfile.mqtt-service

    container_name: app_mqtt_bridge

    restart: unless-stopped

    environment:
      # MQTT Configuration
      - MQTT_BROKER_HOST=${MQTT_BROKER_HOST:-mosquitto}
      - MQTT_BROKER_PORT=${MQTT_BROKER_PORT:-1883}
      - MQTT_USERNAME=${MQTT_USERNAME:-}
      - MQTT_PASSWORD=${MQTT_PASSWORD:-}

      # Redis Configuration
      - REDIS_HOST=${REDIS_HOST:-redis}
      - REDIS_PORT=${REDIS_PORT:-6379}
      - REDIS_PASSWORD=${REDIS_PASSWORD:-}

    networks:
      - app_network

    depends_on:
      mosquitto:
        condition: service_healthy
      redis:
        condition: service_healthy

    healthcheck:
      test: ["CMD", "python", "-c", "from app.redis_client import RedisClient; r = RedisClient(); exit(0 if r.is_connected() else 1)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s
```

**Step 3: Build and start MQTT bridge service**

```bash
docker compose build mqtt-bridge
docker compose up -d mqtt-bridge
```

**Step 4: Verify service is running**

```bash
docker compose logs mqtt-bridge --tail 30
```

Expected: "MQTT-Redis bridge started successfully"

**Step 5: Verify MQTT connection**

```bash
docker compose logs mosquitto | grep mqtt-bridge
```

Expected: "New client connected... as mqtt-bridge-service"

**Step 6: Commit Docker integration**

```bash
git add docker-compose.yml mqtt-dashboard/Dockerfile.mqtt-service
git commit -m "feat: add MQTT bridge service to Docker Compose"
```

---

## Task 6: Modify Dashboard to Use Redis Instead of Direct MQTT

**Files:**
- Modify: `mqtt-dashboard/backend/app/__init__.py`
- Modify: `mqtt-dashboard/backend/wsgi.py` (in Dockerfile)
- Modify: `mqtt-dashboard/backend/app/routes/broker.py`
- Modify: `mqtt-dashboard/backend/app/websocket.py`

**Step 1: Update wsgi.py to use Redis instead of MQTT**

Modify Dockerfile lines 65-136 to replace MQTT initialization with Redis:

```python
"""
WSGI entry point for the MQTT Dashboard.
"""

import os
from flask import send_from_directory, send_file

from app import create_app
from app.config import get_config
from app.redis_client import init_redis_client
from app.websocket import init_socketio, start_background_stats_pusher


def create_production_app():
    """Create and configure the production Flask application."""
    config_name = os.environ.get("FLASK_ENV", "production")
    config = get_config(config_name)

    app = create_app(config_name)

    # Initialize Redis client (replaces MQTT)
    redis_host = os.environ.get("REDIS_HOST", "redis")
    redis_port = int(os.environ.get("REDIS_PORT", "6379"))
    redis_password = os.environ.get("REDIS_PASSWORD")

    redis_client = init_redis_client(
        host=redis_host,
        port=redis_port,
        password=redis_password,
    )
    app.redis_client = redis_client

    # Initialize Flask-SocketIO for WebSocket support
    socketio = init_socketio(app)
    app.socketio = socketio

    # Start background stats pusher (now pulls from Redis)
    start_background_stats_pusher()

    # Serve static files from Vue.js build
    static_folder = os.path.join(os.path.dirname(__file__), "static")

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path):
        """Serve the Vue.js frontend application."""
        file_path = os.path.join(static_folder, path)
        if path and os.path.isfile(file_path):
            return send_from_directory(static_folder, path)
        return send_file(os.path.join(static_folder, "index.html"))

    return app, socketio


# Create the WSGI application instance and SocketIO
application, socketio = create_production_app()
app = application  # Alias for gunicorn
```

**Step 2: Update health check endpoint**

Modify `mqtt-dashboard/backend/app/__init__.py` health_check function (lines 38-62):

```python
@app.route("/health")
def health_check():
    """Health check endpoint for Docker and monitoring."""
    from app.redis_client import get_redis_client
    from app.websocket import get_socketio, get_connected_client_count

    redis_client = get_redis_client()
    redis_status = "connected" if redis_client and redis_client.is_connected() else "disconnected"

    socketio = get_socketio()
    websocket_status = "initialized" if socketio else "not_initialized"

    return {
        "status": "healthy",
        "service": "mqtt-dashboard",
        "redis": {
            "status": redis_status,
        },
        "websocket": {
            "status": websocket_status,
            "connected_clients": get_connected_client_count() if socketio else 0,
        },
    }
```

**Step 3: Update broker status route**

Modify `mqtt-dashboard/backend/app/routes/broker.py` (lines 36-50):

```python
@broker_bp.route("/status")
def get_broker_status():
    """Get the current broker connection status from Redis."""
    from app.redis_client import get_redis_client
    from app.redis_channels import RedisChannels

    redis_client = get_redis_client()

    # Last status is cached in Redis, we subscribe to updates
    # For now, return connected if Redis is connected
    # (Bridge service publishes actual MQTT status)

    status = {
        "connected": redis_client.is_connected(),
        "broker": {
            "host": "via mqtt-bridge",
            "port": 1883,
        },
    }

    return jsonify(status), 200
```

**Step 4: Rebuild dashboard image**

```bash
docker compose build mqtt-dashboard
docker compose up -d mqtt-dashboard
```

**Step 5: Verify dashboard uses Redis**

```bash
docker compose logs mqtt-dashboard | grep -i redis
```

Expected: No MQTT connection attempts, Redis connection established

**Step 6: Commit dashboard modifications**

```bash
git add mqtt-dashboard/backend/app/__init__.py mqtt-dashboard/backend/app/routes/broker.py
git commit -m "refactor: dashboard uses Redis instead of direct MQTT connection"
```

---

## Task 7: Update Dashboard to Subscribe to Redis Channels

**Files:**
- Modify: `mqtt-dashboard/backend/app/websocket.py`
- Create: `mqtt-dashboard/backend/app/redis_subscriber.py`

**Step 1: Create Redis subscriber for dashboard**

Create `mqtt-dashboard/backend/app/redis_subscriber.py`:

```python
"""
Redis Subscriber for Dashboard

Subscribes to Redis channels and forwards messages to WebSocket clients.
"""

import logging
from typing import Optional

from app.redis_client import RedisClient, get_redis_client
from app.redis_channels import RedisChannels, MessageTypes

logger = logging.getLogger(__name__)


class DashboardRedisSubscriber:
    """
    Subscribes to Redis channels from MQTT bridge.
    Forwards messages to WebSocket handlers.
    """

    def __init__(self, redis_client: Optional[RedisClient] = None):
        """Initialize subscriber."""
        self.redis_client = redis_client or get_redis_client()
        self._stats_callback = None
        self._status_callback = None
        self._message_callback = None

    def start(self) -> None:
        """Start subscribing to Redis channels."""
        logger.info("Starting Redis subscriptions for dashboard...")

        # Subscribe to broker stats
        self.redis_client.subscribe(
            RedisChannels.BROKER_STATS,
            self._handle_stats_update,
        )

        # Subscribe to broker status
        self.redis_client.subscribe(
            RedisChannels.BROKER_STATUS,
            self._handle_status_update,
        )

        # Subscribe to MQTT messages
        self.redis_client.subscribe(
            RedisChannels.MQTT_MESSAGES,
            self._handle_mqtt_message,
        )

        logger.info("Redis subscriptions active")

    def set_stats_callback(self, callback):
        """Set callback for stats updates."""
        self._stats_callback = callback

    def set_status_callback(self, callback):
        """Set callback for status updates."""
        self._status_callback = callback

    def set_message_callback(self, callback):
        """Set callback for MQTT messages."""
        self._message_callback = callback

    def _handle_stats_update(self, message: dict) -> None:
        """Handle broker stats update from Redis."""
        if message.get("type") == MessageTypes.STATS_UPDATE:
            if self._stats_callback:
                self._stats_callback(message.get("data", {}))

    def _handle_status_update(self, message: dict) -> None:
        """Handle broker status update from Redis."""
        if message.get("type") == MessageTypes.STATUS_CHANGE:
            if self._status_callback:
                self._status_callback(message)

    def _handle_mqtt_message(self, message: dict) -> None:
        """Handle MQTT message from Redis."""
        if message.get("type") == MessageTypes.MESSAGE_RECEIVED:
            if self._message_callback:
                self._message_callback(message)


# Global subscriber instance
_subscriber: Optional[DashboardRedisSubscriber] = None


def get_redis_subscriber() -> DashboardRedisSubscriber:
    """Get global Redis subscriber instance."""
    global _subscriber
    if _subscriber is None:
        _subscriber = DashboardRedisSubscriber()
    return _subscriber


def init_redis_subscriber() -> DashboardRedisSubscriber:
    """Initialize and start Redis subscriber."""
    global _subscriber
    _subscriber = DashboardRedisSubscriber()
    _subscriber.start()
    return _subscriber
```

**Step 2: Update wsgi.py to initialize subscriber**

Add to `create_production_app()` in Dockerfile after Redis init:

```python
# Initialize Redis subscriber (replaces SysMonitor, TopicTracker, etc.)
from app.redis_subscriber import init_redis_subscriber
redis_subscriber = init_redis_subscriber()
app.redis_subscriber = redis_subscriber
```

**Step 3: Update websocket.py to use Redis subscriber**

Modify `start_background_stats_pusher()` function (around line 569):

```python
def start_background_stats_pusher() -> threading.Thread:
    """Start background thread that broadcasts stats from Redis."""

    def stats_pusher_loop():
        """Background loop that broadcasts stats."""
        import time
        from app.redis_subscriber import get_redis_subscriber

        logger.info("Starting background stats broadcaster")

        subscriber = get_redis_subscriber()

        # Set callback to broadcast stats to WebSocket clients
        subscriber.set_stats_callback(lambda stats: broadcast_stats_data(stats))
        subscriber.set_status_callback(lambda status: broadcast_status(status))

        # Keep thread alive
        while True:
            time.sleep(10)

    thread = threading.Thread(target=stats_pusher_loop, daemon=True)
    thread.start()
    return thread


def broadcast_stats_data(stats: dict) -> None:
    """Broadcast stats to all connected clients."""
    socketio = get_socketio()
    if socketio:
        socketio.emit("broker_stats", stats, namespace="/", broadcast=True)


def broadcast_status(status: dict) -> None:
    """Broadcast status to all connected clients."""
    socketio = get_socketio()
    if socketio:
        socketio.emit("broker_status", status, namespace="/", broadcast=True)
```

**Step 4: Rebuild and restart dashboard**

```bash
docker compose build mqtt-dashboard
docker compose up -d mqtt-dashboard
```

**Step 5: Test end-to-end flow**

```bash
# Check MQTT bridge is publishing to Redis
docker compose exec redis redis-cli SUBSCRIBE mqtt:broker:stats

# In another terminal, check dashboard logs
docker compose logs -f mqtt-dashboard
```

Expected: Stats flowing from MQTT bridge → Redis → Dashboard

**Step 6: Commit Redis subscriber integration**

```bash
git add mqtt-dashboard/backend/app/redis_subscriber.py mqtt-dashboard/backend/app/websocket.py
git commit -m "feat: dashboard subscribes to Redis channels for broker data"
```

---

## Task 8: Remove Old MQTT Client Code from Dashboard

**Files:**
- Modify: `mqtt-dashboard/backend/gunicorn.conf.py`
- Remove references to MQTT client in dashboard

**Step 1: Remove post_fork hook from gunicorn.conf.py**

Replace entire `post_fork()` function with empty implementation:

```python
def post_fork(server, worker):
    """
    Called after a worker has been forked.

    No longer needed - MQTT connection is handled by separate mqtt-bridge service.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Worker {worker.pid}: Started (MQTT handled by bridge service)")
```

**Step 2: Update environment variables documentation**

Modify `.env.example` to document new architecture (around line 225):

```bash
# =============================================================================
# Architecture Note: MQTT Connection
# =============================================================================
# The dashboard no longer connects directly to MQTT broker.
# MQTT connection is handled by the mqtt-bridge service.
# Dashboard communicates with MQTT via Redis pub/sub.
#
# See docker-compose.yml services:
# - mqtt-bridge: Maintains MQTT connection, publishes to Redis
# - mqtt-dashboard: Web UI, subscribes to Redis channels
# =============================================================================
```

**Step 3: Rebuild dashboard with cleaned config**

```bash
docker compose build mqtt-dashboard
docker compose up -d mqtt-dashboard
```

**Step 4: Verify no MQTT connections from dashboard**

```bash
# Check mosquitto logs - should only see mqtt-bridge-service
docker compose logs mosquitto | grep "New client connected"

# Should NOT see any "mqtt-dashboard" client
```

Expected: Only `mqtt-bridge-service` connected, no `mqtt-dashboard` clients

**Step 5: Commit cleanup**

```bash
git add mqtt-dashboard/backend/gunicorn.conf.py .env.example
git commit -m "refactor: remove MQTT client code from dashboard workers"
```

---

## Task 9: Integration Testing

**Files:**
- Create: `tests/integration/test_mqtt_bridge_integration.py`

**Step 1: Write integration test**

Create `tests/integration/test_mqtt_bridge_integration.py`:

```python
"""
Integration tests for MQTT bridge service.

These tests verify end-to-end flow:
MQTT broker → Bridge Service → Redis → Dashboard
"""

import pytest
import time
import redis
import paho.mqtt.publish as mqtt_publish


@pytest.mark.integration
class TestMQTTBridgeIntegration:
    """Integration tests requiring running services."""

    def test_mqtt_message_flows_to_redis(self):
        """Test that MQTT message reaches Redis."""
        # Connect to Redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)

        # Subscribe to MQTT messages channel
        pubsub = r.pubsub()
        pubsub.subscribe('mqtt:messages')

        # Publish MQTT message
        mqtt_publish.single(
            'test/integration',
            payload='test payload',
            hostname='localhost',
            port=1883,
        )

        # Wait for message in Redis
        time.sleep(2)
        message = pubsub.get_message()

        # Verify message arrived
        assert message is not None
        # Note: First message is subscribe confirmation
        message = pubsub.get_message()
        assert 'test/integration' in str(message)

    def test_broker_stats_published_to_redis(self):
        """Test that broker stats are published to Redis."""
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)

        pubsub = r.pubsub()
        pubsub.subscribe('mqtt:broker:stats')

        # Wait for stats update (published every 5s)
        time.sleep(6)

        message = pubsub.get_message()
        assert message is not None
```

**Step 2: Run integration tests**

```bash
# Ensure all services are running
docker compose up -d

# Run integration tests
pytest tests/integration/ -v -m integration
```

Expected: PASS (messages flow through system)

**Step 3: Commit integration tests**

```bash
git add tests/integration/test_mqtt_bridge_integration.py
git commit -m "test: add integration tests for MQTT-Redis bridge"
```

---

## Task 10: Documentation and Final Verification

**Files:**
- Create: `docs/architecture/mqtt-redis-bridge.md`
- Modify: `README.md`

**Step 1: Document architecture**

Create `docs/architecture/mqtt-redis-bridge.md`:

```markdown
# MQTT-Redis Bridge Architecture

## Overview

The MQTT Dashboard uses a **separated architecture** with dedicated services:

- **mqtt-bridge**: Standalone service maintaining MQTT connection
- **mqtt-dashboard**: Web application handling HTTP/WebSocket
- **redis**: Pub/sub message broker between services

## Architecture Diagram

```
┌─────────────────┐
│ Mosquitto MQTT  │
│     Broker      │
└────────┬────────┘
         │ Single connection
         │ (mqtt-bridge-service)
         │
┌────────▼────────┐
│  MQTT Bridge    │◄──── Subscribes to $SYS/#
│    Service      │◄──── Subscribes to user topics
│  (Python)       │
└────────┬────────┘
         │ Publishes to Redis channels:
         │ - mqtt:broker:stats
         │ - mqtt:broker:status
         │ - mqtt:messages
         │
┌────────▼────────┐
│     Redis       │
│   (Pub/Sub)     │
└────────┬────────┘
         │ Subscribers:
         │
┌────────▼────────┐
│ MQTT Dashboard  │
│  (Flask/Vue.js) │◄──── WebSocket clients
│                 │
└─────────────────┘
```

## Benefits

1. **Single MQTT Connection**: Only mqtt-bridge connects to broker
2. **No Threading Conflicts**: Dashboard workers don't manage MQTT
3. **Scalability**: Multiple dashboard instances share one MQTT connection
4. **Reliability**: MQTT keepalive handled by dedicated service
5. **Clean Separation**: Each service has single responsibility

## Message Flow

### Broker Stats Update
1. Mosquitto publishes to `$SYS/broker/version`
2. MQTT bridge receives message
3. Bridge publishes to Redis `mqtt:broker:stats` channel
4. Dashboard subscribes to channel
5. Dashboard broadcasts to WebSocket clients

### Publish Command
1. User sends publish request to dashboard HTTP API
2. Dashboard publishes command to Redis `mqtt:commands` channel
3. MQTT bridge receives command
4. Bridge publishes to MQTT broker

## Redis Channels

| Channel | Publisher | Subscriber | Purpose |
|---------|-----------|------------|---------|
| `mqtt:broker:stats` | mqtt-bridge | dashboard | Broker statistics |
| `mqtt:broker:status` | mqtt-bridge | dashboard | Connection status |
| `mqtt:messages` | mqtt-bridge | dashboard | MQTT messages |
| `mqtt:commands` | dashboard | mqtt-bridge | Publish/subscribe commands |

## Configuration

Both services configured via environment variables:

**mqtt-bridge**:
- `MQTT_BROKER_HOST`
- `MQTT_BROKER_PORT`
- `REDIS_HOST`
- `REDIS_PORT`

**mqtt-dashboard**:
- `REDIS_HOST`
- `REDIS_PORT`
- No direct MQTT configuration

## Deployment

```bash
docker compose up -d redis
docker compose up -d mqtt-bridge
docker compose up -d mqtt-dashboard
```

Services start in dependency order via `depends_on`.
```

**Step 2: Update main README**

Add section to `README.md` after installation section:

```markdown
## Architecture

The MQTT Dashboard uses a separated architecture for reliability:

- **mqtt-bridge service**: Dedicated process maintaining single MQTT connection
- **mqtt-dashboard service**: Web UI and API (HTTP/WebSocket)
- **redis**: Message broker for inter-service communication

This architecture eliminates threading conflicts and ensures stable MQTT connections.

See [Architecture Documentation](docs/architecture/mqtt-redis-bridge.md) for details.
```

**Step 3: Final verification checklist**

Run complete verification:

```bash
# 1. All services healthy
docker compose ps

# Expected: All services "healthy" status

# 2. MQTT bridge connected
docker compose logs mqtt-bridge | grep "bridge started"

# 3. Only one MQTT client
docker compose logs mosquitto | grep "mqtt-bridge-service"

# 4. Dashboard serves UI
curl -s http://localhost:8082/health | jq

# 5. Stats flowing through Redis
docker compose exec redis redis-cli SUBSCRIBE mqtt:broker:stats
# Wait 5 seconds, should see stats messages

# 6. No MQTT connections from dashboard
docker compose logs mosquitto | grep "mqtt-dashboard" | grep "connected"
# Should be empty
```

**Step 4: Commit documentation**

```bash
git add docs/architecture/mqtt-redis-bridge.md README.md
git commit -m "docs: document MQTT-Redis bridge architecture"
```

**Step 5: Create final integration commit**

```bash
git add -A
git commit -m "feat: complete MQTT client separation with Redis bridge

BREAKING CHANGE: Dashboard no longer connects directly to MQTT broker.

Architecture changes:
- New mqtt-bridge service maintains single MQTT connection
- Dashboard communicates via Redis pub/sub
- Eliminates threading conflicts and connection churn
- Improves reliability and scalability

Services:
- mqtt-bridge: Standalone MQTT client, publishes to Redis
- mqtt-dashboard: Web UI, subscribes to Redis
- redis: Pub/sub message broker

Migration:
- docker compose build
- docker compose up -d

Closes: Threading conflicts, keepalive failures, unstable connections"
```

---

## Completion Checklist

Before considering this plan complete:

- [ ] Redis service running and healthy
- [ ] MQTT bridge service connected to broker
- [ ] Dashboard connects to Redis (not MQTT)
- [ ] Stats flow: MQTT → Bridge → Redis → Dashboard
- [ ] Only ONE MQTT client connected (mqtt-bridge-service)
- [ ] No "mqtt-dashboard" clients in broker logs
- [ ] Integration tests pass
- [ ] Documentation complete
- [ ] All commits have descriptive messages

## Rollback Plan

If issues occur:

1. Revert to previous architecture:
   ```bash
   git revert HEAD
   docker compose build mqtt-dashboard
   docker compose up -d
   ```

2. Or keep both running in parallel:
   - mqtt-bridge handles $SYS topics
   - Dashboard keeps direct connection for commands
   - Gradual migration

## Next Steps

After successful deployment:

1. Monitor MQTT connection stability (1 week)
2. Check Redis memory usage
3. Performance testing with load
4. Consider Redis persistence for command queue
5. Add metrics/monitoring for bridge service

---

**Plan saved to:** `docs/plans/2026-01-03-mqtt-client-separation.md`
