#!/usr/bin/env python3
"""Validate docker-compose.yml YAML syntax and structure."""

import yaml
import sys

def validate_docker_compose():
    """Validate the docker-compose.yml file."""
    try:
        with open('docker-compose.yml', 'r') as f:
            config = yaml.safe_load(f)

        # Basic structure validation
        errors = []

        # Check required top-level keys
        if 'services' not in config:
            errors.append("Missing 'services' key")

        # Validate services structure
        if 'services' in config:
            services = config['services']

            # Check mailhog service exists
            if 'mailhog' not in services:
                errors.append("Missing 'mailhog' service")
            else:
                mailhog = services['mailhog']

                # Validate mailhog configuration
                if 'image' not in mailhog:
                    errors.append("mailhog: missing 'image'")
                elif 'mailhog' not in mailhog['image']:
                    errors.append("mailhog: image should reference mailhog")

                if 'container_name' not in mailhog:
                    errors.append("mailhog: missing 'container_name'")

                if 'ports' not in mailhog:
                    errors.append("mailhog: missing 'ports'")
                else:
                    ports = mailhog['ports']
                    port_strs = [str(p) for p in ports]
                    if not any('1025' in p for p in port_strs):
                        errors.append("mailhog: missing SMTP port 1025")
                    if not any('8025' in p for p in port_strs):
                        errors.append("mailhog: missing Web UI port 8025")

                if 'networks' not in mailhog:
                    errors.append("mailhog: missing 'networks'")
                elif 'app_network' not in mailhog['networks']:
                    errors.append("mailhog: should be on 'app_network'")

                if 'healthcheck' not in mailhog:
                    errors.append("mailhog: missing 'healthcheck'")

                if 'restart' not in mailhog:
                    errors.append("mailhog: missing 'restart' policy")

        # Check networks
        if 'networks' not in config:
            errors.append("Missing 'networks' key")
        elif 'app_network' not in config['networks']:
            errors.append("Missing 'app_network' network")

        if errors:
            print("Validation FAILED:")
            for error in errors:
                print(f"  - {error}")
            return False
        else:
            print("✓ YAML syntax is valid")
            print("✓ docker-compose structure is valid")
            print("✓ mailhog service is properly configured")
            print("\nMailhog service details:")
            mailhog = config['services']['mailhog']
            print(f"  Image: {mailhog.get('image')}")
            print(f"  Container: {mailhog.get('container_name')}")
            print(f"  Ports: {mailhog.get('ports')}")
            print(f"  Networks: {mailhog.get('networks')}")
            print(f"  Restart: {mailhog.get('restart')}")
            print(f"  Has healthcheck: {'healthcheck' in mailhog}")
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
    success = validate_docker_compose()
    sys.exit(0 if success else 1)
