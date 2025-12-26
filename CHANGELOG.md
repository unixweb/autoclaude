## 2.7.5 - Automated Certificate Management

### New Features

- Automated SSL/TLS certificate management for MQTT broker using Let's Encrypt and acme.sh
- DNS-01 challenge validation via Hetzner Cloud DNS API
- Automatic certificate renewal every 90 days

### Improvements

- Enhanced security infrastructure for continuous secure MQTT connectivity
- Streamlined certificate lifecycle management for mqtt.unixweb.de domain

---

## What's Changed

- feature: Implement automated SSL/TLS certificate management for Mosquitto MQTT broker by @auto-claude in auto-claude-spec-009

## Thanks to all contributors

@auto-claude

## 2.7.4 - MQTT Service Integration

### New Features

- Added Eclipse Mosquitto MQTT broker service to Docker Compose configuration, enabling real-time message publishing and subscription capabilities for connected applications

### Improvements

- Integrated Mosquitto with existing directory structure for persistent configuration, data storage, and logging
- Enhanced Docker Compose setup to support IoT and real-time messaging workflows

---

## What's Changed

- feat: Add Eclipse Mosquitto MQTT broker service by @auto-claude in 006-add-mosquitto-mqtt-broker-service

## Thanks to all contributors

@auto-claude

## [2.1.0] - 2025-12-23

### Added
- Docker Compose configuration with example services for local development
- Mailhog email testing service for development environments
- SMTP environment variables to web service configuration

### Changed
- Improved Docker Compose YAML validation and syntax checking
- Updated .gitignore configuration

### Fixed
- Removed duplicate Mailhog service definition from configuration

## [2.1.0] - 2025-12-23

### Added
- Docker Compose configuration with example services for local development
- Mailhog email testing service for development environments
- SMTP environment variables to web service configuration

### Changed
- Improved Docker Compose YAML validation and syntax checking
- Updated .gitignore configuration

### Fixed
- Removed duplicate Mailhog service definition from configuration