"""
MQTT Dashboard Application Entry Point

This module serves as the main entry point for running the Flask application.
It initializes the app, configures the MQTT client, and starts the server.
"""

import os
import sys

from app import create_app
from app.config import get_config
from app.mqtt_client import init_mqtt_client, get_mqtt_client


def main() -> None:
    """
    Main entry point for the MQTT Dashboard application.

    This function:
    1. Loads configuration based on environment
    2. Creates the Flask application
    3. Initializes the MQTT client connection
    4. Starts the Flask development server
    """
    # Get configuration
    config_name = os.environ.get("FLASK_ENV", "development")
    config = get_config(config_name)

    # Create Flask application
    app = create_app(config_name)

    # Initialize MQTT client
    mqtt_client = init_mqtt_client(config)

    if mqtt_client.is_connected:
        app.logger.info(
            f"Connected to MQTT broker at {config.MQTT_BROKER_HOST}:{config.MQTT_BROKER_PORT}"
        )
    else:
        app.logger.warning(
            f"Failed to connect to MQTT broker at {config.MQTT_BROKER_HOST}:{config.MQTT_BROKER_PORT}. "
            "Will retry in background."
        )

    # Store MQTT client reference in app context
    app.mqtt_client = mqtt_client

    # Get server configuration
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    debug = config.DEBUG

    try:
        app.logger.info(f"Starting MQTT Dashboard on {host}:{port}")
        app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        app.logger.info("Shutting down MQTT Dashboard...")
    finally:
        # Clean up MQTT connection
        mqtt_client = get_mqtt_client()
        if mqtt_client:
            mqtt_client.disconnect()
            app.logger.info("MQTT client disconnected")


if __name__ == "__main__":
    main()
