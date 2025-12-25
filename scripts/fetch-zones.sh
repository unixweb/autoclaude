#!/bin/bash
#
# fetch-zones.sh - Fetch DNS zones from Hetzner Cloud DNS API
#
# This script retrieves all DNS zones from your Hetzner Cloud account
# using the Hetzner Cloud API v1.
#
# Usage:
#   ./scripts/fetch-zones.sh
#   ./scripts/fetch-zones.sh --token YOUR_TOKEN
#   ./scripts/fetch-zones.sh --json  # Output raw JSON
#
# Requirements:
#   - curl installed
#   - Hetzner Cloud API token with Read permissions
#   - Optional: jq for pretty JSON formatting
#

set -euo pipefail

# Configuration
HETZNER_CLOUD_API="https://api.hetzner.cloud/v1"
ACME_HOME="${HOME}/.acme.sh"
ACCOUNT_CONF="${ACME_HOME}/account.conf"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Options
OUTPUT_FORMAT="pretty"
TOKEN_OVERRIDE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --token)
            TOKEN_OVERRIDE="$2"
            shift 2
            ;;
        --json)
            OUTPUT_FORMAT="json"
            shift
            ;;
        --help|-h)
            echo "Usage: $(basename "$0") [OPTIONS]"
            echo ""
            echo "Fetch DNS zones from Hetzner Cloud DNS API."
            echo ""
            echo "Options:"
            echo "  --token TOKEN    Use specific token instead of configured one"
            echo "  --json           Output raw JSON response"
            echo "  --help           Show this help message"
            echo ""
            echo "Examples:"
            echo "  $(basename "$0")                  # Use token from account.conf"
            echo "  $(basename "$0") --json           # Get JSON output"
            echo "  $(basename "$0") --token abc123   # Use specific token"
            exit 0
            ;;
        *)
            echo -e "${RED}Error:${NC} Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Get token
TOKEN=""
if [[ -n "${TOKEN_OVERRIDE}" ]]; then
    TOKEN="${TOKEN_OVERRIDE}"
elif [[ -f "${ACCOUNT_CONF}" ]]; then
    TOKEN=$(grep -E "^SAVED_HETZNER_TOKEN=" "${ACCOUNT_CONF}" 2>/dev/null | cut -d"'" -f2 || true)

    if [[ -z "${TOKEN}" ]]; then
        echo -e "${RED}Error:${NC} No HETZNER_TOKEN found in ${ACCOUNT_CONF}"
        echo ""
        echo "To fix this, add the token to ${ACCOUNT_CONF}:"
        echo "  SAVED_HETZNER_TOKEN='your-token-here'"
        echo ""
        echo "Or provide a token:"
        echo "  $(basename "$0") --token YOUR_TOKEN"
        echo ""
        echo "Get your token from: https://console.hetzner.cloud/"
        echo "  Security -> API Tokens -> Generate API Token"
        exit 1
    fi
else
    echo -e "${RED}Error:${NC} account.conf not found at ${ACCOUNT_CONF}"
    echo ""
    echo "Provide a token with --token option:"
    echo "  $(basename "$0") --token YOUR_TOKEN"
    exit 1
fi

# Fetch zones
RESPONSE=$(curl -s -H "Authorization: Bearer ${TOKEN}" "${HETZNER_CLOUD_API}/zones" 2>&1)

# Check for errors
if echo "${RESPONSE}" | grep -q '"error"'; then
    ERROR_CODE=$(echo "${RESPONSE}" | grep -o '"code":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "unknown")
    ERROR_MESSAGE=$(echo "${RESPONSE}" | grep -o '"message":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "unknown")

    echo -e "${RED}Error:${NC} API request failed"
    echo "  Code: ${ERROR_CODE}"
    echo "  Message: ${ERROR_MESSAGE}"
    echo ""
    echo "Make sure your token is valid and has Read permissions."
    echo "Get token from: https://console.hetzner.cloud/ -> Security -> API Tokens"
    exit 1
fi

# Output based on format
if [[ "${OUTPUT_FORMAT}" == "json" ]]; then
    # Raw JSON output
    if command -v jq &>/dev/null; then
        echo "${RESPONSE}" | jq '.'
    else
        echo "${RESPONSE}"
    fi
else
    # Pretty formatted output
    echo ""
    echo -e "${BLUE}=== Hetzner Cloud DNS Zones ===${NC}"
    echo ""

    if echo "${RESPONSE}" | grep -q '"zones":\[\]'; then
        echo -e "${YELLOW}No zones found${NC}"
        echo ""
        echo "Your Hetzner Cloud project has no DNS zones configured."
        echo ""
        echo "To create a zone:"
        echo "  1. Log into https://console.hetzner.cloud/"
        echo "  2. Navigate to DNS section"
        echo "  3. Click 'Add Zone' and follow the wizard"
        echo ""
    else
        ZONE_COUNT=$(echo "${RESPONSE}" | grep -o '"name":"[^"]*"' | wc -l || echo "0")
        echo -e "${GREEN}Found ${ZONE_COUNT} zone(s)${NC}"
        echo ""

        # Extract and display zones
        echo "${RESPONSE}" | grep -o '"zones":\[.*\]' | sed 's/"zones":\[//; s/\]$//' | \
        while IFS= read -r zones_json; do
            # Parse each zone (simple parsing without jq)
            echo "${zones_json}" | grep -o '{[^}]*}' | while IFS= read -r zone; do
                NAME=$(echo "${zone}" | grep -o '"name":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
                ID=$(echo "${zone}" | grep -o '"id":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
                TTL=$(echo "${zone}" | grep -o '"ttl":[0-9]*' | cut -d':' -f2 || echo "unknown")

                echo -e "  ${GREEN}●${NC} ${NAME}"
                echo "    ID:  ${ID}"
                echo "    TTL: ${TTL}"
                echo ""
            done
        done

        echo -e "${BLUE}=== Zone Details ===${NC}"
        echo ""
        echo "To view records for a zone, use the zone ID:"
        echo "  curl -H \"Authorization: Bearer \$TOKEN\" \\"
        echo "    \"${HETZNER_CLOUD_API}/zones/{ZONE_ID}/records\""
        echo ""
    fi
fi
