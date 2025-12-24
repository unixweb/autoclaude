#!/bin/bash
#
# test-dns-token.sh - Quick test of a Hetzner DNS Console API token
#
# This script verifies that a token has access to the unixweb.de DNS zone.
#
# Usage:
#   ./scripts/test-dns-token.sh YOUR_TOKEN_HERE
#
# If the token works, it will update ~/.acme.sh/account.conf automatically.
#

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ROOT_DOMAIN="unixweb.de"
DNS_API="https://dns.hetzner.com/api/v1"
ACCOUNT_CONF="${HOME}/.acme.sh/account.conf"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 YOUR_HETZNER_DNS_TOKEN"
    echo ""
    echo "Get your token from:"
    echo "  1. Log into https://dns.hetzner.com/"
    echo "  2. Go to Settings -> API tokens"
    echo "  3. Create a new token"
    echo ""
    exit 1
fi

TOKEN="$1"

echo ""
echo "Testing token with Hetzner DNS Console API..."
echo ""

# Test the token
RESPONSE=$(curl -s -H "Auth-API-Token: ${TOKEN}" "${DNS_API}/zones" 2>&1)

if echo "${RESPONSE}" | grep -q '"message":"Invalid authentication credentials"'; then
    echo -e "${RED}[FAIL]${NC} Invalid token - authentication failed"
    echo ""
    echo "Make sure you're using a token from https://dns.hetzner.com/"
    echo "(NOT from Hetzner Cloud Console at console.hetzner.cloud)"
    exit 1
fi

if echo "${RESPONSE}" | grep -q "\"name\":\"${ROOT_DOMAIN}\""; then
    echo -e "${GREEN}[OK]${NC} Token is valid and has access to ${ROOT_DOMAIN} zone!"
    echo ""

    # Ask to update account.conf
    echo "Would you like to update ~/.acme.sh/account.conf with this token? [y/N]"
    read -r CONFIRM

    if [[ "${CONFIRM}" =~ ^[Yy]$ ]]; then
        # Backup existing config
        cp "${ACCOUNT_CONF}" "${ACCOUNT_CONF}.backup"

        # Update the token (dns_hetzner uses SAVED_HETZNER_Token - mixed case)
        if grep -q "^SAVED_HETZNER_Token=" "${ACCOUNT_CONF}"; then
            sed -i "s|^SAVED_HETZNER_Token=.*|SAVED_HETZNER_Token='${TOKEN}'|" "${ACCOUNT_CONF}"
        else
            echo "SAVED_HETZNER_Token='${TOKEN}'" >> "${ACCOUNT_CONF}"
        fi

        echo -e "${GREEN}[OK]${NC} Token saved to ${ACCOUNT_CONF}"
        echo ""
        echo "Now you can issue the certificate:"
        echo "  ./scripts/issue-certificate.sh --staging"
        echo ""
    fi
else
    ZONES=$(echo "${RESPONSE}" | grep -o '"name":"[^"]*"' | sed 's/"name":"//g; s/"//g' | tr '\n' ' ' || echo "none")
    echo -e "${YELLOW}[WARN]${NC} Token is valid but does NOT have access to ${ROOT_DOMAIN}"
    echo ""
    echo "Zones accessible with this token: ${ZONES:-none}"
    echo ""
    echo "Make sure you're logged into the correct Hetzner account that manages ${ROOT_DOMAIN}"
    exit 1
fi
