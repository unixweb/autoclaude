"""
MQTT Dashboard Flask Application

This module initializes the Flask application for the MQTT broker management dashboard.
"""

from flask import Flask
from flask_cors import CORS


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
    app.config.from_mapping(
        SECRET_KEY="dev-secret-key-change-in-production",
        MQTT_BROKER_HOST="mosquitto",
        MQTT_BROKER_PORT=1883,
    )

    # Enable CORS for frontend development
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register blueprints
    from app.routes import api_bp

    app.register_blueprint(api_bp, url_prefix="/api")

    # Health check endpoint at root
    @app.route("/health")
    def health_check():
        """Health check endpoint for Docker and monitoring."""
        return {"status": "healthy", "service": "mqtt-dashboard"}

    return app
