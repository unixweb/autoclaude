"""
Topics API Routes

This module provides REST API endpoints for topic listing and exploration.
Topics are tracked by monitoring message traffic on a wildcard subscription.
"""

from flask import Blueprint, jsonify, request

from app.mqtt_client import get_mqtt_client
from app.services.topic_tracker import get_topic_tracker

topics_bp = Blueprint("topics", __name__)


@topics_bp.route("")
def get_topics():
    """
    Get list of active topics.

    Query Parameters:
        filter: Optional pattern to filter topics (supports wildcards * and ?)
        prefix: Optional prefix to filter topics (exact prefix match)
        limit: Optional limit on number of topics to return (default: no limit)
        include_inactive: Include inactive topics (default: false)

    Returns:
        JSON response with list of active topics.

    Response format:
        {
            "topics": [
                {
                    "topic": "home/temperature",
                    "message_count": 42,
                    "last_payload": "23.5",
                    "last_qos": 0,
                    "last_retained": false,
                    "first_seen": "2024-01-02T12:00:00Z",
                    "last_seen": "2024-01-02T12:05:00Z"
                },
                ...
            ],
            "total": 10,
            "filtered": 5
        }
    """
    mqtt_client = get_mqtt_client()

    if not mqtt_client.is_connected:
        return jsonify({
            "error": "Not connected to MQTT broker",
            "code": "BROKER_DISCONNECTED",
        }), 503

    topic_tracker = get_topic_tracker()

    if not topic_tracker.is_subscribed:
        return jsonify({
            "error": "Not subscribed to topic tracking",
            "code": "TOPIC_TRACKER_NOT_SUBSCRIBED",
        }), 503

    # Get query parameters
    filter_pattern = request.args.get("filter")
    prefix_filter = request.args.get("prefix")
    limit = request.args.get("limit", type=int)
    include_inactive = request.args.get("include_inactive", "false").lower() == "true"

    # Get all topics
    topics = topic_tracker.get_topics(include_inactive=include_inactive)
    total_count = len(topics)

    # Apply prefix filter
    if prefix_filter:
        topics = [t for t in topics if t.topic.startswith(prefix_filter)]

    # Apply wildcard filter (convert MQTT wildcards to simple pattern matching)
    if filter_pattern:
        import fnmatch
        # Convert MQTT wildcards to fnmatch patterns
        # + becomes ?, # becomes *
        fnmatch_pattern = filter_pattern.replace("+", "?").replace("#", "*")
        topics = [t for t in topics if fnmatch.fnmatch(t.topic, fnmatch_pattern)]

    filtered_count = len(topics)

    # Apply limit
    if limit and limit > 0:
        topics = topics[:limit]

    # Convert to dict
    topics_dict = [topic.to_dict() for topic in topics]

    return jsonify({
        "topics": topics_dict,
        "total": total_count,
        "filtered": filtered_count,
    }), 200


@topics_bp.route("/<path:topic_name>")
def get_topic(topic_name: str):
    """
    Get information about a specific topic.

    Args:
        topic_name: The MQTT topic name (path parameter)

    Returns:
        JSON response with topic details including last message.

    Response format:
        {
            "topic": "home/temperature",
            "message_count": 42,
            "last_payload": "23.5",
            "last_qos": 0,
            "last_retained": false,
            "first_seen": "2024-01-02T12:00:00Z",
            "last_seen": "2024-01-02T12:05:00Z"
        }
    """
    mqtt_client = get_mqtt_client()

    if not mqtt_client.is_connected:
        return jsonify({
            "error": "Not connected to MQTT broker",
            "code": "BROKER_DISCONNECTED",
        }), 503

    topic_tracker = get_topic_tracker()

    if not topic_tracker.is_subscribed:
        return jsonify({
            "error": "Not subscribed to topic tracking",
            "code": "TOPIC_TRACKER_NOT_SUBSCRIBED",
        }), 503

    # Get topic info
    topic_info = topic_tracker.get_topic(topic_name)

    if topic_info is None:
        return jsonify({
            "error": f"Topic '{topic_name}' not found",
            "code": "TOPIC_NOT_FOUND",
        }), 404

    return jsonify(topic_info.to_dict()), 200


@topics_bp.route("/count")
def get_topics_count():
    """
    Get the count of currently tracked topics.

    Returns:
        JSON response with topic count.

    Response format:
        {
            "count": 10
        }
    """
    mqtt_client = get_mqtt_client()

    if not mqtt_client.is_connected:
        return jsonify({
            "error": "Not connected to MQTT broker",
            "code": "BROKER_DISCONNECTED",
        }), 503

    topic_tracker = get_topic_tracker()

    if not topic_tracker.is_subscribed:
        return jsonify({
            "error": "Not subscribed to topic tracking",
            "code": "TOPIC_TRACKER_NOT_SUBSCRIBED",
        }), 503

    count = topic_tracker.get_topic_count()

    return jsonify({
        "count": count,
    }), 200


@topics_bp.route("/summary")
def get_topics_summary():
    """
    Get a summary list of active topics (lightweight response).

    Query Parameters:
        prefix: Optional prefix to filter topics (exact prefix match)
        limit: Optional limit on number of topics to return (default: 100)

    Returns:
        JSON response with summary of active topics.

    Response format:
        {
            "topics": [
                {
                    "topic": "home/temperature",
                    "message_count": 42,
                    "last_seen": "2024-01-02T12:05:00Z"
                },
                ...
            ],
            "total": 10
        }
    """
    mqtt_client = get_mqtt_client()

    if not mqtt_client.is_connected:
        return jsonify({
            "error": "Not connected to MQTT broker",
            "code": "BROKER_DISCONNECTED",
        }), 503

    topic_tracker = get_topic_tracker()

    if not topic_tracker.is_subscribed:
        return jsonify({
            "error": "Not subscribed to topic tracking",
            "code": "TOPIC_TRACKER_NOT_SUBSCRIBED",
        }), 503

    # Get query parameters
    prefix_filter = request.args.get("prefix")
    limit = request.args.get("limit", default=100, type=int)

    # Get all topics
    topics = topic_tracker.get_topics(include_inactive=False)

    # Apply prefix filter
    if prefix_filter:
        topics = [t for t in topics if t.topic.startswith(prefix_filter)]

    total_count = len(topics)

    # Apply limit
    if limit and limit > 0:
        topics = topics[:limit]

    # Convert to summary dict
    topics_summary = [topic.to_summary_dict() for topic in topics]

    return jsonify({
        "topics": topics_summary,
        "total": total_count,
    }), 200
