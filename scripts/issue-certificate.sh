#!/bin/bash
#
# issue-certificate.sh - Issue SSL/TLS certificate for mqtt.unixweb.de using acme.sh
#
# This script issues a Let's Encrypt certificate for mqtt.unixweb.de using
# DNS-01 challenge validation via Hetzner Cloud DNS API. It supports both
# staging (for testing) and production certificate issuance.
#
# Usage:
#   ./scripts/issue-certificate.sh              # Issue production certificate
#   ./scripts/issue-certificate.sh --staging    # Issue staging certificate (testing)
#   ./scripts/issue-certificate.sh --install    # Install certificate to Mosquitto
#   ./scripts/issue-certificate.sh --help       # Show help
#
# Requirements:
#   - acme.sh installed (~/.acme.sh/acme.sh)
#   - HETZNER_TOKEN configured in ~/.acme.sh/account.conf
#   - For --install: sudo access for certificate deployment
#

set -euo pipefail

# Configuration
DOMAIN="mqtt.unixweb.de"
ACME_HOME="${HOME}/.acme.sh"
ACME_BIN="${ACME_HOME}/acme.sh"
CERT_DIR="/etc/mosquitto/certs"
CERT_FILE="${CERT_DIR}/${DOMAIN}.crt"
KEY_FILE="${CERT_DIR}/${DOMAIN}.key"
DNS_API="dns_hetzner"
CA_SERVER="letsencrypt"

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

show_help() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Issue SSL/TLS certificate for ${DOMAIN} using Let's Encrypt and Hetzner Cloud DNS.

Options:
    --staging       Use Let's Encrypt staging server (for testing, avoids rate limits)
    --production    Use Let's Encrypt production server (default)
    --install       Install certificate to Mosquitto after issuance
    --force         Force re-issuance even if certificate exists
    --help          Show this help message

Examples:
    $(basename "$0") --staging           # Test with staging certificate
    $(basename "$0") --staging --install # Test with staging and install to Mosquitto
    $(basename "$0") --production        # Issue production certificate
    $(basename "$0") --force             # Force re-issue production certificate

Certificate Paths:
    Certificate: ${CERT_FILE}
    Private Key: ${KEY_FILE}

Notes:
    - Staging certificates are NOT trusted by browsers/clients (for testing only)
    - Production has rate limits: 50 certificates/week per domain
    - Certificate valid for 90 days, auto-renewed at 60 days by acme.sh cron
EOF
}

# Check if acme.sh is installed
check_acme_installed() {
    if [[ ! -f "${ACME_BIN}" ]]; then
        log_error "acme.sh is not installed at ${ACME_HOME}"
        log_error "Run: ./scripts/install-acme.sh first"
        exit 1
    fi
    if [[ ! -x "${ACME_BIN}" ]]; then
        log_error "acme.sh is not executable: ${ACME_BIN}"
        exit 1
    fi
    log_info "acme.sh found at: ${ACME_BIN}"
}

# Check if Hetzner DNS token is configured
check_dns_credentials() {
    local account_conf="${ACME_HOME}/account.conf"

    if [[ ! -f "${account_conf}" ]]; then
        log_error "acme.sh account.conf not found: ${account_conf}"
        exit 1
    fi

    # Check for SAVED_HETZNER_Token (used by dns_hetzner - DNS Console API)
    if grep -q "SAVED_HETZNER_Token" "${account_conf}"; then
        log_info "Hetzner DNS Console API token configured (dns_hetzner)"
        return 0
    fi

    # Check for SAVED_HETZNER_TOKEN (alternative uppercase format)
    if grep -q "SAVED_HETZNER_TOKEN" "${account_conf}"; then
        log_info "Hetzner DNS API token configured (uppercase format)"
        return 0
    fi

    # Check for environment variable (HETZNER_Token for dns_hetzner)
    if [[ -n "${HETZNER_Token:-}" ]]; then
        log_info "HETZNER_Token found in environment (will be saved on first use)"
        return 0
    fi

    # Also check uppercase version
    if [[ -n "${HETZNER_TOKEN:-}" ]]; then
        log_info "HETZNER_TOKEN found in environment (will be saved on first use)"
        return 0
    fi

    log_error "Hetzner DNS token not configured"
    log_error ""
    log_error "To configure, either:"
    log_error "  1. Export HETZNER_Token environment variable before running this script"
    log_error "  2. Add SAVED_HETZNER_Token='your-token' to ${account_conf}"
    log_error ""
    log_error "Get token from: https://dns.hetzner.com/ -> Settings -> API Tokens"
    exit 1
}

# Check if certificate already exists
check_existing_certificate() {
    local staging_flag="$1"

    # Check if domain is already registered in acme.sh
    if "${ACME_BIN}" --list 2>/dev/null | grep -q "${DOMAIN}"; then
        local cert_info
        cert_info=$("${ACME_BIN}" --info -d "${DOMAIN}" 2>/dev/null || true)

        if [[ -n "${cert_info}" ]]; then
            log_info "Certificate already exists for ${DOMAIN}"

            # Check if it's a staging or production cert
            if echo "${cert_info}" | grep -q "Staging"; then
                log_info "Current certificate: STAGING"
            else
                log_info "Current certificate: PRODUCTION"
            fi

            # Show expiry
            local cert_path="${ACME_HOME}/${DOMAIN}_ecc/${DOMAIN}.cer"
            if [[ -f "${cert_path}" ]]; then
                local expiry
                expiry=$(openssl x509 -in "${cert_path}" -noout -enddate 2>/dev/null | cut -d= -f2 || echo "unknown")
                log_info "Expires: ${expiry}"
            fi

            return 0
        fi
    fi
    return 1
}

# Issue certificate
issue_certificate() {
    local staging_flag="$1"
    local force_flag="$2"

    log_step "Issuing certificate for ${DOMAIN}"
    log_info "DNS API: ${DNS_API}"
    log_info "CA Server: ${CA_SERVER}${staging_flag:+ (staging)}"

    local cmd_args=(
        "--issue"
        "--dns" "${DNS_API}"
        "-d" "${DOMAIN}"
        "--server" "${CA_SERVER}"
    )

    if [[ -n "${staging_flag}" ]]; then
        cmd_args+=("--staging")
        log_warn "Using STAGING server - certificate will NOT be trusted by clients"
    fi

    if [[ -n "${force_flag}" ]]; then
        cmd_args+=("--force")
        log_info "Force flag set - will re-issue even if certificate exists"
    fi

    log_info ""
    log_info "Running: ${ACME_BIN} ${cmd_args[*]}"
    log_info ""

    if "${ACME_BIN}" "${cmd_args[@]}"; then
        log_info ""
        log_info "Certificate issued successfully!"

        # Show certificate info
        local cert_path="${ACME_HOME}/${DOMAIN}_ecc/${DOMAIN}.cer"
        if [[ -f "${cert_path}" ]]; then
            log_info ""
            log_info "Certificate details:"
            log_info "  Subject: $(openssl x509 -in "${cert_path}" -noout -subject 2>/dev/null | sed 's/subject=//' || echo 'unknown')"
            log_info "  Issuer: $(openssl x509 -in "${cert_path}" -noout -issuer 2>/dev/null | sed 's/issuer=//' || echo 'unknown')"
            log_info "  Expires: $(openssl x509 -in "${cert_path}" -noout -enddate 2>/dev/null | cut -d= -f2 || echo 'unknown')"
        fi

        return 0
    else
        log_error "Certificate issuance failed!"
        log_error ""
        log_error "Check the log for details:"
        log_error "  ${ACME_HOME}/${DOMAIN}_ecc/${DOMAIN}.log"
        return 1
    fi
}

# Install certificate to Mosquitto
install_certificate() {
    log_step "Installing certificate to Mosquitto"

    # Check if certificate directory exists
    if [[ ! -d "${CERT_DIR}" ]]; then
        log_error "Certificate directory does not exist: ${CERT_DIR}"
        log_error "Run: sudo ./scripts/setup-mosquitto-certs.sh first"
        exit 1
    fi

    log_info "Installing to: ${CERT_DIR}/"
    log_info "  Certificate: ${CERT_FILE}"
    log_info "  Private Key: ${KEY_FILE}"
    log_info "  Reload Command: systemctl reload mosquitto"
    log_info ""

    # Note: --install-cert needs to run with sudo to write to /etc/mosquitto/certs/
    local install_cmd="${ACME_BIN} --install-cert -d ${DOMAIN} \
        --fullchain-file ${CERT_FILE} \
        --key-file ${KEY_FILE} \
        --reloadcmd 'systemctl reload mosquitto'"

    log_info "Running: ${install_cmd}"
    log_info ""
    log_warn "This command requires sudo access to:"
    log_warn "  1. Write certificate files to ${CERT_DIR}/"
    log_warn "  2. Reload Mosquitto service"
    log_info ""

    # Try to run the install command
    if sudo "${ACME_BIN}" --install-cert -d "${DOMAIN}" \
        --fullchain-file "${CERT_FILE}" \
        --key-file "${KEY_FILE}" \
        --reloadcmd "systemctl reload mosquitto"; then

        log_info ""
        log_info "Certificate installed successfully!"

        # Fix permissions (acme.sh installs as root)
        log_info "Setting correct file permissions..."
        sudo chown mosquitto:mosquitto "${CERT_FILE}" "${KEY_FILE}"
        sudo chmod 644 "${CERT_FILE}"
        sudo chmod 600 "${KEY_FILE}"

        log_info "  ${CERT_FILE}: 644 (mosquitto:mosquitto)"
        log_info "  ${KEY_FILE}: 600 (mosquitto:mosquitto)"

        return 0
    else
        log_error "Certificate installation failed!"
        return 1
    fi
}

# Main execution
main() {
    local staging=""
    local install=""
    local force=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --staging)
                staging="yes"
                shift
                ;;
            --production)
                staging=""
                shift
                ;;
            --install)
                install="yes"
                shift
                ;;
            --force)
                force="yes"
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                log_error "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    log_info "=== SSL/TLS Certificate Issuance for ${DOMAIN} ==="
    log_info ""

    # Pre-flight checks
    check_acme_installed
    check_dns_credentials

    log_info ""

    # Check for existing certificate
    if check_existing_certificate "${staging}"; then
        if [[ -z "${force}" ]]; then
            log_info ""
            log_info "Certificate already exists. Use --force to re-issue."

            # If --install was requested, proceed with installation
            if [[ -n "${install}" ]]; then
                log_info ""
                install_certificate
            fi
            exit 0
        fi
    fi

    log_info ""

    # Issue certificate
    if ! issue_certificate "${staging}" "${force}"; then
        exit 1
    fi

    # Install if requested
    if [[ -n "${install}" ]]; then
        log_info ""
        install_certificate
    fi

    log_info ""
    log_info "=== Certificate Issuance Complete ==="
    log_info ""

    if [[ -z "${install}" ]]; then
        log_info "Next steps:"
        log_info "  1. Install certificate: $(basename "$0") --install"
        log_info "  2. Or manually install with:"
        log_info "     ${ACME_BIN} --install-cert -d ${DOMAIN} \\"
        log_info "       --fullchain-file ${CERT_FILE} \\"
        log_info "       --key-file ${KEY_FILE} \\"
        log_info "       --reloadcmd 'systemctl reload mosquitto'"
    else
        log_info "Certificate is installed and Mosquitto should be serving TLS."
        log_info ""
        log_info "Test with:"
        log_info "  openssl s_client -connect ${DOMAIN}:8883 -servername ${DOMAIN}"
    fi
    log_info ""
}

main "$@"
