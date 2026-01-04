"""
MQTT Dashboard Application Entry Point

This module serves as the main entry point for running the Flask application.
It initializes the app, configures the MQTT client, WebSocket support, and starts the server.
"""

import os

from app import create_app
from app.config import get_config
from app.mqtt_client import init_mqtt_client, get_mqtt_client
from app.services.sys_monitor import init_sys_monitor
from app.services.topic_tracker import init_topic_tracker
from app.services.subscription_manager import init_subscription_manager
from app.websocket import init_socketio, start_background_stats_pusher


def main() -> None:
    """
    Main entry point for the MQTT Dashboard application.

    This function:
    1. Loads configuration based on environment
    2. Creates the Flask application
    3. Initializes the MQTT client connection
    4. Initializes the SysMonitor service
    5. Initializes the TopicTracker service
    6. Initializes the SubscriptionManager service
    7. Initializes Flask-SocketIO for real-time updates
    8. Starts background stats pusher
    9. Starts the server with SocketIO support
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

    # Initialize SysMonitor for $SYS topic subscription
    sys_monitor = init_sys_monitor(mqtt_client)
    app.logger.info("SysMonitor service initialized")

    # Initialize TopicTracker for topic discovery
    topic_tracker = init_topic_tracker(mqtt_client)
    app.logger.info("TopicTracker service initialized")

    # Initialize SubscriptionManager for per-client topic subscriptions (uses Redis)
    from app.redis_client import get_redis_client
    redis_client = get_redis_client()
    subscription_manager = init_subscription_manager(redis_client)
    app.logger.info("SubscriptionManager service initialized")

    # Store references in app context
    app.mqtt_client = mqtt_client
    app.sys_monitor = sys_monitor
    app.topic_tracker = topic_tracker
    app.subscription_manager = subscription_manager

    # Initialize Flask-SocketIO
    socketio = init_socketio(app)
    app.socketio = socketio
    app.logger.info("Flask-SocketIO initialized")

    # Start background stats pusher for real-time updates
    start_background_stats_pusher()
    app.logger.info("Background stats pusher started")

    # Get server configuration
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", "5000"))
    debug = config.DEBUG

    try:
        app.logger.info(f"Starting MQTT Dashboard on {host}:{port}")
        # Use socketio.run() instead of app.run() for WebSocket support
        socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
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
