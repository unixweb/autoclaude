#!/bin/bash
#
# fix-cert-permissions.sh - Set correct permissions on Mosquitto certificate files
#
# This script ensures the SSL/TLS certificate files have the correct
# ownership and permissions for the Mosquitto MQTT broker.
#
# Usage: sudo ./scripts/fix-cert-permissions.sh
#
# Permissions set:
#   - Certificate (.crt): 644 (world-readable, needed for clients)
#   - Private key (.key): 600 (owner-only read, security requirement)
#   - Both files: owned by mosquitto:mosquitto
#

set -euo pipefail

# Configuration
DOMAIN="mqtt.unixweb.de"
CERT_DIR="/etc/mosquitto/certs"
CERT_FILE="${CERT_DIR}/${DOMAIN}.crt"
KEY_FILE="${CERT_DIR}/${DOMAIN}.key"
MOSQUITTO_USER="mosquitto"
MOSQUITTO_GROUP="mosquitto"

# Required permissions
CERT_PERMISSIONS="644"
KEY_PERMISSIONS="600"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        log_error "Usage: sudo $0"
        exit 1
    fi
}

# Check if mosquitto user exists
check_mosquitto_user() {
    if ! id "${MOSQUITTO_USER}" &>/dev/null; then
        log_error "Mosquitto user '${MOSQUITTO_USER}' does not exist"
        log_error "Please install Mosquitto first: apt-get install mosquitto"
        exit 1
    fi
}

# Check if certificate files exist
check_certificate_files() {
    local missing=0

    if [[ ! -f "${CERT_FILE}" ]]; then
        log_error "Certificate file not found: ${CERT_FILE}"
        missing=1
    fi

    if [[ ! -f "${KEY_FILE}" ]]; then
        log_error "Private key file not found: ${KEY_FILE}"
        missing=1
    fi

    if [[ ${missing} -eq 1 ]]; then
        log_error ""
        log_error "Certificate files do not exist."
        log_error "Please install certificates first:"
        log_error "  sudo ./scripts/install-certificate.sh"
        log_error "  or"
        log_error "  sudo ./scripts/complete-ssl-setup.sh"
        exit 1
    fi
}

# Set ownership on certificate files
set_ownership() {
    log_step "Setting ownership to ${MOSQUITTO_USER}:${MOSQUITTO_GROUP}..."

    chown "${MOSQUITTO_USER}:${MOSQUITTO_GROUP}" "${CERT_FILE}"
    log_info "Set ownership on: ${CERT_FILE}"

    chown "${MOSQUITTO_USER}:${MOSQUITTO_GROUP}" "${KEY_FILE}"
    log_info "Set ownership on: ${KEY_FILE}"
}

# Set permissions on certificate files
set_permissions() {
    log_step "Setting permissions..."

    # Certificate: 644 (world-readable for client verification)
    chmod "${CERT_PERMISSIONS}" "${CERT_FILE}"
    log_info "Set ${CERT_FILE} to ${CERT_PERMISSIONS} (world-readable)"

    # Private key: 600 (owner-only, security critical)
    chmod "${KEY_PERMISSIONS}" "${KEY_FILE}"
    log_info "Set ${KEY_FILE} to ${KEY_PERMISSIONS} (owner-only)"
}

# Verify permissions are correct
verify_permissions() {
    log_step "Verifying permissions..."

    local errors=0

    # Check certificate file
    local cert_owner cert_perms
    cert_owner=$(stat -c '%U:%G' "${CERT_FILE}")
    cert_perms=$(stat -c '%a' "${CERT_FILE}")

    if [[ "${cert_owner}" == "${MOSQUITTO_USER}:${MOSQUITTO_GROUP}" ]]; then
        log_info "Certificate ownership: OK (${cert_owner})"
    else
        log_error "Certificate ownership: FAIL (expected ${MOSQUITTO_USER}:${MOSQUITTO_GROUP}, got ${cert_owner})"
        errors=1
    fi

    if [[ "${cert_perms}" == "${CERT_PERMISSIONS}" ]]; then
        log_info "Certificate permissions: OK (${cert_perms})"
    else
        log_error "Certificate permissions: FAIL (expected ${CERT_PERMISSIONS}, got ${cert_perms})"
        errors=1
    fi

    # Check private key file
    local key_owner key_perms
    key_owner=$(stat -c '%U:%G' "${KEY_FILE}")
    key_perms=$(stat -c '%a' "${KEY_FILE}")

    if [[ "${key_owner}" == "${MOSQUITTO_USER}:${MOSQUITTO_GROUP}" ]]; then
        log_info "Private key ownership: OK (${key_owner})"
    else
        log_error "Private key ownership: FAIL (expected ${MOSQUITTO_USER}:${MOSQUITTO_GROUP}, got ${key_owner})"
        errors=1
    fi

    if [[ "${key_perms}" == "${KEY_PERMISSIONS}" ]]; then
        log_info "Private key permissions: OK (${key_perms})"
    else
        log_error "Private key permissions: FAIL (expected ${KEY_PERMISSIONS}, got ${key_perms})"
        errors=1
    fi

    if [[ ${errors} -eq 0 ]]; then
        log_info ""
        log_info "All permission checks passed!"
        echo "OK"
        return 0
    else
        log_error ""
        log_error "Permission verification failed!"
        return 1
    fi
}

# Show file status
show_file_status() {
    log_info ""
    log_info "File status:"
    ls -la "${CERT_DIR}/" 2>/dev/null || true
}

# Main execution
main() {
    log_info "=== Certificate Permission Fix for ${DOMAIN} ==="
    log_info ""

    check_root
    check_mosquitto_user
    check_certificate_files
    log_info ""

    set_ownership
    set_permissions
    log_info ""

    if verify_permissions; then
        show_file_status
        log_info ""
        log_info "=== Permissions Fixed Successfully ==="
        exit 0
    else
        log_error "=== Permission Fix Failed ==="
        exit 1
    fi
}

main "$@"
