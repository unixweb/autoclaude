"""
MQTT Dashboard Flask Application

This module initializes the Flask application for the MQTT broker management dashboard.
"""

from flask import Flask
from flask_cors import CORS

from app.config import get_config


def create_app(config_name: str = "development") -> Flask:
    """
    Application factory for creating Flask app instances.

    Args:
        config_name: Configuration environment name (development, production, testing)

    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)

    # Load configuration based on environment
    config = get_config(config_name)
    app.config.from_object(config)

    # Enable CORS for frontend development
    CORS(app, resources={r"/api/*": {"origins": config.CORS_ORIGINS}})

    # Register blueprints
    from app.routes import api_bp

    app.register_blueprint(api_bp, url_prefix="/api")

    # Health check endpoint at root
    @app.route("/health")
    def health_check():
        """Health check endpoint for Docker and monitoring."""
        from app.mqtt_client import get_mqtt_client
        from app.websocket import get_socketio, get_connected_client_count

        mqtt_client = get_mqtt_client()
        mqtt_status = "connected" if mqtt_client and mqtt_client.is_connected else "disconnected"

        socketio = get_socketio()
        websocket_status = "initialized" if socketio else "not_initialized"

        return {
            "status": "healthy",
            "service": "mqtt-dashboard",
            "mqtt_broker": {
                "host": config.MQTT_BROKER_HOST,
                "port": config.MQTT_BROKER_PORT,
                "status": mqtt_status,
            },
            "websocket": {
                "status": websocket_status,
                "connected_clients": get_connected_client_count() if socketio else 0,
            },
        }

    return app
