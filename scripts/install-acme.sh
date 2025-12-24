#!/bin/bash
#
# install-acme.sh - Install acme.sh ACME client for SSL certificate management
#
# This script installs acme.sh with email admin@unixweb.de for Let's Encrypt
# certificate management. It's designed to be idempotent - safe to run multiple times.
#
# Usage: ./scripts/install-acme.sh
#
# Requirements:
#   - curl installed
#   - Internet access to https://get.acme.sh
#

set -euo pipefail

# Configuration
ACME_EMAIL="admin@unixweb.de"
ACME_HOME="${HOME}/.acme.sh"
ACME_BIN="${ACME_HOME}/acme.sh"

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

# Check if curl is available
check_dependencies() {
    if ! command -v curl &> /dev/null; then
        log_error "curl is required but not installed. Please install curl first."
        exit 1
    fi
}

# Check if acme.sh is already installed
check_existing_installation() {
    if [[ -f "${ACME_BIN}" ]]; then
        local version
        version=$("${ACME_BIN}" --version 2>/dev/null | head -1 || echo "unknown")
        log_info "acme.sh is already installed (${version})"
        log_info "Location: ${ACME_HOME}"
        return 0
    fi
    return 1
}

# Install acme.sh
install_acme() {
    log_info "Installing acme.sh with email: ${ACME_EMAIL}"

    # Download and run the installer
    curl -fsSL https://get.acme.sh | sh -s email="${ACME_EMAIL}"

    if [[ $? -eq 0 ]] && [[ -f "${ACME_BIN}" ]]; then
        log_info "acme.sh installed successfully!"

        # Display version
        local version
        version=$("${ACME_BIN}" --version 2>/dev/null | head -1 || echo "unknown")
        log_info "Installed version: ${version}"
        log_info "Location: ${ACME_HOME}"

        # Note about sourcing bashrc
        log_info ""
        log_info "To use acme.sh in the current session, run:"
        log_info "  source ~/.bashrc"
        log_info ""
        log_info "Or use the full path:"
        log_info "  ${ACME_BIN}"
    else
        log_error "acme.sh installation failed!"
        exit 1
    fi
}

# Verify installation
verify_installation() {
    if [[ -f "${ACME_BIN}" ]] && [[ -x "${ACME_BIN}" ]]; then
        log_info "Installation verified: acme.sh is ready to use"

        # Check if cron job was installed
        if crontab -l 2>/dev/null | grep -q "acme.sh"; then
            log_info "Cron job for auto-renewal is configured"
        else
            log_warn "Cron job for auto-renewal may not be configured"
        fi

        return 0
    else
        log_error "Verification failed: acme.sh binary not found or not executable"
        return 1
    fi
}

# Main execution
main() {
    log_info "=== acme.sh Installation Script ==="
    log_info ""

    check_dependencies

    if check_existing_installation; then
        log_info ""
        log_info "Skipping installation - acme.sh is already installed"
        log_info "To reinstall, remove ${ACME_HOME} first"
        verify_installation
        exit 0
    fi

    log_info ""
    install_acme
    log_info ""
    verify_installation

    log_info ""
    log_info "=== Installation Complete ==="
    log_info ""
    log_info "Next steps:"
    log_info "  1. Configure Hetzner DNS API token in ~/.acme.sh/account.conf"
    log_info "  2. Issue certificate: acme.sh --issue --dns dns_hetzner -d mqtt.unixweb.de"
    log_info ""
}

main "$@"
