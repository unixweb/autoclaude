"""
Messages API Routes

This module provides REST API endpoints for publishing messages to MQTT topics.
"""

from flask import Blueprint, jsonify, request

from app.mqtt_client import get_mqtt_client

messages_bp = Blueprint("messages", __name__)


@messages_bp.route("/publish", methods=["POST"])
def publish_message():
    """
    Publish a message to an MQTT topic.

    Request body:
        {
            "topic": "home/temperature",
            "payload": "23.5",
            "qos": 0,           # Optional: 0, 1, or 2 (default: 0)
            "retain": false     # Optional: true or false (default: false)
        }

    Returns:
        JSON response with success status and message details.

    Response format (success):
        {
            "success": true,
            "message": "Message published successfully",
            "details": {
                "topic": "home/temperature",
                "payload": "23.5",
                "qos": 0,
                "retain": false
            }
        }

    Response format (error):
        {
            "success": false,
            "error": "Error message",
            "code": "ERROR_CODE"
        }
    """
    mqtt_client = get_mqtt_client()

    # Check broker connection
    if not mqtt_client.is_connected:
        return jsonify({
            "success": False,
            "error": "Not connected to MQTT broker",
            "code": "BROKER_DISCONNECTED",
        }), 503

    # Get request data
    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "error": "Request body must be JSON",
            "code": "INVALID_REQUEST",
        }), 400

    # Validate required fields
    topic = data.get("topic")
    if not topic:
        return jsonify({
            "success": False,
            "error": "Topic is required",
            "code": "MISSING_TOPIC",
        }), 400

    # Validate topic name
    if not isinstance(topic, str) or not topic.strip():
        return jsonify({
            "success": False,
            "error": "Topic must be a non-empty string",
            "code": "INVALID_TOPIC",
        }), 400

    # Check for wildcard characters in topic (not allowed for publishing)
    if "+" in topic or "#" in topic:
        return jsonify({
            "success": False,
            "error": "Topic cannot contain wildcard characters (+ or #) when publishing",
            "code": "INVALID_TOPIC_WILDCARDS",
        }), 400

    # Get payload (can be empty string)
    payload = data.get("payload", "")
    if not isinstance(payload, str):
        # Convert non-string payloads to string
        payload = str(payload)

    # Get and validate QoS
    qos = data.get("qos", 0)
    if not isinstance(qos, int) or qos not in [0, 1, 2]:
        return jsonify({
            "success": False,
            "error": "QoS must be 0, 1, or 2",
            "code": "INVALID_QOS",
        }), 400

    # Get and validate retain flag
    retain = data.get("retain", False)
    if not isinstance(retain, bool):
        return jsonify({
            "success": False,
            "error": "Retain must be a boolean value",
            "code": "INVALID_RETAIN",
        }), 400

    # Publish the message
    try:
        success = mqtt_client.publish(
            topic=topic,
            payload=payload,
            qos=qos,
            retain=retain,
        )

        if success:
            return jsonify({
                "success": True,
                "message": "Message published successfully",
                "details": {
                    "topic": topic,
                    "payload": payload,
                    "qos": qos,
                    "retain": retain,
                },
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Failed to publish message",
                "code": "PUBLISH_FAILED",
            }), 500

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Error publishing message: {str(e)}",
            "code": "PUBLISH_ERROR",
        }), 500
