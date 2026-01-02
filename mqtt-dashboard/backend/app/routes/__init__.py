"""
API Routes Package

This module defines the Flask blueprints and route registrations
for the MQTT Dashboard API.
"""

from flask import Blueprint

# Create main API blueprint
api_bp = Blueprint("api", __name__)


@api_bp.route("/")
def api_root():
    """API root endpoint returning API information."""
    return {
        "name": "MQTT Dashboard API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "broker": "/api/broker",
            "clients": "/api/clients",
            "topics": "/api/topics",
            "messages": "/api/messages",
        },
    }
