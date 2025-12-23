#!/usr/bin/env python3
"""Validate docker-compose.yml mosquitto service configuration."""

import yaml
import sys
import os

def validate_mosquitto_service():
    """Validate the mosquitto service in docker-compose.yml."""
    try:
        with open('docker-compose.yml', 'r') as f:
            config = yaml.safe_load(f)

        errors = []
        warnings = []

        # Check services exist
        if 'services' not in config:
            errors.append("Missing 'services' key")
            print("Validation FAILED:")
            for error in errors:
                print(f"  - {error}")
            return False

        services = config['services']

        # Check mosquitto service exists
        if 'mosquitto' not in services:
            errors.append("Missing 'mosquitto' service")
        else:
            mosquitto = services['mosquitto']

            # Validate image
            if 'image' not in mosquitto:
                errors.append("mosquitto: missing 'image'")
            elif 'eclipse-mosquitto' not in mosquitto['image']:
                errors.append("mosquitto: image should be eclipse-mosquitto")

            # Validate container_name
            if 'container_name' not in mosquitto:
                errors.append("mosquitto: missing 'container_name'")
            elif mosquitto['container_name'] != 'app_mosquitto':
                warnings.append(f"mosquitto: container_name is '{mosquitto['container_name']}', expected 'app_mosquitto'")

            # Validate restart policy
            if 'restart' not in mosquitto:
                errors.append("mosquitto: missing 'restart' policy")
            elif mosquitto['restart'] != 'unless-stopped':
                warnings.append(f"mosquitto: restart is '{mosquitto['restart']}', expected 'unless-stopped'")

            # Validate ports
            if 'ports' not in mosquitto:
                errors.append("mosquitto: missing 'ports'")
            else:
                ports = mosquitto['ports']
                port_strs = [str(p) for p in ports]
                has_mqtt = any('1883' in p for p in port_strs)
                has_websocket = any('9001' in p for p in port_strs)
                if not has_mqtt:
                    errors.append("mosquitto: missing MQTT port 1883")
                if not has_websocket:
                    errors.append("mosquitto: missing WebSocket port 9001")

            # Validate volumes
            if 'volumes' not in mosquitto:
                errors.append("mosquitto: missing 'volumes'")
            else:
                volumes = mosquitto['volumes']
                volume_strs = [str(v) for v in volumes]
                has_config = any('mosquitto/config' in v for v in volume_strs)
                has_data = any('mosquitto/data' in v for v in volume_strs)
                has_log = any('mosquitto/log' in v for v in volume_strs)
                if not has_config:
                    errors.append("mosquitto: missing config volume mount")
                if not has_data:
                    errors.append("mosquitto: missing data volume mount")
                if not has_log:
                    errors.append("mosquitto: missing log volume mount")

            # Validate networks
            if 'networks' not in mosquitto:
                errors.append("mosquitto: missing 'networks'")
            elif 'app_network' not in mosquitto['networks']:
                errors.append("mosquitto: should be on 'app_network'")

            # Validate healthcheck
            if 'healthcheck' not in mosquitto:
                errors.append("mosquitto: missing 'healthcheck'")
            else:
                healthcheck = mosquitto['healthcheck']
                if 'test' not in healthcheck:
                    errors.append("mosquitto: healthcheck missing 'test'")
                if 'interval' not in healthcheck:
                    warnings.append("mosquitto: healthcheck missing 'interval'")
                if 'timeout' not in healthcheck:
                    warnings.append("mosquitto: healthcheck missing 'timeout'")
                if 'retries' not in healthcheck:
                    warnings.append("mosquitto: healthcheck missing 'retries'")

        # Check app_network exists
        if 'networks' not in config:
            errors.append("Missing 'networks' key")
        elif 'app_network' not in config['networks']:
            errors.append("Missing 'app_network' network")

        # Check mosquitto directory structure exists
        dir_checks = [
            ('mosquitto/config', 'config directory'),
            ('mosquitto/data', 'data directory'),
            ('mosquitto/log', 'log directory'),
            ('mosquitto/config/mosquitto.conf', 'configuration file')
        ]
        for path, desc in dir_checks:
            if not os.path.exists(path):
                warnings.append(f"mosquitto: {desc} not found at '{path}'")

        # Output results
        if errors:
            print("Validation FAILED:")
            for error in errors:
                print(f"  ✗ {error}")
            if warnings:
                print("\nWarnings:")
                for warning in warnings:
                    print(f"  ⚠ {warning}")
            return False
        else:
            print("✓ YAML syntax is valid")
            print("✓ docker-compose structure is valid")
            print("✓ mosquitto service is properly configured")

            if warnings:
                print("\nWarnings:")
                for warning in warnings:
                    print(f"  ⚠ {warning}")

            print("\nMosquitto service details:")
            mosquitto = services['mosquitto']
            print(f"  Image: {mosquitto.get('image')}")
            print(f"  Container: {mosquitto.get('container_name')}")
            print(f"  Ports: {mosquitto.get('ports')}")
            print(f"  Volumes: {mosquitto.get('volumes')}")
            print(f"  Networks: {mosquitto.get('networks')}")
            print(f"  Restart: {mosquitto.get('restart')}")
            print(f"  Has healthcheck: {'healthcheck' in mosquitto}")

            # List all services in docker-compose
            print("\nAll services defined:")
            for service_name in services.keys():
                print(f"  - {service_name}")

            return True

    except yaml.YAMLError as e:
        print(f"YAML syntax error: {e}")
        return False
    except FileNotFoundError:
        print("Error: docker-compose.yml not found")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

if __name__ == '__main__':
    success = validate_mosquitto_service()
    sys.exit(0 if success else 1)
