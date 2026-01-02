"""
API Routes Package

This module defines the Flask blueprints and route registrations
for the MQTT Dashboard API.
"""

from flask import Blueprint

# Create main API blueprint
api_bp = Blueprint("api", __name__)

# Import and register child blueprints
from app.routes.broker import broker_bp
from app.routes.clients import clients_bp

api_bp.register_blueprint(broker_bp, url_prefix="/broker")
api_bp.register_blueprint(clients_bp, url_prefix="/clients")


@api_bp.route("/")
def api_root():
    """API root endpoint returning API information."""
    return {
        "name": "MQTT Dashboard API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "broker": "/api/broker",
            "broker_status": "/api/broker/status",
            "broker_stats": "/api/broker/stats",
            "broker_stats_summary": "/api/broker/stats/summary",
            "broker_version": "/api/broker/version",
            "clients": "/api/clients",
            "clients_count": "/api/clients/count",
            "clients_active": "/api/clients/active",
            "clients_stats": "/api/clients/stats",
            "topics": "/api/topics",
            "messages": "/api/messages",
        },
    }
