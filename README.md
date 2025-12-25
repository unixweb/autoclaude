# Docker Compose Multi-Container Umgebung

Eine vollständige Docker Compose Konfiguration mit Web-Server, PostgreSQL-Datenbank, Mailhog Email-Testing, Adminer Datenbank-Administration und **Eclipse Mosquitto MQTT Broker mit SSL/TLS-Verschlüsselung**.

## 📋 Inhaltsverzeichnis

- [Übersicht](#übersicht)
- [Dienste](#dienste)
- [Neue Features](#neue-features)
- [Schnellstart](#schnellstart)
- [MQTT Broker Setup](#mqtt-broker-setup)
- [SSL/TLS Zertifikate](#ssltls-zertifikate)
- [Scripts Dokumentation](#scripts-dokumentation)
- [Automatische Zertifikatserneuerung](#automatische-zertifikatserneuerung)
- [Konfiguration](#konfiguration)
- [Testing](#testing)

## 🎯 Übersicht

Diese Docker Compose Umgebung bietet:
- **Web-Server** (nginx) auf Port 8080
- **PostgreSQL** Datenbank mit persistenter Speicherung
- **Mailhog** für E-Mail Testing (SMTP + Web-UI)
- **Adminer** für Datenbank-Verwaltung
- **🆕 Eclipse Mosquitto** MQTT Broker mit SSL/TLS
- **🆕 Automatische SSL-Zertifikate** via Let's Encrypt

## 🚀 Dienste

| Service | Beschreibung | Port(s) | Web-UI |
|---------|-------------|---------|--------|
| **web** | Nginx Web-Server | 8080 | http://localhost:8080 |
| **db** | PostgreSQL 15 Datenbank | 5432 (intern) | - |
| **mailhog** | E-Mail Testing | 1025 (SMTP), 8025 (UI) | http://localhost:8025 |
| **adminer** | Datenbank-Admin | 8081 | http://localhost:8081 |
| **🆕 mosquitto** | MQTT Broker | 1883, 8883, 9001, 8084 | - |

## 🆕 Neue Features

### Eclipse Mosquitto MQTT Broker

Der MQTT Broker unterstützt folgende Protokolle und Ports:

| Port | Protokoll | Verschlüsselung | Verwendung |
|------|-----------|----------------|------------|
| **1883** | MQTT | ❌ Keine | Lokale Entwicklung, interne Netzwerke |
| **8883** | MQTT | ✅ TLS 1.2 | Sichere externe Verbindungen |
| **9001** | WebSocket | ❌ Keine | Browser-basierte Clients (Development) |
| **8084** | WebSocket | ✅ TLS 1.2 | Sichere Browser-Clients (Production) |

**Features:**
- ✅ Automatische SSL/TLS-Zertifikate via Let's Encrypt
- ✅ DNS-01 Challenge mit Hetzner Cloud DNS
- ✅ Automatische Erneuerung (60 Tage vor Ablauf)
- ✅ Persistente Daten und Logs
- ✅ Health Checks
- ✅ Anonymous Authentication (konfigurierbar)

### SSL/TLS Management

**Automatisierte Zertifikatsverwaltung:**
- 🔐 Let's Encrypt Zertifikate für alle Domains
- 🔄 Automatische Erneuerung alle 60 Tage
- 🛡️ TLS 1.2 Verschlüsselung
- 📦 Integration mit acme.sh
- ☁️ DNS-01 Challenge via Hetzner Cloud DNS API

## 🏁 Schnellstart

### 1. Voraussetzungen

```bash
# Docker und Docker Compose
docker --version
docker compose version

# Git Repository klonen (falls noch nicht geschehen)
git clone <repository-url>
cd claude
```

### 2. Umgebungsvariablen konfigurieren

```bash
# .env Datei erstellen
cp .env.example .env

# .env bearbeiten und Werte anpassen
nano .env
```

**Wichtige Variablen:**
```bash
# PostgreSQL
POSTGRES_PASSWORD=CHANGE_ME_TO_SECURE_PASSWORD

# MQTT Ports (optional - Defaults sind OK)
MQTT_PORT=1883
MQTT_TLS_PORT=8883
MQTT_WS_PORT=9001
MQTT_WSS_PORT=8084

# Hetzner DNS Token (für SSL-Zertifikate)
HETZNER_TOKEN=CHANGE_ME_TO_HETZNER_API_TOKEN
```

### 3. Container starten

```bash
# Alle Container starten
docker compose up -d

# Status prüfen
docker compose ps

# Logs anzeigen
docker compose logs -f
```

## 🔐 MQTT Broker Setup

### Schritt 1: SSL Domain und Hetzner Cloud DNS Token einrichten

**SSL Domain konfigurieren:**

Die Domain für SSL-Zertifikate wird zentral in `~/.acme.sh/account.conf` konfiguriert:

```bash
# SSL Domain setzen (Standard: mqtt.unixweb.de)
echo "SSL_DOMAIN='mqtt.unixweb.de'" >> ~/.acme.sh/account.conf
```

**WICHTIG:** Wenn Sie eine andere Domain verwenden, müssen Sie auch die Zertifikatspfade in `mosquitto/config/mosquitto.conf` entsprechend anpassen.

**Hetzner Cloud DNS Token einrichten:**

1. Anmelden bei [Hetzner Cloud Console](https://console.hetzner.cloud/)
2. Navigieren zu: **Security → API Tokens → Generate API Token**
3. Token-Name: `acme-mqtt-ssl`
4. Berechtigungen: **Read & Write**
5. Token kopieren und in `~/.acme.sh/account.conf` speichern:

```bash
echo "SAVED_HETZNER_TOKEN='YOUR_TOKEN_HERE'" >> ~/.acme.sh/account.conf
```

### Schritt 2: DNS-Setup verifizieren

```bash
./scripts/verify-dns-setup.sh
```

**Erwartete Ausgabe:**
```
[OK] Token found in account.conf
[OK] Cloud DNS API: 1 zone(s) accessible
[OK] Zone 'unixweb.de' is accessible via Cloud DNS API
✓ READY: DNS setup is correct
```

### Schritt 3: SSL-Zertifikat erstellen

**Staging-Zertifikat (zum Testen):**
```bash
./scripts/issue-certificate.sh --staging
```

**Produktionszertifikat:**
```bash
./scripts/issue-certificate.sh --production
```

### Schritt 4: Zertifikate installieren

```bash
./scripts/install-mosquitto-certs.sh
```

**Das Script:**
- ✅ Kopiert Zertifikate von acme.sh nach mosquitto/certs/
- ✅ Setzt korrekte Berechtigungen (644 für alle Dateien)
- ✅ Konfiguriert automatische Erneuerung
- ✅ Verifiziert die Installation

### Schritt 5: Mosquitto Container starten

```bash
docker compose up -d mosquitto

# Logs prüfen
docker compose logs -f mosquitto
```

**Erfolgreiche Ausgabe:**
```
mosquitto  | Opening ipv4 listen socket on port 1883.
mosquitto  | Opening ipv4 listen socket on port 8883.
mosquitto  | Opening websockets listen socket on port 9001.
mosquitto  | Opening websockets listen socket on port 8084.
mosquitto  | mosquitto version 2.0.22 running
```

## 📜 Scripts Dokumentation

Alle Scripts befinden sich im `/scripts` Verzeichnis und verwenden die **Hetzner Cloud DNS API**.

### Core Scripts

#### `verify-dns-setup.sh`
Verifiziert die DNS-Konfiguration und Token-Zugriff.

```bash
# Verwendung
./scripts/verify-dns-setup.sh

# Mit spezifischem Token testen
./scripts/verify-dns-setup.sh --token YOUR_TOKEN
```

**Prüft:**
- ✅ HETZNER_TOKEN in account.conf
- ✅ Zugriff auf Hetzner Cloud DNS API
- ✅ Zone 'unixweb.de' ist zugänglich
- ✅ DNS-Plugin Kompatibilität (dns_hetznercloud)

#### `test-dns-token.sh`
Schnelltest eines Hetzner Cloud API Tokens.

```bash
# Token testen
./scripts/test-dns-token.sh YOUR_TOKEN_HERE
```

**Funktionen:**
- ✅ Validiert Token gegen Hetzner Cloud API
- ✅ Prüft Zugriff auf unixweb.de Zone
- ✅ Optional: Speichert Token in account.conf

#### `issue-certificate.sh`
Erstellt Let's Encrypt Zertifikate mit DNS-01 Challenge.

```bash
# Staging-Zertifikat (Testing)
./scripts/issue-certificate.sh --staging

# Produktions-Zertifikat
./scripts/issue-certificate.sh --production

# Zertifikat erneuern
./scripts/issue-certificate.sh --production --force
```

**Parameter:**
- `--staging`: Let's Encrypt Staging-Server (keine Rate Limits)
- `--production`: Produktions-Server (50 Zertifikate/Woche Limit)
- `--force`: Erneuert existierendes Zertifikat
- `--help`: Zeigt Hilfe an

#### `install-mosquitto-certs.sh`
Installiert acme.sh Zertifikate für Mosquitto Docker Container.

```bash
# Zertifikate installieren
./scripts/install-mosquitto-certs.sh

# Force Reinstallation
./scripts/install-mosquitto-certs.sh --force
```

**Was das Script tut:**
1. Liest SSL_DOMAIN aus `~/.acme.sh/account.conf` (Standard: mqtt.unixweb.de)
2. Kopiert Zertifikate von `~/.acme.sh/${SSL_DOMAIN}_ecc/` nach `mosquitto/certs/`
3. Setzt Berechtigungen auf 644 (lesbar für Container-User 1883)
4. Konfiguriert acme.sh Reload-Hook für automatische Updates
5. Verifiziert die Installation

#### `fetch-zones.sh`
Listet alle DNS-Zones aus Hetzner Cloud auf.

```bash
# Zones auflisten
./scripts/fetch-zones.sh

# JSON-Output
./scripts/fetch-zones.sh --json

# Mit spezifischem Token
./scripts/fetch-zones.sh --token YOUR_TOKEN
```

### Hilfs-Scripts

#### `install-acme.sh`
Installiert acme.sh Zertifikats-Manager (falls nicht vorhanden).

```bash
./scripts/install-acme.sh
```

#### `check-ssl-status.sh`
Umfassender Status-Check der SSL/TLS-Konfiguration.

```bash
./scripts/check-ssl-status.sh
```

**Prüft:**
- Mosquitto Installation
- DNS Token Status
- Zertifikats-Status (acme.sh)
- Installierte Zertifikate (/etc/mosquitto/certs/)
- Renewal-Konfiguration

## 🔄 Automatische Zertifikatserneuerung

### Wie funktioniert die Erneuerung?

**acme.sh Cron-Job (läuft täglich um 10:19 Uhr):**

```
┌─────────────────────────────────────────────────────┐
│ acme.sh --cron                                       │
├─────────────────────────────────────────────────────┤
│ 1. Prüft alle Zertifikate                          │
│ 2. Erneuert 60 Tage vor Ablauf                     │
│ 3. Kopiert neue Zertifikate                        │
│ 4. Führt Reload-Hook aus:                          │
│    docker compose restart mosquitto                 │
└─────────────────────────────────────────────────────┘
```

### Erneuerungs-Timeline

```
Zertifikat ausgestellt: Tag 0
                         ↓
Gültig für: 90 Tage     │
                         │
Erneuerung startet:     │ ← Tag 30 (60 Tage vor Ablauf)
                         │    acme.sh --cron erneuert
                         │
Zertifikat läuft ab:    │ ← Tag 90
                         ✗
```

### Manuelle Erneuerung (falls erforderlich)

```bash
# SSL Domain aus config lesen
SSL_DOMAIN=$(grep "^SSL_DOMAIN=" ~/.acme.sh/account.conf | cut -d"'" -f2)

# Zertifikat manuell erneuern
~/.acme.sh/acme.sh --renew -d "${SSL_DOMAIN:-mqtt.unixweb.de}" --ecc --force

# Container neu starten (erfolgt automatisch)
docker compose restart mosquitto
```

### Status der Erneuerung prüfen

```bash
# SSL Domain aus config lesen
SSL_DOMAIN=$(grep "^SSL_DOMAIN=" ~/.acme.sh/account.conf | cut -d"'" -f2)

# Nächster Erneuerungszeitpunkt
~/.acme.sh/acme.sh --info -d "${SSL_DOMAIN:-mqtt.unixweb.de}" | grep NextRenew

# Zertifikats-Ablaufdatum
openssl x509 -in mosquitto/certs/${SSL_DOMAIN:-mqtt.unixweb.de}.crt -noout -enddate

# Cron-Job überprüfen
crontab -l | grep acme
```

**Ausgabe:**
```
Le_NextRenewTimeStr=2026-02-22T12:45:21Z
notAfter=May 25 11:45:21 2026 GMT
19 10 * * * "/home/user/.acme.sh"/acme.sh --cron ...
```

### Wichtig: Container-Restart bei Erneuerung

**Ja, Mosquitto muss neu gestartet werden**, da es Zertifikate nur beim Start lädt.

- **Automatisch:** Reload-Hook startet Container automatisch
- **Downtime:** ~2 Sekunden
- **Auswirkung:** Bestehende MQTT-Verbindungen werden getrennt
- **Clients:** Sollten Auto-Reconnect implementieren

## ⚙️ Konfiguration

### Mosquitto Konfiguration

Datei: `mosquitto/config/mosquitto.conf`

**Wichtige Einstellungen:**

```conf
# Listener-Konfiguration
listener 1883         # MQTT unverschlüsselt
listener 8883         # MQTT mit TLS
listener 9001         # WebSocket unverschlüsselt
listener 8084         # WebSocket mit TLS

# TLS-Zertifikate (Listener 8883 und 8084)
cafile /mosquitto/certs/ca.crt
certfile /mosquitto/certs/mqtt.unixweb.de.crt
keyfile /mosquitto/certs/mqtt.unixweb.de.key
tls_version tlsv1.2

# Authentifizierung
allow_anonymous true  # Für Produktion auf false setzen

# Persistenz
persistence true
persistence_location /mosquitto/data/

# Logging
log_dest file /mosquitto/log/mosquitto.log
log_dest stdout
```

### Authentifizierung aktivieren (Produktion)

```bash
# Mosquitto Container shell öffnen
docker exec -it app_mosquitto sh

# Passwort-Datei erstellen
mosquitto_passwd -c /mosquitto/config/passwd username

# Weiteren Benutzer hinzufügen
mosquitto_passwd -b /mosquitto/config/passwd another_user password123
```

**mosquitto.conf anpassen:**
```conf
allow_anonymous false
password_file /mosquitto/config/passwd
```

**Container neu starten:**
```bash
docker compose restart mosquitto
```

### Docker Compose Konfiguration

**Mosquitto Service (docker-compose.yml):**

```yaml
mosquitto:
  image: eclipse-mosquitto:latest
  container_name: app_mosquitto
  restart: unless-stopped
  user: "1883:1883"  # Läuft als mosquitto user

  ports:
    - "${MQTT_PORT:-1883}:1883"       # MQTT
    - "${MQTT_TLS_PORT:-8883}:8883"   # MQTT TLS
    - "${MQTT_WS_PORT:-9001}:9001"    # WebSocket
    - "${MQTT_WSS_PORT:-8084}:8084"   # WebSocket TLS

  volumes:
    - ./mosquitto/config:/mosquitto/config:ro
    - ./mosquitto/certs:/mosquitto/certs:ro
    - mosquitto_data:/mosquitto/data
    - mosquitto_logs:/mosquitto/log

  networks:
    - app_network

  healthcheck:
    test: ["CMD-SHELL", "mosquitto_sub -t '$$SYS/#' -C 1 -i healthcheck -W 3 || exit 1"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 10s
```

## 🧪 Testing

### MQTT Verbindungen testen

#### 1. Unverschlüsselt (Port 1883)

```bash
# Terminal 1: Subscribe
docker exec -it app_mosquitto mosquitto_sub -h localhost -p 1883 -t test/topic -v

# Terminal 2: Publish
docker exec -it app_mosquitto mosquitto_pub -h localhost -p 1883 -t test/topic -m "Hello MQTT!"
```

#### 2. Mit TLS (Port 8883)

```bash
# Voraussetzung: mosquitto-clients auf Host installiert
sudo apt-get install mosquitto-clients

# Terminal 1: Subscribe mit TLS
mosquitto_sub -h mqtt.unixweb.de -p 8883 \
  --cafile mosquitto/certs/ca.crt \
  -t test/topic -v

# Terminal 2: Publish mit TLS
mosquitto_pub -h mqtt.unixweb.de -p 8883 \
  --cafile mosquitto/certs/ca.crt \
  -t test/topic -m "Hello Secure MQTT!"
```

#### 3. WebSocket (Port 9001)

**JavaScript (Browser Console):**
```javascript
// Benötigt: MQTT.js Library
var client = mqtt.connect('ws://localhost:9001');

client.on('connect', function() {
  console.log('Connected to MQTT broker!');
  client.subscribe('test/topic');
});

client.on('message', function(topic, message) {
  console.log('Received:', topic, message.toString());
});

// Nachricht senden
client.publish('test/topic', 'Hello from Browser!');
```

#### 4. WebSocket mit TLS (Port 8084)

**JavaScript (Browser Console):**
```javascript
var client = mqtt.connect('wss://mqtt.unixweb.de:8084');

client.on('connect', function() {
  console.log('Secure WebSocket connected!');
});
```

### Container Health Checks

```bash
# Alle Container-Status anzeigen
docker compose ps

# Sollte zeigen:
# mosquitto  healthy  "Up X minutes (healthy)"

# Logs überwachen
docker compose logs -f mosquitto

# Health Check manuell ausführen
docker exec app_mosquitto mosquitto_sub -t '$SYS/#' -C 1 -i healthcheck -W 3
```

### System-Topics abfragen

```bash
# Broker-Version
docker exec app_mosquitto mosquitto_sub -h localhost -p 1883 -t '$SYS/broker/version' -C 1

# Verbundene Clients
docker exec app_mosquitto mosquitto_sub -h localhost -p 1883 -t '$SYS/broker/clients/connected' -C 1

# Alle System-Informationen
docker exec app_mosquitto mosquitto_sub -h localhost -p 1883 -t '$SYS/#' -C 20
```

## 📊 Troubleshooting

### Problem: Zertifikats-Fehler

```
Error: Unable to load server key file
OpenSSL Error: Permission denied
```

**Lösung:**
```bash
# Berechtigungen korrigieren
chmod 644 mosquitto/certs/mqtt.unixweb.de.key
docker compose restart mosquitto
```

### Problem: DNS Token funktioniert nicht

```bash
# Token testen
./scripts/test-dns-token.sh YOUR_TOKEN

# DNS Setup verifizieren
./scripts/verify-dns-setup.sh
```

### Problem: Container startet nicht

```bash
# Logs prüfen
docker compose logs mosquitto

# Konfiguration testen
docker run --rm -v $(pwd)/mosquitto/config:/mosquitto/config:ro \
  eclipse-mosquitto:latest mosquitto -c /mosquitto/config/mosquitto.conf -v
```

### Problem: Verbindung fehlgeschlagen

```bash
# Ports prüfen
docker compose ps mosquitto
netstat -tulpn | grep -E '1883|8883|9001|8084'

# Firewall prüfen (falls aktiv)
sudo ufw status
sudo ufw allow 1883/tcp
sudo ufw allow 8883/tcp
sudo ufw allow 9001/tcp
sudo ufw allow 8084/tcp
```

## 🔐 Sicherheitshinweise

### Produktion Checklist

- [ ] `allow_anonymous false` in mosquitto.conf
- [ ] Passwort-Authentifizierung aktiviert
- [ ] ACL (Access Control List) konfiguriert
- [ ] Nur TLS-Ports (8883, 8084) extern verfügbar
- [ ] Firewall konfiguriert
- [ ] Starkes POSTGRES_PASSWORD gesetzt
- [ ] Hetzner Token sicher gespeichert
- [ ] Regelmäßige Backups der mosquitto_data

### ACL Beispiel (mosquitto/config/acl)

```conf
# Admin hat vollen Zugriff
user admin
topic readwrite #

# Normale User nur auf eigene Topics
pattern readwrite devices/%u/#
pattern read shared/#
```

## 📚 Weitere Ressourcen

### Dokumentation

- [Eclipse Mosquitto Docs](https://mosquitto.org/documentation/)
- [MQTT Protocol](http://mqtt.org/)
- [Let's Encrypt](https://letsencrypt.org/)
- [acme.sh GitHub](https://github.com/acmesh-official/acme.sh)
- [Hetzner Cloud DNS API](https://docs.hetzner.cloud/reference/cloud#dns)

### MQTT Clients

- **Command Line:** mosquitto-clients, mqtt-cli
- **Desktop:** MQTT Explorer, MQTT.fx
- **JavaScript:** mqtt.js, paho-mqtt
- **Python:** paho-mqtt
- **Node.js:** mqtt (npm)

## 📝 Changelog

### Version 2.0 (Dezember 2025)

**Neue Features:**
- ✨ Eclipse Mosquitto MQTT Broker hinzugefügt
- ✨ SSL/TLS Support mit Let's Encrypt
- ✨ Automatische Zertifikatserneuerung
- ✨ DNS-01 Challenge via Hetzner Cloud DNS
- ✨ WebSocket Support (unverschlüsselt + TLS)
- ✨ 10+ neue Management-Scripts

**Scripts:**
- `verify-dns-setup.sh` - DNS-Konfiguration verifizieren
- `test-dns-token.sh` - Hetzner API Token testen
- `issue-certificate.sh` - SSL-Zertifikate erstellen
- `install-mosquitto-certs.sh` - Zertifikate installieren
- `fetch-zones.sh` - DNS-Zones auflisten
- `check-ssl-status.sh` - SSL-Status prüfen

**Bugfixes:**
- 🐛 Alle Scripts auf Hetzner Cloud API migriert
- 🐛 mosquitto.conf Konfigurationsfehler behoben
- 🐛 Container-Berechtigungen korrigiert

### Version 1.0 (Initial)

- Web-Server (nginx)
- PostgreSQL Datenbank
- Mailhog E-Mail Testing
- Adminer Datenbank-Admin

## 📄 Lizenz

Dieses Projekt steht unter der MIT-Lizenz.

## 🤝 Support

Bei Fragen oder Problemen:
1. Logs prüfen: `docker compose logs`
2. Scripts ausführen: `./scripts/check-ssl-status.sh`
3. Dokumentation konsultieren

---

**Hinweis:** Dies ist eine Entwicklungsumgebung. Für Produktions-Deployments sollten zusätzliche Sicherheitsmaßnahmen implementiert werden.
