#!/bin/bash
#
# install-certificate.sh - Install acme.sh certificate to Mosquitto certificate directory
#
# This script copies the issued certificate from acme.sh to /etc/mosquitto/certs/
# with correct ownership and permissions for Mosquitto TLS.
#
# Usage: sudo ./scripts/install-certificate.sh
#
# Requirements:
#   - Root/sudo privileges
#   - Certificate issued via acme.sh for mqtt.unixweb.de
#   - Mosquitto service installed (mosquitto user/group must exist)
#   - Certificate directory exists (/etc/mosquitto/certs/)
#

set -euo pipefail

# Configuration
ACME_HOME="${ACME_HOME:-/home/${SUDO_USER:-$USER}/.acme.sh}"

# Load SSL domain from acme.sh account.conf
if [[ -f "${ACME_HOME}/account.conf" ]]; then
    source "${ACME_HOME}/account.conf"
fi
DOMAIN="${SSL_DOMAIN:-mqtt.unixweb.de}"  # Fallback if not set
ACME_BIN="${ACME_HOME}/acme.sh"

# Source certificate locations (acme.sh default paths)
# Note: acme.sh uses _ecc suffix for ECC certificates
ACME_CERT_DIR="${ACME_HOME}/${DOMAIN}_ecc"
ACME_FULLCHAIN="${ACME_CERT_DIR}/fullchain.cer"
ACME_KEY="${ACME_CERT_DIR}/${DOMAIN}.key"
ACME_CERT="${ACME_CERT_DIR}/${DOMAIN}.cer"

# Destination paths
CERT_DIR="/etc/mosquitto/certs"
DEST_CERT="${CERT_DIR}/${DOMAIN}.crt"
DEST_KEY="${CERT_DIR}/${DOMAIN}.key"

# Mosquitto settings
MOSQUITTO_USER="mosquitto"
MOSQUITTO_GROUP="mosquitto"
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

# Check if certificate directory exists
check_cert_dir() {
    if [[ ! -d "${CERT_DIR}" ]]; then
        log_error "Certificate directory does not exist: ${CERT_DIR}"
        log_error "Run: sudo ./scripts/setup-mosquitto-certs.sh first"
        exit 1
    fi
    log_info "Certificate directory exists: ${CERT_DIR}"
}

# Check if acme.sh certificates exist
check_acme_certificates() {
    log_step "Checking for acme.sh certificates..."
    log_info "Looking in: ${ACME_CERT_DIR}"

    local missing=0

    # Check for fullchain (preferred) or individual cert
    if [[ -f "${ACME_FULLCHAIN}" ]]; then
        log_info "Found fullchain certificate: ${ACME_FULLCHAIN}"
    elif [[ -f "${ACME_CERT}" ]]; then
        log_warn "Fullchain not found, using individual certificate: ${ACME_CERT}"
        log_warn "Note: This may cause chain validation issues for clients"
        ACME_FULLCHAIN="${ACME_CERT}"
    else
        log_error "No certificate found!"
        log_error "Expected: ${ACME_FULLCHAIN}"
        log_error "      or: ${ACME_CERT}"
        missing=1
    fi

    # Check for private key
    if [[ -f "${ACME_KEY}" ]]; then
        log_info "Found private key: ${ACME_KEY}"
    else
        log_error "Private key not found: ${ACME_KEY}"
        missing=1
    fi

    if [[ ${missing} -eq 1 ]]; then
        log_error ""
        log_error "Certificate files not found. Please issue a certificate first:"
        log_error "  ./scripts/issue-certificate.sh --staging"
        log_error ""
        log_error "Or for production:"
        log_error "  ./scripts/issue-certificate.sh --production"
        exit 1
    fi

    # Display certificate info
    log_info ""
    log_info "Certificate details:"
    log_info "  Subject: $(openssl x509 -in "${ACME_FULLCHAIN}" -noout -subject 2>/dev/null | sed 's/subject=//' || echo 'unknown')"
    log_info "  Issuer: $(openssl x509 -in "${ACME_FULLCHAIN}" -noout -issuer 2>/dev/null | sed 's/issuer=//' || echo 'unknown')"
    log_info "  Expires: $(openssl x509 -in "${ACME_FULLCHAIN}" -noout -enddate 2>/dev/null | cut -d= -f2 || echo 'unknown')"
}

# Install certificate files
install_certificates() {
    log_step "Installing certificates to ${CERT_DIR}/"

    # Copy fullchain certificate
    log_info "Copying certificate..."
    cp "${ACME_FULLCHAIN}" "${DEST_CERT}"
    log_info "  ${ACME_FULLCHAIN} -> ${DEST_CERT}"

    # Copy private key
    log_info "Copying private key..."
    cp "${ACME_KEY}" "${DEST_KEY}"
    log_info "  ${ACME_KEY} -> ${DEST_KEY}"

    # Set ownership
    log_info "Setting ownership to ${MOSQUITTO_USER}:${MOSQUITTO_GROUP}..."
    chown "${MOSQUITTO_USER}:${MOSQUITTO_GROUP}" "${DEST_CERT}" "${DEST_KEY}"

    # Set permissions
    log_info "Setting permissions..."
    chmod "${CERT_PERMISSIONS}" "${DEST_CERT}"
    chmod "${KEY_PERMISSIONS}" "${DEST_KEY}"
    log_info "  ${DEST_CERT}: ${CERT_PERMISSIONS} (world-readable)"
    log_info "  ${DEST_KEY}: ${KEY_PERMISSIONS} (owner-only)"
}

# Configure acme.sh install-cert for automatic renewal
configure_renewal_hook() {
    log_step "Configuring automatic renewal hook..."

    # Run as the original user (not root)
    local original_user="${SUDO_USER:-$USER}"

    if [[ -f "${ACME_BIN}" ]]; then
        log_info "Running acme.sh --install-cert to configure renewal hook..."

        # Use su to run as original user, but keep sudo for the reloadcmd
        su - "${original_user}" -c "${ACME_BIN} --install-cert -d ${DOMAIN} \
            --fullchain-file ${DEST_CERT} \
            --key-file ${DEST_KEY} \
            --reloadcmd 'sudo systemctl reload mosquitto'" 2>/dev/null || {
            log_warn "Could not configure automatic renewal hook via acme.sh"
            log_warn "You may need to manually run:"
            log_warn "  ${ACME_BIN} --install-cert -d ${DOMAIN} \\"
            log_warn "    --fullchain-file ${DEST_CERT} \\"
            log_warn "    --key-file ${DEST_KEY} \\"
            log_warn "    --reloadcmd 'sudo systemctl reload mosquitto'"
        }
    else
        log_warn "acme.sh not found at ${ACME_BIN}"
        log_warn "Automatic renewal hook not configured"
    fi
}

# Verify installation
verify_installation() {
    log_step "Verifying installation..."

    local errors=0

    # Check certificate file
    if [[ -f "${DEST_CERT}" ]]; then
        local cert_owner cert_perms
        cert_owner=$(stat -c '%U:%G' "${DEST_CERT}")
        cert_perms=$(stat -c '%a' "${DEST_CERT}")

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
    else
        log_error "Certificate file not found: ${DEST_CERT}"
        errors=1
    fi

    # Check key file
    if [[ -f "${DEST_KEY}" ]]; then
        local key_owner key_perms
        key_owner=$(stat -c '%U:%G' "${DEST_KEY}")
        key_perms=$(stat -c '%a' "${DEST_KEY}")

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
    else
        log_error "Private key file not found: ${DEST_KEY}"
        errors=1
    fi

    return ${errors}
}

# Main execution
main() {
    log_info "=== SSL/TLS Certificate Installation for ${DOMAIN} ==="
    log_info ""

    check_root
    check_mosquitto_user
    check_cert_dir
    log_info ""

    check_acme_certificates
    log_info ""

    install_certificates
    log_info ""

    # Try to configure renewal hook (optional, may fail)
    configure_renewal_hook 2>/dev/null || true
    log_info ""

    if verify_installation; then
        log_info ""
        log_info "=== Installation Complete ==="
        log_info ""
        log_info "Certificate files installed:"
        log_info "  Certificate: ${DEST_CERT}"
        log_info "  Private Key: ${DEST_KEY}"
        log_info ""
        log_info "Next steps:"
        log_info "  1. Create Mosquitto TLS configuration:"
        log_info "     sudo nano /etc/mosquitto/conf.d/ssl.conf"
        log_info ""
        log_info "  2. Reload Mosquitto:"
        log_info "     sudo systemctl reload mosquitto"
        log_info ""
        log_info "  3. Test TLS connection:"
        log_info "     openssl s_client -connect ${DOMAIN}:8883 -servername ${DOMAIN}"
        log_info ""
        exit 0
    else
        log_error ""
        log_error "=== Installation Failed ==="
        exit 1
    fi
}

main "$@"
