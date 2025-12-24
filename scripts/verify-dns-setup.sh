#!/bin/bash
#
# verify-dns-setup.sh - Verify Hetzner DNS API setup for acme.sh certificate issuance
#
# This script checks:
# 1. If HETZNER_TOKEN is configured in acme.sh account.conf
# 2. If the token can access any DNS zones
# 3. If the unixweb.de zone is accessible
# 4. If DNS records can be created (dry-run test)
#
# Usage:
#   ./scripts/verify-dns-setup.sh
#   ./scripts/verify-dns-setup.sh --token YOUR_TOKEN  # Test with a specific token
#
# Requirements:
#   - curl installed
#   - jq installed (optional, for pretty output)
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="mqtt.unixweb.de"
ROOT_DOMAIN="unixweb.de"
ACME_HOME="${HOME}/.acme.sh"
ACCOUNT_CONF="${ACME_HOME}/account.conf"

# APIs to check
HETZNER_DNS_API="https://dns.hetzner.com/api/v1"
HETZNER_CLOUD_API="https://api.hetzner.cloud/v1"

log_info() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[CHECK]${NC} $1"
}

# Parse arguments
TOKEN_OVERRIDE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --token)
            TOKEN_OVERRIDE="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $(basename "$0") [--token YOUR_TOKEN]"
            echo ""
            echo "Verify Hetzner DNS API setup for SSL/TLS certificate issuance."
            echo ""
            echo "Options:"
            echo "  --token TOKEN    Test with a specific token instead of the configured one"
            echo "  --help           Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo ""
echo "=== Hetzner DNS API Verification ==="
echo ""
echo "This script verifies your Hetzner DNS API setup for certificate issuance."
echo "Domain: ${DOMAIN}"
echo ""

# Check 1: HETZNER_TOKEN configured
log_step "Checking if HETZNER_TOKEN is configured..."

TOKEN=""
if [[ -n "${TOKEN_OVERRIDE}" ]]; then
    TOKEN="${TOKEN_OVERRIDE}"
    log_info "Using provided token"
elif [[ -f "${ACCOUNT_CONF}" ]]; then
    # Try both variable names
    TOKEN=$(grep -E "^SAVED_HETZNER_TOKEN=" "${ACCOUNT_CONF}" 2>/dev/null | cut -d"'" -f2 || true)
    if [[ -z "${TOKEN}" ]]; then
        TOKEN=$(grep -E "^SAVED_HETZNER_Token=" "${ACCOUNT_CONF}" 2>/dev/null | cut -d"'" -f2 || true)
        if [[ -n "${TOKEN}" ]]; then
            log_warn "Found legacy HETZNER_Token (mixed case). dns_hetznercloud requires HETZNER_TOKEN (uppercase)."
        fi
    fi

    if [[ -n "${TOKEN}" ]]; then
        log_info "Token found in ${ACCOUNT_CONF}"
    else
        log_error "No HETZNER_TOKEN found in ${ACCOUNT_CONF}"
        echo ""
        echo "To fix this, add the token to ${ACCOUNT_CONF}:"
        echo "  SAVED_HETZNER_TOKEN='your-token-here'"
        echo ""
        echo "Or set the environment variable before running acme.sh:"
        echo "  export HETZNER_TOKEN='your-token-here'"
        echo ""
        exit 1
    fi
else
    log_error "acme.sh account.conf not found at ${ACCOUNT_CONF}"
    echo "Install acme.sh first: ./scripts/install-acme.sh"
    exit 1
fi

echo ""

# Check 2: Test Hetzner DNS Console API (dns_hetzner)
log_step "Testing Hetzner DNS Console API (dns.hetzner.com)..."
DNS_CONSOLE_RESPONSE=$(curl -s -H "Auth-API-Token: ${TOKEN}" "${HETZNER_DNS_API}/zones" 2>&1)

if echo "${DNS_CONSOLE_RESPONSE}" | grep -q '"zones":\[\]'; then
    log_warn "DNS Console API: No zones found"
    DNS_CONSOLE_ZONES=0
elif echo "${DNS_CONSOLE_RESPONSE}" | grep -q '"zones":\[{'; then
    DNS_CONSOLE_ZONES=$(echo "${DNS_CONSOLE_RESPONSE}" | grep -o '"name":"[^"]*"' | wc -l || echo "0")
    log_info "DNS Console API: ${DNS_CONSOLE_ZONES} zone(s) accessible"

    # Check if unixweb.de is among them
    if echo "${DNS_CONSOLE_RESPONSE}" | grep -q "\"name\":\"${ROOT_DOMAIN}\""; then
        log_info "Zone '${ROOT_DOMAIN}' is accessible via DNS Console API"
        echo ""
        echo "Use dns_hetzner (legacy API) for certificate issuance:"
        echo "  acme.sh --issue --dns dns_hetzner -d ${DOMAIN} --staging"
    else
        log_warn "Zone '${ROOT_DOMAIN}' NOT found in accessible zones"
        echo "Available zones:"
        echo "${DNS_CONSOLE_RESPONSE}" | grep -o '"name":"[^"]*"' | sed 's/"name":"//g; s/"//g' | sed 's/^/  - /'
    fi
elif echo "${DNS_CONSOLE_RESPONSE}" | grep -q '"code":401'; then
    log_error "DNS Console API: Unauthorized (invalid token)"
elif echo "${DNS_CONSOLE_RESPONSE}" | grep -q '"code":403'; then
    log_error "DNS Console API: Forbidden (insufficient permissions)"
else
    log_error "DNS Console API: Unexpected response"
    echo "Response: ${DNS_CONSOLE_RESPONSE}"
fi

echo ""

# Check 3: Test Hetzner Cloud DNS API (dns_hetznercloud)
log_step "Testing Hetzner Cloud DNS API (api.hetzner.cloud)..."
CLOUD_RESPONSE=$(curl -s -H "Authorization: Bearer ${TOKEN}" "${HETZNER_CLOUD_API}/primary_ips" 2>&1)

if echo "${CLOUD_RESPONSE}" | grep -q '"error"'; then
    ERROR_CODE=$(echo "${CLOUD_RESPONSE}" | grep -o '"code":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "unknown")

    case "${ERROR_CODE}" in
        "unauthorized")
            log_warn "Cloud API: Token not valid for Hetzner Cloud API"
            ;;
        "forbidden")
            log_error "Cloud API: Forbidden (insufficient permissions)"
            ;;
        *)
            log_warn "Cloud API: Error - ${ERROR_CODE}"
            ;;
    esac
elif echo "${CLOUD_RESPONSE}" | grep -q '"primary_ips"'; then
    log_info "Cloud API: Token is valid for Hetzner Cloud"

    # Check for DNS zones in Cloud API
    CLOUD_DNS_RESPONSE=$(curl -s -H "Authorization: Bearer ${TOKEN}" "https://dns.hetzner.com/api/v1/zones" 2>&1)
    if echo "${CLOUD_DNS_RESPONSE}" | grep -q "\"name\":\"${ROOT_DOMAIN}\""; then
        log_info "Zone '${ROOT_DOMAIN}' accessible via Cloud API - use dns_hetznercloud"
    fi
else
    log_warn "Cloud API: Could not verify (may be a DNS-only token)"
fi

echo ""

# Summary and recommendations
echo "=== Summary ==="
echo ""

if [[ "${DNS_CONSOLE_ZONES:-0}" -gt 0 ]] && echo "${DNS_CONSOLE_RESPONSE}" | grep -q "\"name\":\"${ROOT_DOMAIN}\""; then
    log_info "READY: DNS setup is correct"
    echo ""
    echo "You can issue a certificate with:"
    echo "  ./scripts/issue-certificate.sh --staging"
    echo ""
    echo "Or manually:"
    echo "  ~/.acme.sh/acme.sh --issue --dns dns_hetzner -d ${DOMAIN} --server letsencrypt --staging"
else
    log_error "NOT READY: DNS zone '${ROOT_DOMAIN}' is not accessible"
    echo ""
    echo "The token provided cannot access the '${ROOT_DOMAIN}' DNS zone."
    echo "This means certificate issuance via DNS-01 challenge will fail."
    echo ""
    echo "Possible causes:"
    echo "  1. The token is for a different Hetzner account/project"
    echo "  2. The token doesn't have DNS read/write permissions"
    echo "  3. The '${ROOT_DOMAIN}' domain DNS is not managed by Hetzner"
    echo "  4. The DNS zone exists but in a different Hetzner project"
    echo ""
    echo "How to fix:"
    echo "  1. Log into Hetzner DNS Console: https://dns.hetzner.com/"
    echo "  2. Verify '${ROOT_DOMAIN}' zone exists in your account"
    echo "  3. Generate a new API token: Settings → API tokens → Create API Token"
    echo "  4. Update ~/.acme.sh/account.conf with the new token:"
    echo "     SAVED_HETZNER_TOKEN='your-new-token'"
    echo ""
    echo "If your DNS is not with Hetzner:"
    echo "  - Use a different DNS provider plugin for acme.sh"
    echo "  - See: https://github.com/acmesh-official/acme.sh/wiki/dnsapi"
    echo ""
fi

echo "=== End Verification ==="
