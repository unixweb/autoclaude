# SSL/TLS Certificate Setup for Mosquitto MQTT Broker

This document describes how to set up automated SSL/TLS certificates for the Mosquitto MQTT broker using Let's Encrypt and acme.sh with Hetzner DNS validation.

## Quick Start

```bash
# 1. Check current status
./scripts/check-ssl-status.sh

# 2. Fix DNS token if needed (see Troubleshooting)

# 3. Run complete setup
sudo ./scripts/complete-ssl-setup.sh --staging

# 4. For production certificate
sudo ./scripts/complete-ssl-setup.sh --production
```

## Prerequisites

| Requirement | How to Check | How to Fix |
|-------------|--------------|------------|
| Mosquitto installed | `which mosquitto` | `apt-get install mosquitto mosquitto-clients` |
| acme.sh installed | `ls ~/.acme.sh/acme.sh` | `curl https://get.acme.sh \| sh -s email=admin@example.com` |
| DNS token configured | `grep HETZNER ~/.acme.sh/account.conf` | See [DNS Token Setup](#dns-token-setup) |
| Certificate directory | `ls /etc/mosquitto/certs/` | `sudo ./scripts/setup-mosquitto-certs.sh` |

## Configuration

### SSL Domain Setup

The SSL domain is configured centrally in `~/.acme.sh/account.conf`:

```bash
# Set your SSL domain (default: mqtt.unixweb.de)
echo "SSL_DOMAIN='mqtt.unixweb.de'" >> ~/.acme.sh/account.conf
```

**IMPORTANT**: If you change the SSL_DOMAIN, you must also update the certificate paths in `mosquitto/config/mosquitto.conf` to match your domain.

All scripts automatically read this configuration, so you only need to change it in one place.

### DNS Token Setup

**IMPORTANT**: The DNS token must come from the correct Hetzner account.

Hetzner has **two separate services**:
- **Hetzner Cloud** (console.hetzner.cloud) - for servers, volumes, etc.
- **Hetzner DNS Console** (dns.hetzner.com) - for DNS zones

You need a token from **Hetzner DNS Console** (dns.hetzner.com), and it must be from the account that manages your DNS zone.

### Getting the Correct Token

1. Go to https://dns.hetzner.com/
2. Log in with the account that owns the `unixweb.de` zone
3. Navigate to: **Settings** → **API Tokens** → **Create API Token**
4. Give it a descriptive name (e.g., `acme.sh-mqtt-cert`)
5. Copy the token immediately (it won't be shown again)

### Testing Your Token

```bash
# Quick test
./scripts/test-dns-token.sh YOUR_TOKEN_HERE

# Or manually test
curl -H "Auth-API-Token: YOUR_TOKEN" https://dns.hetzner.com/api/v1/zones
```

A valid token should return a JSON response with `"zones":[...]` containing the `unixweb.de` zone.

### Updating the Configuration

```bash
# Edit account.conf
nano ~/.acme.sh/account.conf

# Update these lines:
SSL_DOMAIN='your-domain.example.com'
SAVED_HETZNER_Token='YOUR_NEW_TOKEN_HERE'
```

**Note**: After changing SSL_DOMAIN, update the certificate paths in `mosquitto/config/mosquitto.conf`.

## Certificate Management

### Issue Staging Certificate (Testing)

Use staging certificates first to avoid Let's Encrypt rate limits (50 certs/week):

```bash
sudo ./scripts/complete-ssl-setup.sh --staging
```

Staging certificates are NOT trusted by clients but allow testing the entire workflow.

### Issue Production Certificate

After successful staging test:

```bash
sudo ./scripts/complete-ssl-setup.sh --production
```

### Manual Certificate Operations

```bash
# Issue certificate only (no installation)
./scripts/issue-certificate.sh --staging

# Install existing certificate to Mosquitto
sudo ./scripts/install-certificate.sh

# Force renewal (reads SSL_DOMAIN from config)
SSL_DOMAIN=$(grep "^SSL_DOMAIN=" ~/.acme.sh/account.conf | cut -d"'" -f2)
~/.acme.sh/acme.sh --renew -d "${SSL_DOMAIN:-mqtt.unixweb.de}" --force
```

## File Locations

| File | Purpose |
|------|---------|
| `/etc/mosquitto/certs/mqtt.unixweb.de.crt` | Installed certificate (fullchain) |
| `/etc/mosquitto/certs/mqtt.unixweb.de.key` | Installed private key |
| `~/.acme.sh/mqtt.unixweb.de_ecc/` | acme.sh certificate directory |
| `~/.acme.sh/account.conf` | acme.sh configuration (contains DNS token) |
| `/etc/mosquitto/conf.d/ssl.conf` | Mosquitto TLS configuration |

### File Permissions

| File | Permissions | Owner |
|------|-------------|-------|
| Certificate (.crt) | 644 | mosquitto:mosquitto |
| Private Key (.key) | 600 | mosquitto:mosquitto |
| Cert Directory | 755 | mosquitto:mosquitto |

## Mosquitto TLS Configuration

After certificates are installed, create `/etc/mosquitto/conf.d/ssl.conf`:

```conf
# TLS Listener Configuration
listener 8883
protocol mqtt

# Certificate Files
certfile /etc/mosquitto/certs/mqtt.unixweb.de.crt
keyfile /etc/mosquitto/certs/mqtt.unixweb.de.key

# TLS Protocol Version (minimum TLS 1.2)
tls_version tlsv1.2

# Security Settings
require_certificate false
```

Then reload Mosquitto:

```bash
# Test configuration
mosquitto -c /etc/mosquitto/mosquitto.conf -t

# Reload without dropping connections
sudo systemctl reload mosquitto

# Check status
sudo systemctl status mosquitto
```

## Verification Commands

### Check Certificate

```bash
# View installed certificate
openssl x509 -in /etc/mosquitto/certs/mqtt.unixweb.de.crt -noout -text

# Check expiration
openssl x509 -in /etc/mosquitto/certs/mqtt.unixweb.de.crt -noout -dates
```

### Test TLS Connection

```bash
# Test with openssl
echo 'QUIT' | openssl s_client -connect mqtt.unixweb.de:8883 -servername mqtt.unixweb.de

# Test with mosquitto client
mosquitto_pub -h mqtt.unixweb.de -p 8883 --capath /etc/ssl/certs/ -t test -m "hello" -d
```

### Check Renewal Configuration

```bash
# List certificates
~/.acme.sh/acme.sh --list

# Check renewal hook
~/.acme.sh/acme.sh --info -d mqtt.unixweb.de | grep Le_ReloadCmd

# Check cron job
crontab -l | grep acme
```

## Automatic Renewal

Certificates auto-renew via cron job installed by acme.sh:
- Runs daily at a random time
- Renews certificates when < 30 days remain (60 days into 90-day validity)
- Executes reload hook after successful renewal

To force renewal:

```bash
~/.acme.sh/acme.sh --renew -d mqtt.unixweb.de --force
```

## Troubleshooting

### DNS Token Returns Empty Zones

**Symptom**: `{"zones":[],...}` when testing token

**Cause**: Token is from wrong Hetzner account

**Solution**: Get token from the account that owns unixweb.de zone at dns.hetzner.com

### "Invalid domain" Error

**Symptom**: Certificate issuance fails with "Invalid domain" from dns_hetzner API

**Cause**: Same as above - token doesn't have zone access

### Rate Limited

**Symptom**: "too many failed authorizations" error

**Cause**: Let's Encrypt rate limit (5 failures per hour per account/domain)

**Solution**: Wait 1 hour, then retry with correct token

### Certificate Files Missing

**Symptom**: `~/.acme.sh/mqtt.unixweb.de_ecc/fullchain.cer` doesn't exist

**Cause**: Certificate issuance failed (usually DNS token issue)

**Solution**: Fix DNS token, then run `./scripts/issue-certificate.sh --staging`

### Mosquitto Won't Start

**Symptom**: `systemctl status mosquitto` shows failed

**Steps**:
1. Check config syntax: `mosquitto -c /etc/mosquitto/mosquitto.conf -t`
2. Check certificate paths in `/etc/mosquitto/conf.d/ssl.conf`
3. Verify file permissions: `ls -la /etc/mosquitto/certs/`
4. Check logs: `journalctl -u mosquitto -n 50`

## Available Scripts

| Script | Purpose | Root Required |
|--------|---------|---------------|
| `check-ssl-status.sh` | Show current setup status | No |
| `test-dns-token.sh` | Test a DNS API token | No |
| `verify-dns-setup.sh` | Full DNS verification | No |
| `issue-certificate.sh` | Issue certificate | No |
| `install-certificate.sh` | Install cert to Mosquitto | Yes |
| `setup-mosquitto-certs.sh` | Create cert directory | Yes |
| `complete-ssl-setup.sh` | Complete end-to-end setup | Yes |

## Security Notes

- DNS token is stored in `~/.acme.sh/account.conf` - protect this file
- Private key has 600 permissions (owner-only read)
- Always use `systemctl reload` (not restart) to preserve connections
- TLS 1.2 minimum is enforced (TLS 1.0/1.1 are insecure)
- Staging certificates are NOT trusted - for testing only
