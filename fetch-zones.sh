#!/bin/bash
#
# Fetch Hetzner Cloud DNS Zones
# Uses Bearer token authentication from access.txt
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOKEN_FILE="${SCRIPT_DIR}/access.txt"
API_ENDPOINT="https://dns.hetzner.com/api/v1/zones"
# Note: Hetzner DNS API uses dns.hetzner.com with Auth-API-Token header

# Check if token file exists
if [[ ! -f "${TOKEN_FILE}" ]]; then
    echo "Error: Token file '${TOKEN_FILE}' not found." >&2
    echo "Please create access.txt with your Hetzner API token." >&2
    exit 1
fi

# Read token from file (trim whitespace)
TOKEN=$(cat "${TOKEN_FILE}" | tr -d '[:space:]')

# Check if token is empty
if [[ -z "${TOKEN}" ]]; then
    echo "Error: Token file is empty." >&2
    exit 1
fi

# Execute API call
curl -s -H "Auth-API-Token: ${TOKEN}" "${API_ENDPOINT}"
