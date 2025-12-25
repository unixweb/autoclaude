#!/bin/bash
#
# complete-ssl-setup.sh - Complete SSL/TLS setup for Mosquitto MQTT broker
#
# This is a comprehensive one-command setup script that:
# 1. Verifies prerequisites (mosquitto, acme.sh)
# 2. Tests DNS API token
# 3. Issues staging certificate
# 4. Creates certificate directory
# 5. Installs certificates with correct permissions
# 6. Configures automatic renewal
#
# Usage:
#   sudo ./scripts/complete-ssl-setup.sh
#   sudo ./scripts/complete-ssl-setup.sh --production   # For production certificate
#
# Requirements:
#   - Root/sudo access
#   - Mosquitto installed (apt-get install mosquitto)
#   - acme.sh installed (~/.acme.sh/acme.sh)
#   - HETZNER_Token configured in ~/.acme.sh/account.conf
#     (from https://dns.hetzner.com/ - NOT console.hetzner.cloud)
#

set -euo pipefail

# Configuration
# Detect original user when running with sudo
ORIGINAL_USER="${SUDO_USER:-$USER}"
ACME_HOME="/home/${ORIGINAL_USER}/.acme.sh"

# Load SSL domain from acme.sh account.conf
if [[ -f "${ACME_HOME}/account.conf" ]]; then
    source "${ACME_HOME}/account.conf"
fi
DOMAIN="${SSL_DOMAIN:-mqtt.unixweb.de}"  # Fallback if not set

CERT_DIR="/etc/mosquitto/certs"
CERT_FILE="${CERT_DIR}/${DOMAIN}.crt"
KEY_FILE="${CERT_DIR}/${DOMAIN}.key"
MOSQUITTO_USER="mosquitto"
MOSQUITTO_GROUP="mosquitto"
ACME_BIN="${ACME_HOME}/acme.sh"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }
log_header() { echo -e "\n${CYAN}════════════════════════════════════════════════════════════${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}\n"; }

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        log_error "Usage: sudo $0"
        exit 1
    fi
    log_info "Running as root (original user: ${ORIGINAL_USER})"
}

# Check prerequisites
check_prerequisites() {
    log_header "Step 1: Checking Prerequisites"

    local errors=0

    # Check mosquitto
    if command -v mosquitto &>/dev/null; then
        log_info "Mosquitto is installed: $(mosquitto -h 2>&1 | head -1 || echo 'version unknown')"
    else
        log_error "Mosquitto is NOT installed"
        log_error "Install with: apt-get install mosquitto mosquitto-clients"
        errors=1
    fi

    # Check mosquitto user
    if id "${MOSQUITTO_USER}" &>/dev/null; then
        log_info "Mosquitto user exists: ${MOSQUITTO_USER}"
    else
        log_error "Mosquitto user '${MOSQUITTO_USER}' does not exist"
        log_error "This usually means Mosquitto is not properly installed"
        errors=1
    fi

    # Check acme.sh
    if [[ -f "${ACME_BIN}" && -x "${ACME_BIN}" ]]; then
        log_info "acme.sh is installed: ${ACME_BIN}"
    else
        log_error "acme.sh is NOT installed at ${ACME_BIN}"
        log_error "Install with: curl https://get.acme.sh | sh -s email=admin@example.com"
        errors=1
    fi

    # Check DNS token
    if grep -q "SAVED_HETZNER_TOKEN" "${ACME_HOME}/account.conf" 2>/dev/null; then
        log_info "Hetzner Cloud DNS token is configured"

        # Test the token
        log_info "Testing Cloud DNS API access..."
        local token
        token=$(grep "SAVED_HETZNER_TOKEN" "${ACME_HOME}/account.conf" 2>/dev/null | cut -d"'" -f2 || true)

        if [[ -n "${token}" ]]; then
            local response
            response=$(curl -s -H "Authorization: Bearer ${token}" "https://api.hetzner.cloud/v1/zones" 2>/dev/null || echo '{"error":"curl failed"}')

            if echo "${response}" | grep -q '"zones":\[\]'; then
                log_warn "DNS token is valid but has NO zones accessible"
                log_warn "This token cannot manage the ${DOMAIN} zone"
                log_error ""
                log_error "IMPORTANT: You need a token from the Hetzner Cloud Console"
                log_error "that has access to the unixweb.de DNS zone."
                log_error ""
                log_error "1. Log into: https://console.hetzner.cloud/"
                log_error "2. Navigate to: Security -> API Tokens -> Generate API Token"
                log_error "3. Make sure token has Read & Write permissions"
                log_error "4. Update token in: ${ACME_HOME}/account.conf"
                log_error "   SAVED_HETZNER_TOKEN='YOUR_NEW_TOKEN'"
                log_error ""
                errors=1
            elif echo "${response}" | grep -q "unixweb.de"; then
                log_info "DNS token has access to unixweb.de zone"
            else
                log_warn "Could not verify zone access (check token manually)"
            fi
        fi
    else
        log_error "Hetzner Cloud DNS token is NOT configured"
        log_error "Add to ${ACME_HOME}/account.conf:"
        log_error "  SAVED_HETZNER_TOKEN='your-token-from-console.hetzner.cloud'"
        errors=1
    fi

    if [[ ${errors} -ne 0 ]]; then
        log_error ""
        log_error "Prerequisites check failed. Please fix the above issues."
        exit 1
    fi

    log_info ""
    log_info "All prerequisites met!"
}

# Create certificate directory
create_cert_directory() {
    log_header "Step 2: Creating Certificate Directory"

    if [[ -d "${CERT_DIR}" ]]; then
        log_info "Certificate directory already exists: ${CERT_DIR}"
    else
        log_info "Creating certificate directory: ${CERT_DIR}"
        mkdir -p "${CERT_DIR}"
    fi

    log_info "Setting ownership to ${MOSQUITTO_USER}:${MOSQUITTO_GROUP}"
    chown "${MOSQUITTO_USER}:${MOSQUITTO_GROUP}" "${CERT_DIR}"
    chmod 755 "${CERT_DIR}"

    log_info "Directory ready: ${CERT_DIR}"
}

# Issue certificate
issue_certificate() {
    local staging_flag="$1"

    log_header "Step 3: Issuing Certificate"

    local acme_args=(
        "--issue"
        "--dns" "dns_hetznercloud"
        "-d" "${DOMAIN}"
        "--server" "letsencrypt"
    )

    if [[ "${staging_flag}" == "staging" ]]; then
        acme_args+=("--staging")
        log_warn "Using STAGING server - certificate will NOT be trusted by clients"
        log_warn "This is for testing only. Use --production for real certificate."
    else
        log_info "Using PRODUCTION server"
    fi

    log_info "Issuing certificate for: ${DOMAIN}"
    log_info "DNS API: dns_hetznercloud (Hetzner Cloud DNS)"
    log_info ""

    # Run as original user (acme.sh stores certs in user's home)
    if su - "${ORIGINAL_USER}" -c "${ACME_BIN} ${acme_args[*]}"; then
        log_info ""
        log_info "Certificate issued successfully!"
    else
        log_error "Certificate issuance failed!"
        log_error ""
        log_error "Common issues:"
        log_error "  - DNS token doesn't have access to zone (check dns.hetzner.com)"
        log_error "  - Rate limited (wait and retry)"
        log_error "  - Network issues (check connectivity)"
        log_error ""
        log_error "Check log: ${ACME_HOME}/${DOMAIN}_ecc/${DOMAIN}.log"
        exit 1
    fi
}

# Install certificate
install_certificate() {
    log_header "Step 4: Installing Certificate"

    local acme_cert_dir="${ACME_HOME}/${DOMAIN}_ecc"
    local fullchain="${acme_cert_dir}/fullchain.cer"
    local privkey="${acme_cert_dir}/${DOMAIN}.key"

    # Check source files
    if [[ ! -f "${fullchain}" ]]; then
        log_error "Certificate not found: ${fullchain}"
        log_error "Please issue the certificate first"
        exit 1
    fi

    if [[ ! -f "${privkey}" ]]; then
        log_error "Private key not found: ${privkey}"
        exit 1
    fi

    # Copy files
    log_info "Copying certificate files..."
    cp "${fullchain}" "${CERT_FILE}"
    cp "${privkey}" "${KEY_FILE}"

    # Set ownership
    log_info "Setting ownership to ${MOSQUITTO_USER}:${MOSQUITTO_GROUP}..."
    chown "${MOSQUITTO_USER}:${MOSQUITTO_GROUP}" "${CERT_FILE}" "${KEY_FILE}"

    # Set permissions
    log_info "Setting permissions..."
    chmod 644 "${CERT_FILE}"   # Certificate: world-readable
    chmod 600 "${KEY_FILE}"    # Private key: owner-only

    # Show certificate info
    log_info ""
    log_info "Certificate installed:"
    log_info "  Certificate: ${CERT_FILE}"
    log_info "  Private Key: ${KEY_FILE}"
    log_info ""
    log_info "Certificate details:"
    log_info "  Subject: $(openssl x509 -in "${CERT_FILE}" -noout -subject 2>/dev/null | sed 's/subject=//')"
    log_info "  Issuer:  $(openssl x509 -in "${CERT_FILE}" -noout -issuer 2>/dev/null | sed 's/issuer=//')"
    log_info "  Expires: $(openssl x509 -in "${CERT_FILE}" -noout -enddate 2>/dev/null | cut -d= -f2)"
}

# Configure renewal hook
configure_renewal() {
    log_header "Step 5: Configuring Automatic Renewal"

    log_info "Setting up acme.sh install-cert with reload hook..."

    # Run as original user
    if su - "${ORIGINAL_USER}" -c "${ACME_BIN} --install-cert -d ${DOMAIN} \
        --fullchain-file ${CERT_FILE} \
        --key-file ${KEY_FILE} \
        --reloadcmd 'sudo systemctl reload mosquitto'"; then
        log_info "Renewal hook configured successfully"
    else
        log_warn "Could not configure renewal hook automatically"
        log_warn "You may need to run manually:"
        log_warn "  ${ACME_BIN} --install-cert -d ${DOMAIN} \\"
        log_warn "    --fullchain-file ${CERT_FILE} \\"
        log_warn "    --key-file ${KEY_FILE} \\"
        log_warn "    --reloadcmd 'sudo systemctl reload mosquitto'"
    fi

    # Verify cron job
    log_info ""
    if su - "${ORIGINAL_USER}" -c "crontab -l 2>/dev/null" | grep -q "acme.sh"; then
        log_info "Cron job for automatic renewal is active"
    else
        log_warn "Cron job not found. Renewal may not be automatic."
    fi
}

# Verify installation
verify_installation() {
    log_header "Step 6: Verification"

    local errors=0

    # Check certificate file
    if [[ -f "${CERT_FILE}" ]]; then
        local perms owner
        perms=$(stat -c '%a' "${CERT_FILE}")
        owner=$(stat -c '%U:%G' "${CERT_FILE}")

        if [[ "${perms}" == "644" ]]; then
            log_info "Certificate permissions: OK (${perms})"
        else
            log_error "Certificate permissions: FAIL (expected 644, got ${perms})"
            errors=1
        fi

        if [[ "${owner}" == "${MOSQUITTO_USER}:${MOSQUITTO_GROUP}" ]]; then
            log_info "Certificate ownership: OK (${owner})"
        else
            log_error "Certificate ownership: FAIL (expected ${MOSQUITTO_USER}:${MOSQUITTO_GROUP}, got ${owner})"
            errors=1
        fi
    else
        log_error "Certificate file not found: ${CERT_FILE}"
        errors=1
    fi

    # Check key file
    if [[ -f "${KEY_FILE}" ]]; then
        local perms owner
        perms=$(stat -c '%a' "${KEY_FILE}")
        owner=$(stat -c '%U:%G' "${KEY_FILE}")

        if [[ "${perms}" == "600" ]]; then
            log_info "Private key permissions: OK (${perms})"
        else
            log_error "Private key permissions: FAIL (expected 600, got ${perms})"
            errors=1
        fi

        if [[ "${owner}" == "${MOSQUITTO_USER}:${MOSQUITTO_GROUP}" ]]; then
            log_info "Private key ownership: OK (${owner})"
        else
            log_error "Private key ownership: FAIL (expected ${MOSQUITTO_USER}:${MOSQUITTO_GROUP}, got ${owner})"
            errors=1
        fi
    else
        log_error "Private key file not found: ${KEY_FILE}"
        errors=1
    fi

    if [[ ${errors} -eq 0 ]]; then
        log_info ""
        log_info "All verifications passed!"
        echo "INSTALLED"
    else
        log_error ""
        log_error "Some verifications failed!"
        return 1
    fi
}

# Show next steps
show_next_steps() {
    log_header "Setup Complete"

    log_info "Certificate files are now installed at:"
    log_info "  ${CERT_FILE}"
    log_info "  ${KEY_FILE}"
    log_info ""
    log_info "Next steps:"
    log_info ""
    log_info "1. Create Mosquitto TLS configuration:"
    log_info "   sudo tee /etc/mosquitto/conf.d/ssl.conf << 'EOF'"
    log_info "   listener 8883"
    log_info "   certfile ${CERT_FILE}"
    log_info "   keyfile ${KEY_FILE}"
    log_info "   tls_version tlsv1.2"
    log_info "   EOF"
    log_info ""
    log_info "2. Reload Mosquitto:"
    log_info "   sudo systemctl reload mosquitto"
    log_info ""
    log_info "3. Test TLS connection:"
    log_info "   openssl s_client -connect ${DOMAIN}:8883 -servername ${DOMAIN}"
    log_info ""
}

# Main
main() {
    local mode="staging"  # Default to staging for safety

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --production|--prod)
                mode="production"
                shift
                ;;
            --staging|--stage)
                mode="staging"
                shift
                ;;
            --help|-h)
                echo "Usage: sudo $0 [--staging|--production]"
                echo ""
                echo "Options:"
                echo "  --staging     Issue staging certificate (default, for testing)"
                echo "  --production  Issue production certificate (rate limited)"
                echo ""
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    log_header "Complete SSL/TLS Setup for ${DOMAIN}"
    log_info "Mode: ${mode}"
    log_info "User: ${ORIGINAL_USER}"
    log_info ""

    check_root
    check_prerequisites
    create_cert_directory
    issue_certificate "${mode}"
    install_certificate
    configure_renewal
    verify_installation
    show_next_steps
}

main "$@"
