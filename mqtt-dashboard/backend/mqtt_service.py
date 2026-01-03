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
