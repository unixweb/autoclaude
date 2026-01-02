"""
Application Configuration

This module defines configuration classes for different environments
(development, testing, production).
"""

import os
from typing import Optional


class Config:
    """Base configuration class with common settings."""

    # Flask settings
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG: bool = False
    TESTING: bool = False

    # MQTT Broker settings
    MQTT_BROKER_HOST: str = os.environ.get("MQTT_BROKER_HOST", "mosquitto")
    MQTT_BROKER_PORT: int = int(os.environ.get("MQTT_BROKER_PORT", "1883"))
    MQTT_BROKER_WS_PORT: int = int(os.environ.get("MQTT_BROKER_WS_PORT", "9001"))
    MQTT_CLIENT_ID: str = os.environ.get("MQTT_CLIENT_ID", "mqtt-dashboard")
    MQTT_USERNAME: Optional[str] = os.environ.get("MQTT_USERNAME")
    MQTT_PASSWORD: Optional[str] = os.environ.get("MQTT_PASSWORD")
    MQTT_USE_TLS: bool = os.environ.get("MQTT_USE_TLS", "false").lower() == "true"
    MQTT_KEEPALIVE: int = int(os.environ.get("MQTT_KEEPALIVE", "60"))
    MQTT_RECONNECT_DELAY: int = int(os.environ.get("MQTT_RECONNECT_DELAY", "5"))

    # CORS settings
    CORS_ORIGINS: str = os.environ.get("CORS_ORIGINS", "*")

    # SocketIO settings
    SOCKETIO_ASYNC_MODE: str = os.environ.get("SOCKETIO_ASYNC_MODE", "eventlet")


class DevelopmentConfig(Config):
    """Development environment configuration."""

    DEBUG: bool = True
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-key")


class TestingConfig(Config):
    """Testing environment configuration."""

    DEBUG: bool = True
    TESTING: bool = True
    SECRET_KEY: str = "test-secret-key"
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_CLIENT_ID: str = "mqtt-dashboard-test"


class ProductionConfig(Config):
    """Production environment configuration."""

    DEBUG: bool = False

    def __init__(self):
        """Validate production configuration."""
        if self.SECRET_KEY == "dev-secret-key-change-in-production":
            raise ValueError("SECRET_KEY must be set in production environment")


# Configuration mapping by environment name
config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(config_name: Optional[str] = None) -> Config:
    """
    Get configuration class by environment name.

    Args:
        config_name: Environment name (development, testing, production).
                    Defaults to FLASK_ENV environment variable or 'development'.

    Returns:
        Configuration class instance for the specified environment.
    """
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    config_class = config_by_name.get(config_name, DevelopmentConfig)

    # ProductionConfig needs instantiation for validation
    if config_name == "production":
        return config_class()

    return config_class()
