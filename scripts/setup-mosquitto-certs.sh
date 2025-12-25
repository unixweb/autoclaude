#!/bin/bash
#
# setup-mosquitto-certs.sh - Create Mosquitto certificate directory with correct permissions
#
# This script creates the /etc/mosquitto/certs/ directory with proper ownership
# and permissions for storing SSL/TLS certificates.
#
# Usage: sudo ./scripts/setup-mosquitto-certs.sh
#
# Requirements:
#   - Root/sudo privileges
#   - Mosquitto service installed (mosquitto user/group must exist)
#

set -euo pipefail

# Configuration
CERTS_DIR="/etc/mosquitto/certs"
MOSQUITTO_USER="mosquitto"
MOSQUITTO_GROUP="mosquitto"
DIR_PERMISSIONS="755"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Check if mosquitto user exists
check_mosquitto_user() {
    if ! id "${MOSQUITTO_USER}" &>/dev/null; then
        log_error "Mosquitto user '${MOSQUITTO_USER}' does not exist."
        log_error "Please install Mosquitto first: apt-get install mosquitto"
        exit 1
    fi
    log_info "Mosquitto user '${MOSQUITTO_USER}' found"
}

# Check if /etc/mosquitto exists
check_mosquitto_config_dir() {
    if [[ ! -d "/etc/mosquitto" ]]; then
        log_error "Mosquitto configuration directory /etc/mosquitto does not exist."
        log_error "Please install Mosquitto first: apt-get install mosquitto"
        exit 1
    fi
    log_info "Mosquitto configuration directory exists"
}

# Create certificate directory
create_certs_dir() {
    if [[ -d "${CERTS_DIR}" ]]; then
        log_warn "Directory ${CERTS_DIR} already exists"

        # Verify ownership and permissions
        local current_owner
        current_owner=$(stat -c '%U:%G' "${CERTS_DIR}")
        local current_perms
        current_perms=$(stat -c '%a' "${CERTS_DIR}")

        log_info "Current ownership: ${current_owner}"
        log_info "Current permissions: ${current_perms}"

        if [[ "${current_owner}" != "${MOSQUITTO_USER}:${MOSQUITTO_GROUP}" ]]; then
            log_warn "Ownership mismatch. Fixing..."
            chown "${MOSQUITTO_USER}:${MOSQUITTO_GROUP}" "${CERTS_DIR}"
        fi

        if [[ "${current_perms}" != "${DIR_PERMISSIONS}" ]]; then
            log_warn "Permissions mismatch. Fixing..."
            chmod "${DIR_PERMISSIONS}" "${CERTS_DIR}"
        fi
    else
        log_info "Creating certificate directory: ${CERTS_DIR}"
        mkdir -p "${CERTS_DIR}"

        log_info "Setting ownership to ${MOSQUITTO_USER}:${MOSQUITTO_GROUP}"
        chown "${MOSQUITTO_USER}:${MOSQUITTO_GROUP}" "${CERTS_DIR}"

        log_info "Setting permissions to ${DIR_PERMISSIONS}"
        chmod "${DIR_PERMISSIONS}" "${CERTS_DIR}"
    fi
}

# Verify the setup
verify_setup() {
    local result_owner
    result_owner=$(stat -c '%U:%G' "${CERTS_DIR}")
    local result_perms
    result_perms=$(stat -c '%a' "${CERTS_DIR}")

    if [[ "${result_owner}" == "${MOSQUITTO_USER}:${MOSQUITTO_GROUP}" ]] && \
       [[ "${result_perms}" == "${DIR_PERMISSIONS}" ]]; then
        log_info "Verification passed!"
        log_info "  Directory: ${CERTS_DIR}"
        log_info "  Owner: ${result_owner}"
        log_info "  Permissions: ${result_perms}"
        return 0
    else
        log_error "Verification failed!"
        log_error "  Expected owner: ${MOSQUITTO_USER}:${MOSQUITTO_GROUP}, got: ${result_owner}"
        log_error "  Expected perms: ${DIR_PERMISSIONS}, got: ${result_perms}"
        return 1
    fi
}

# Main execution
main() {
    log_info "=== Mosquitto Certificate Directory Setup ==="
    log_info ""

    check_root
    check_mosquitto_user
    check_mosquitto_config_dir

    log_info ""
    create_certs_dir

    log_info ""
    verify_setup

    log_info ""
    log_info "=== Setup Complete ==="
    log_info ""
    log_info "Certificate directory is ready for SSL/TLS certificates:"
    log_info "  - Certificate: ${CERTS_DIR}/mqtt.unixweb.de.crt"
    log_info "  - Private key: ${CERTS_DIR}/mqtt.unixweb.de.key"
    log_info ""
    log_info "Next steps:"
    log_info "  1. Issue certificate with acme.sh"
    log_info "  2. Install certificate to this directory"
    log_info "  3. Configure Mosquitto TLS listener"
    log_info ""
}

main "$@"
