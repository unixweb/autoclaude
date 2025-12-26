# Release Notes v2.2.0

**Datum:** Dezember 2025
**Version:** 2.2.0
**Vorgängerversion:** v2.1.1

---

## Überblick

Diese Version bringt umfangreiche Erweiterungen für MQTT-Kommunikation, automatisiertes SSL/TLS-Zertifikatsmanagement und verbesserte Datenbank-Administration. Mit 27 Commits wurden neue Features implementiert, bestehende Funktionalitäten verbessert und die Sicherheit erhöht.

---

## Neue Features

### 1. Eclipse Mosquitto MQTT Broker

Ein vollständig integrierter MQTT-Broker für IoT-Anwendungen und Echtzeit-Kommunikation:

- **Eclipse Mosquitto** als Docker-Service in `docker-compose.yml` integriert
- **Vier Kommunikations-Ports:**
  - Port 1883: Standard MQTT (unverschlüsselt)
  - Port 8883: MQTT über TLS (verschlüsselt)
  - Port 9001: WebSocket (unverschlüsselt)
  - Port 8084: WebSocket über TLS (verschlüsselt)
- **SSL/TLS-Unterstützung** mit Let's Encrypt Zertifikaten
- **Konfigurierbare Domain** über `SSL_DOMAIN` Variable (Standard: mqtt.unixweb.de)
- Umfassende Dokumentation im README (450+ Zeilen)

### 2. Automatisiertes SSL/TLS Zertifikat-Management

Ein komplettes System zur automatischen Verwaltung von SSL/TLS-Zertifikaten:

- **Let's Encrypt Integration** über acme.sh
- **DNS-01 Challenge** mit Hetzner Cloud DNS API
- **Automatische Zertifikatserneuerung** (60 Tage vor Ablauf)
- **Neue Scripts:**
  - `issue-certificate.sh` - Zertifikatsausstellung (Staging/Production)
  - `install-certificate.sh` - Installation im Mosquitto-Verzeichnis
  - `complete-ssl-setup.sh` - Einheitliches One-Command Setup
  - `check-ssl-status.sh` - Status-Prüfung und Diagnose
  - `setup-mosquitto-certs.sh` - Verzeichnis-Einrichtung
  - `fix-cert-permissions.sh` - Berechtigungskorrektur
- **Umfassende Dokumentation** in `docs/SSL-SETUP.md`

### 3. Hetzner Cloud DNS API Integration

Vollständige Integration der Hetzner DNS APIs für Zertifikatsvalidierung:

- **Unterstützung beider Hetzner APIs:**
  - Hetzner DNS Console API (dns.hetzner.com)
  - Hetzner Cloud API (api.hetzner.cloud)
- **Neue Scripts:**
  - `fetch-zones.sh` - DNS-Zonen auflisten
  - `verify-dns-setup.sh` - DNS-Konfiguration überprüfen
  - `test-dns-token.sh` - API-Token validieren
- **Korrekte Authentifizierung:**
  - DNS Console: `Auth-API-Token` Header
  - Cloud API: `Authorization: Bearer` Header

### 4. Adminer Datenbank-Administration

Web-basiertes Datenbank-Management-Tool:

- **Adminer Service** in docker-compose.yml integriert
- **Erreichbar unter:** http://localhost:8081
- **Unterstützt PostgreSQL** (und weitere Datenbanken)
- **Features:**
  - Direkte Verbindung zur `db` Service
  - Healthcheck mit wget
  - Container-Name: `app_adminer`
- QA-Signoff nach vollständiger Verifikation

---

## Verbesserungen

### Sicherheit

- **Secret Scanning:** Automatische Überprüfung aller Scripts auf versehentlich committete Secrets
- **Aktualisierte .gitignore:**
  - `access.txt` für Token-Schutz hinzugefügt
  - Zertifikatsdateien ausgeschlossen
- **API-Authentifizierung:** Dokumentierte Unterschiede zwischen DNS Console und Cloud API

### Konfiguration

- **SSL_DOMAIN Variable:** Konfigurierbare Domain statt hardcodierter Werte
- **HETZNER_TOKEN:** Neuer Eintrag in `.env.example` für DNS-API-Zugang
- **MQTT Port-Variablen:** Konfigurierbare Ports in `.env.example`

### Dokumentation

- **README.md:** Erweitert um MQTT-Broker Setup, SSL/TLS-Management und Troubleshooting
- **docs/SSL-SETUP.md:** Vollständiger SSL/TLS-Setup-Guide
- **API-Dokumentation:** Inline-Kommentare für Authentifizierungsmethoden

---

## Bug-Fixes

- **API-Endpunkte korrigiert:** `fetch-zones.sh` verwendet jetzt korrekten Cloud API Endpunkt
- **Authentifizierung korrigiert:** DNS Console API verwendet `Auth-API-Token` statt `Bearer`
- **Script-Kompatibilität:** Alle Scripts lesen Domain aus zentraler Konfiguration

---

## Technische Details

### Neue Dateien

| Datei | Beschreibung |
|-------|--------------|
| `scripts/issue-certificate.sh` | Let's Encrypt Zertifikatsausstellung |
| `scripts/install-certificate.sh` | Zertifikats-Installation für Mosquitto |
| `scripts/complete-ssl-setup.sh` | Vollständiges SSL-Setup in einem Befehl |
| `scripts/check-ssl-status.sh` | SSL-Status und Diagnose |
| `scripts/setup-mosquitto-certs.sh` | Zertifikatsverzeichnis einrichten |
| `scripts/fix-cert-permissions.sh` | Dateiberechtigungen korrigieren |
| `scripts/fetch-zones.sh` | DNS-Zonen auflisten |
| `scripts/verify-dns-setup.sh` | DNS-Setup überprüfen |
| `scripts/test-dns-token.sh` | API-Token testen |
| `docs/SSL-SETUP.md` | SSL/TLS Dokumentation |
| `mosquitto/config/mosquitto.conf` | MQTT-Broker Konfiguration |

### Geänderte Dateien

- `docker-compose.yml` - MQTT-Broker und Adminer hinzugefügt
- `.env.example` - MQTT-Ports und HETZNER_TOKEN hinzugefügt
- `.gitignore` - Sicherheitserweiterungen
- `README.md` - Umfassende Dokumentationserweiterung

---

## Upgrade-Hinweise

### Voraussetzungen

1. **Hetzner DNS Token:** Für SSL-Zertifikate wird ein API-Token von dns.hetzner.com benötigt
2. **Docker:** Mosquitto-Service benötigt Docker Compose v2+

### Schnellstart MQTT

```bash
# 1. Umgebungsvariablen kopieren
cp .env.example .env

# 2. Services starten
docker compose up -d mosquitto

# 3. SSL-Zertifikate einrichten (optional)
sudo ./scripts/complete-ssl-setup.sh --staging  # Zum Testen
sudo ./scripts/complete-ssl-setup.sh --production  # Für Produktion
```

### Schnellstart Adminer

```bash
# Services starten
docker compose up -d adminer

# Zugriff über Browser
# http://localhost:8081
# Server: db, Benutzer: siehe .env
```

---

## Mitwirkende

Diese Version wurde mit Unterstützung von Claude Code (Anthropic) entwickelt.

---

*Generiert am 26. Dezember 2025*
