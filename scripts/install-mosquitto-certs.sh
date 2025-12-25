#!/bin/bash
#
# install-mosquitto-certs.sh - Install SSL/TLS certificates for Mosquitto Docker container
#
# This script installs Let's Encrypt certificates from acme.sh to the Docker-mapped
# mosquitto/certs directory for use by the Mosquitto MQTT broker container.
#
# Usage:
#   ./scripts/install-mosquitto-certs.sh
#   ./scripts/install-mosquitto-certs.sh --force  # Force re-installation
#
# Requirements:
#   - acme.sh installed and certificate already issued for mqtt.unixweb.de
#   - mosquitto/certs/ directory exists (Docker volume mount point)
#

set -euo pipefail

# Configuration
ACME_HOME="${HOME}/.acme.sh"

# Load SSL domain from acme.sh account.conf
if [[ -f "${ACME_HOME}/account.conf" ]]; then
    source "${ACME_HOME}/account.conf"
fi
DOMAIN="${SSL_DOMAIN:-mqtt.unixweb.de}"  # Fallback if not set
CERT_SOURCE_DIR="${ACME_HOME}/${DOMAIN}_ecc"
CERT_DEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/mosquitto/certs"

# Certificate files
FULLCHAIN_SRC="${CERT_SOURCE_DIR}/fullchain.cer"
PRIVKEY_SRC="${CERT_SOURCE_DIR}/${DOMAIN}.key"
CA_SRC="${CERT_SOURCE_DIR}/ca.cer"

CERT_DEST="${CERT_DEST_DIR}/${DOMAIN}.crt"
KEY_DEST="${CERT_DEST_DIR}/${DOMAIN}.key"
CA_DEST="${CERT_DEST_DIR}/ca.crt"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# Parse arguments
FORCE=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --force)
            FORCE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $(basename "$0") [--force]"
            echo ""
            echo "Install SSL/TLS certificates for Mosquitto Docker container."
            echo ""
            echo "Options:"
            echo "  --force    Force re-installation even if certificates exist"
            echo "  --help     Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

log_info "=== Mosquitto SSL/TLS Certificate Installation (Docker) ==="
log_info ""
log_step "Installing SSL/TLS certificates for Mosquitto Docker container"

# Check if acme.sh certificates exist
if [[ ! -f "${FULLCHAIN_SRC}" ]]; then
    log_error "Certificate not found: ${FULLCHAIN_SRC}"
    log_error ""
    log_error "Please issue the certificate first:"
    log_error "  ./scripts/issue-certificate.sh --staging"
    exit 1
fi

if [[ ! -f "${PRIVKEY_SRC}" ]]; then
    log_error "Private key not found: ${PRIVKEY_SRC}"
    exit 1
fi

if [[ ! -f "${CA_SRC}" ]]; then
    log_error "CA certificate not found: ${CA_SRC}"
    exit 1
fi

log_info "Source certificates found in ${CERT_SOURCE_DIR}"

# Check if destination directory exists
if [[ ! -d "${CERT_DEST_DIR}" ]]; then
    log_error "Destination directory does not exist: ${CERT_DEST_DIR}"
    log_error "Please ensure Docker Compose structure is in place."
    exit 1
fi

log_info "Destination directory: ${CERT_DEST_DIR}"
log_info ""

# Check if certificates already installed
if [[ -f "${CERT_DEST}" ]] && [[ "${FORCE}" == "false" ]]; then
    log_warn "Certificates already installed. Use --force to reinstall."
    log_info "Existing files:"
    log_info "  ${CERT_DEST}"
    log_info "  ${KEY_DEST}"
    log_info "  ${CA_DEST}"
    exit 0
fi

# Copy certificates
log_step "Copying certificate files..."

cp "${FULLCHAIN_SRC}" "${CERT_DEST}"
log_info "Copied: ${DOMAIN}.crt"

cp "${PRIVKEY_SRC}" "${KEY_DEST}"
log_info "Copied: ${DOMAIN}.key"

cp "${CA_SRC}" "${CA_DEST}"
log_info "Copied: ca.crt"

# Set permissions (readable by Docker container running as UID 1883)
chmod 644 "${CERT_DEST}"
chmod 644 "${KEY_DEST}"  # Must be readable by mosquitto user (UID 1883)
chmod 644 "${CA_DEST}"

log_info "Permissions set: cert=644, key=644, ca=644"
log_info "Note: Key file is 644 for Docker container access (user 1883:1883)"
log_info ""

# Verify installation
log_step "Verifying installation..."

CERT_SUBJECT=$(openssl x509 -in "${CERT_DEST}" -noout -subject 2>/dev/null | sed 's/subject=//' || echo "unknown")
CERT_ISSUER=$(openssl x509 -in "${CERT_DEST}" -noout -issuer 2>/dev/null | sed 's/issuer=//' || echo "unknown")
CERT_EXPIRES=$(openssl x509 -in "${CERT_DEST}" -noout -enddate 2>/dev/null | cut -d= -f2 || echo "unknown")

log_info ""
log_info "Certificate details:"
log_info "  Subject: ${CERT_SUBJECT}"
log_info "  Issuer:  ${CERT_ISSUER}"
log_info "  Expires: ${CERT_EXPIRES}"
log_info ""

# Configure acme.sh auto-renewal hook
log_step "Configuring automatic certificate renewal..."

# Get absolute path to docker-compose.yml
COMPOSE_FILE="$(cd "$(dirname "${CERT_DEST_DIR}")" && pwd)/docker-compose.yml"

if "${ACME_HOME}/acme.sh" --install-cert -d "${DOMAIN}" \
    --ecc \
    --cert-file "${CERT_DEST}" \
    --key-file "${KEY_DEST}" \
    --ca-file "${CA_DEST}" \
    --fullchain-file "${CERT_DEST}" \
    --reloadcmd "docker compose -f ${COMPOSE_FILE} restart mosquitto"; then
    log_info "Auto-renewal hook configured successfully"
    log_info "acme.sh will automatically update certificates and restart Mosquitto"
else
    log_warn "Could not configure auto-renewal hook"
    log_warn "You may need to manually restart Mosquitto after certificate renewal"
fi

log_info ""
log_info "${GREEN}✓ Certificates successfully installed!${NC}"
log_info ""
log_info "=== Next Steps ==="
log_info ""
log_info "1. Restart Mosquitto container:"
log_info "   docker-compose restart mosquitto"
log_info ""
log_info "2. Check container logs:"
log_info "   docker-compose logs mosquitto"
log_info ""
log_info "3. Test unencrypted MQTT connection (Port 1883):"
log_info "   mosquitto_sub -h localhost -p 1883 -t test/topic"
log_info ""
log_info "4. Test encrypted MQTT connection (Port 8883):"
log_info "   mosquitto_sub -h mqtt.unixweb.de -p 8883 --cafile ${CA_DEST} -t test/topic"
log_info ""
log_info "5. Test WebSocket with TLS (Port 8084):"
log_info "   # In browser console: mqtt.connect('wss://mqtt.unixweb.de:8084')"
log_info ""
log_info "=== Certificate Renewal ==="
log_info ""
log_info "Certificates will be auto-renewed by acme.sh (runs daily via cron)."
log_info "After renewal, Mosquitto will restart automatically."
log_info ""
