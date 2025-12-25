#!/bin/bash
#
# check-ssl-status.sh - Check SSL/TLS setup status for Mosquitto MQTT broker
#
# This script shows the current status of all components needed for SSL/TLS setup.
# Run this before complete-ssl-setup.sh to see what's ready and what's missing.
#
# Usage: ./scripts/check-ssl-status.sh
#
# No root required - just checks status.
#

set -uo pipefail

# Configuration
DOMAIN="mqtt.unixweb.de"
CERT_DIR="/etc/mosquitto/certs"
CERT_FILE="${CERT_DIR}/${DOMAIN}.crt"
KEY_FILE="${CERT_DIR}/${DOMAIN}.key"
ACME_HOME="${HOME}/.acme.sh"
ACME_BIN="${ACME_HOME}/acme.sh"
ACME_CERT_DIR="${ACME_HOME}/${DOMAIN}_ecc"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

# Status indicators
OK="${GREEN}✓${NC}"
FAIL="${RED}✗${NC}"
WARN="${YELLOW}!${NC}"
INFO="${BLUE}i${NC}"

echo -e "\n${CYAN}${BOLD}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}${BOLD}  SSL/TLS Setup Status Check for ${DOMAIN}${NC}"
echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════════════════════${NC}\n"

# Track overall status
TOTAL_CHECKS=0
PASSED_CHECKS=0
BLOCKED=0

check_status() {
    local name="$1"
    local status="$2"
    local message="$3"
    local extra="${4:-}"

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    case "$status" in
        ok)
            echo -e "  ${OK} ${name}: ${GREEN}${message}${NC}"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
            ;;
        fail)
            echo -e "  ${FAIL} ${name}: ${RED}${message}${NC}"
            if [[ -n "${extra}" ]]; then
                echo -e "     ${extra}"
            fi
            ;;
        warn)
            echo -e "  ${WARN} ${name}: ${YELLOW}${message}${NC}"
            if [[ -n "${extra}" ]]; then
                echo -e "     ${extra}"
            fi
            ;;
        blocked)
            echo -e "  ${FAIL} ${name}: ${RED}${message}${NC}"
            if [[ -n "${extra}" ]]; then
                echo -e "     ${extra}"
            fi
            BLOCKED=1
            ;;
    esac
}

# Section 1: Prerequisites
echo -e "${BOLD}1. PREREQUISITES${NC}\n"

# Check Mosquitto
if command -v mosquitto &>/dev/null; then
    check_status "Mosquitto" "ok" "Installed"
elif [[ -f "/usr/sbin/mosquitto" ]]; then
    check_status "Mosquitto" "ok" "Installed at /usr/sbin/mosquitto"
else
    check_status "Mosquitto" "fail" "Not installed" "Install: apt-get install mosquitto mosquitto-clients"
fi

# Check Mosquitto user
if id mosquitto &>/dev/null 2>&1; then
    check_status "Mosquitto user" "ok" "User exists"
else
    check_status "Mosquitto user" "fail" "User does not exist"
fi

# Check acme.sh
if [[ -f "${ACME_BIN}" && -x "${ACME_BIN}" ]]; then
    check_status "acme.sh" "ok" "Installed at ${ACME_BIN}"
else
    check_status "acme.sh" "fail" "Not installed" "Install: curl https://get.acme.sh | sh -s email=admin@example.com"
fi

# Section 2: DNS Token
echo -e "\n${BOLD}2. DNS TOKEN${NC}\n"

if [[ -f "${ACME_HOME}/account.conf" ]]; then
    if grep -q "SAVED_HETZNER_TOKEN" "${ACME_HOME}/account.conf" 2>/dev/null; then
        # Extract and test token
        token=$(grep "SAVED_HETZNER_TOKEN" "${ACME_HOME}/account.conf" 2>/dev/null | head -1 | cut -d"'" -f2 || true)

        if [[ -n "${token}" && "${#token}" -gt 10 ]]; then
            check_status "DNS Token" "ok" "Configured in account.conf"

            # Test token access
            echo -e "\n  Testing Cloud DNS API access..."
            response=$(curl -s -H "Authorization: Bearer ${token}" "https://api.hetzner.cloud/v1/zones" 2>/dev/null || echo '{"error":"connection failed"}')

            if echo "${response}" | grep -q '"zones":\[\]'; then
                check_status "Zone Access" "blocked" "Token has ZERO zones accessible" "→ Get token from correct Hetzner Cloud account (see instructions below)"
            elif echo "${response}" | grep -q "unixweb.de"; then
                check_status "Zone Access" "ok" "Token has access to unixweb.de zone"
            elif echo "${response}" | grep -q '"zones":\['; then
                # Has zones but not unixweb.de
                zones=$(echo "${response}" | grep -o '"name":"[^"]*"' | head -3 | tr '\n' ' ')
                check_status "Zone Access" "blocked" "Token does NOT have access to unixweb.de" "→ Found zones: ${zones}"
            elif echo "${response}" | grep -q '"error"'; then
                check_status "Zone Access" "blocked" "Token is INVALID" "→ Generate new token at console.hetzner.cloud"
            else
                check_status "Zone Access" "warn" "Could not verify (network issue?)"
            fi
        else
            check_status "DNS Token" "fail" "Token appears empty or invalid"
        fi
    else
        check_status "DNS Token" "fail" "Not configured" "Add SAVED_HETZNER_TOKEN to ${ACME_HOME}/account.conf"
    fi
else
    check_status "account.conf" "fail" "File not found" "${ACME_HOME}/account.conf"
fi

# Section 3: Certificate Status
echo -e "\n${BOLD}3. CERTIFICATE STATUS${NC}\n"

# Check if domain is registered with acme.sh
if [[ -f "${ACME_BIN}" ]] && "${ACME_BIN}" --list 2>/dev/null | grep -q "${DOMAIN}"; then
    check_status "Domain Registration" "ok" "Registered with acme.sh"

    # Show registration details
    echo -e "     $(${ACME_BIN} --list 2>/dev/null | grep "${DOMAIN}" | head -1)"
else
    check_status "Domain Registration" "warn" "Not registered with acme.sh yet"
fi

# Check for certificate files in acme.sh directory
if [[ -d "${ACME_CERT_DIR}" ]]; then
    if [[ -f "${ACME_CERT_DIR}/fullchain.cer" ]]; then
        check_status "Certificate (acme.sh)" "ok" "Exists in ${ACME_CERT_DIR}/"

        # Show certificate details
        issuer=$(openssl x509 -in "${ACME_CERT_DIR}/fullchain.cer" -noout -issuer 2>/dev/null | sed 's/issuer=//' || echo "unknown")
        expires=$(openssl x509 -in "${ACME_CERT_DIR}/fullchain.cer" -noout -enddate 2>/dev/null | cut -d= -f2 || echo "unknown")
        echo -e "     Issuer: ${issuer}"
        echo -e "     Expires: ${expires}"
    else
        check_status "Certificate (acme.sh)" "fail" "NOT FOUND - Certificate issuance failed" "→ Run: ./scripts/issue-certificate.sh --staging"
    fi

    if [[ -f "${ACME_CERT_DIR}/${DOMAIN}.key" ]]; then
        check_status "Private Key (acme.sh)" "ok" "Exists"
    else
        check_status "Private Key (acme.sh)" "fail" "Not found"
    fi
else
    check_status "Certificate Dir" "warn" "Not created yet (${ACME_CERT_DIR}/)"
fi

# Section 4: Mosquitto Installation
echo -e "\n${BOLD}4. MOSQUITTO INSTALLATION${NC}\n"

# Check certificate directory
if [[ -d "${CERT_DIR}" ]]; then
    perms=$(stat -c '%a' "${CERT_DIR}" 2>/dev/null || echo "unknown")
    owner=$(stat -c '%U:%G' "${CERT_DIR}" 2>/dev/null || echo "unknown")
    check_status "Cert Directory" "ok" "${CERT_DIR} (${owner}, ${perms})"
else
    check_status "Cert Directory" "fail" "Not created" "→ Run: sudo ./scripts/setup-mosquitto-certs.sh"
fi

# Check installed certificates
if [[ -f "${CERT_FILE}" ]]; then
    perms=$(stat -c '%a' "${CERT_FILE}" 2>/dev/null || echo "unknown")
    check_status "Installed Cert" "ok" "${CERT_FILE} (${perms})"
else
    check_status "Installed Cert" "fail" "Not installed" "→ Run: sudo ./scripts/install-certificate.sh"
fi

if [[ -f "${KEY_FILE}" ]]; then
    perms=$(stat -c '%a' "${KEY_FILE}" 2>/dev/null || echo "unknown")
    if [[ "${perms}" == "600" ]]; then
        check_status "Installed Key" "ok" "${KEY_FILE} (${perms})"
    else
        check_status "Installed Key" "warn" "${KEY_FILE} (${perms} - should be 600)"
    fi
else
    check_status "Installed Key" "fail" "Not installed"
fi

# Section 5: Renewal Configuration
echo -e "\n${BOLD}5. RENEWAL CONFIGURATION${NC}\n"

if [[ -f "${ACME_BIN}" ]]; then
    reload_cmd=$("${ACME_BIN}" --info -d "${DOMAIN}" 2>/dev/null | grep "Le_ReloadCmd" || true)
    if [[ -n "${reload_cmd}" ]]; then
        check_status "Reload Hook" "ok" "Configured"
        echo -e "     ${reload_cmd}"
    else
        check_status "Reload Hook" "warn" "Not configured"
    fi
fi

if crontab -l 2>/dev/null | grep -q "acme.sh"; then
    check_status "Cron Job" "ok" "Active"
else
    check_status "Cron Job" "warn" "Not found in crontab"
fi

# Summary
echo -e "\n${BOLD}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}SUMMARY${NC}"
echo -e "${BOLD}═══════════════════════════════════════════════════════════════════${NC}\n"

echo -e "  Checks passed: ${PASSED_CHECKS}/${TOTAL_CHECKS}\n"

if [[ ${BLOCKED} -eq 1 ]]; then
    echo -e "${RED}${BOLD}⚠ BLOCKER DETECTED: DNS Token Issue${NC}\n"
    echo -e "The Hetzner Cloud API token doesn't have access to the unixweb.de zone."
    echo -e "This is the PRIMARY blocker preventing certificate issuance.\n"
    echo -e "${BOLD}To fix:${NC}"
    echo -e "  1. Log into ${CYAN}https://console.hetzner.cloud/${NC}"
    echo -e "     (Use the project that OWNS the unixweb.de zone)"
    echo -e ""
    echo -e "  2. Navigate to: Security → API Tokens → Generate API Token"
    echo -e "     Give it a name like 'acme.sh-mqtt'"
    echo -e "     Make sure it has Read & Write permissions"
    echo -e ""
    echo -e "  3. Copy the token and update acme.sh config:"
    echo -e "     ${CYAN}nano ${ACME_HOME}/account.conf${NC}"
    echo -e "     Change: SAVED_HETZNER_TOKEN='YOUR_NEW_TOKEN'"
    echo -e ""
    echo -e "  4. Verify with: ${CYAN}./scripts/test-dns-token.sh YOUR_NEW_TOKEN${NC}"
    echo -e ""
    echo -e "  5. Then run: ${CYAN}sudo ./scripts/complete-ssl-setup.sh --staging${NC}"
    echo -e ""
elif [[ ! -f "${CERT_FILE}" ]]; then
    echo -e "${YELLOW}${BOLD}Certificate not yet installed to Mosquitto.${NC}\n"
    echo -e "Once the DNS token blocker is resolved, run:"
    echo -e "  ${CYAN}sudo ./scripts/complete-ssl-setup.sh --staging${NC}"
    echo -e ""
else
    echo -e "${GREEN}${BOLD}✓ All components are in place!${NC}\n"
fi

echo -e "${BOLD}Available Scripts:${NC}"
echo -e "  ./scripts/check-ssl-status.sh      - This status check"
echo -e "  ./scripts/test-dns-token.sh TOKEN  - Test a DNS API token"
echo -e "  sudo ./scripts/complete-ssl-setup.sh --staging  - Complete setup"
echo -e ""
