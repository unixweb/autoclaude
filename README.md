# Docker Compose Multi-Container Umgebung

Eine vollständige Docker Compose Konfiguration mit Web-Server, PostgreSQL-Datenbank, Mailhog Email-Testing, Adminer Datenbank-Administration, **Eclipse Mosquitto MQTT Broker mit SSL/TLS-Verschlüsselung** und **MQTT Management Dashboard**.

## 📋 Inhaltsverzeichnis

- [Übersicht](#übersicht)
- [Dienste](#dienste)
- [Neue Features](#neue-features)
- [Schnellstart](#schnellstart)
- [MQTT Broker Setup](#mqtt-broker-setup)
- [MQTT Dashboard](#mqtt-dashboard)
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
- **🆕 MQTT Dashboard** Web-basierte Broker-Verwaltung
- **🆕 Automatische SSL-Zertifikate** via Let's Encrypt

## 🚀 Dienste

| Service | Beschreibung | Port(s) | Web-UI |
|---------|-------------|---------|--------|
| **web** | Nginx Web-Server | 8080 | http://localhost:8080 |
| **db** | PostgreSQL 15 Datenbank | 5432 (intern) | - |
| **mailhog** | E-Mail Testing | 1025 (SMTP), 8025 (UI) | http://localhost:8025 |
| **adminer** | Datenbank-Admin | 8081 | http://localhost:8081 |
| **🆕 mosquitto** | MQTT Broker | 1883, 8883, 9001, 8084 | - |
| **🆕 mqtt-dashboard** | MQTT Management Dashboard | 8082 | http://localhost:8082 |

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

## 📊 MQTT Dashboard

### Übersicht

Das **MQTT Dashboard** ist eine moderne, web-basierte Verwaltungsoberfläche für den Mosquitto MQTT Broker. Es bietet Echtzeit-Monitoring, Topic-Management und Message-Publishing über eine intuitive grafische Benutzeroberfläche.

**Technologie-Stack:**
- 🎨 **Frontend:** Vue.js 3 mit Vite und Tailwind CSS
- 🔧 **Backend:** Python Flask mit Flask-SocketIO
- 🔌 **MQTT Client:** paho-mqtt (Python)
- ⚡ **Real-Time:** WebSocket-basierte Live-Updates
- 🐳 **Deployment:** Docker Multi-Stage Build

### Zugriff

```
URL: http://localhost:8082
Port: 8082 (konfigurierbar via MQTT_DASHBOARD_PORT)
```

Das Dashboard startet automatisch mit `docker compose up -d` und benötigt einen laufenden Mosquitto Broker.

### Features

#### 1. 📈 Broker Overview
**Echtzeit-Statistiken und Broker-Status:**
- Broker-Version und Uptime
- Verbundene Clients (aktuell, maximum, gesamt)
- Message Throughput (Nachrichten/Minute)
- Bytes Transferiert (Sent/Received)
- Subscriptions und Retained Messages
- Broker Load (1min, 5min, 15min)
- Heap Memory Nutzung
- Live Performance Charts

**Screenshots-Metriken:**
- Broker Health mit Kapazitätsanzeige
- Client Statistiken mit Trends
- Message Throughput (empfangen/gesendet)
- Datenübertragung (Bytes)
- Broker Load und Memory

#### 2. 👥 Connected Clients
**Client-Monitoring:**
- Liste verbundener Clients
- Gesamtanzahl (connected, disconnected, total)
- Peak Connections Tracking
- Connection Activity Rates (1min, 5min, 15min)
- Expired Sessions Anzeige
- Echtzeit-Updates via WebSocket
- Such- und Filterfunktion

**Client-Kategorien:**
- ✅ Connected: Aktuell verbundene Clients
- ❌ Disconnected: Getrennte Clients (persistent sessions)
- ⏱️ Expired: Abgelaufene Sessions
- 📊 Total: Gesamtzahl getrackte Clients

#### 3. 📂 Topics Explorer
**Topic-Management und Monitoring:**
- Liste aller aktiven Topics
- Message Count pro Topic
- Last Activity Timestamp
- QoS Badge (0, 1, 2)
- Retained Message Indicator
- Such- und Filterfunktion (MQTT Wildcards unterstützt)
- Live-Subscription zu Topics
- JSON Payload Formatierung
- Message History anzeigen

**Topic-Filter:**
- `#` - Multi-level Wildcard (alle Subtopics)
- `+` - Single-level Wildcard (eine Ebene)
- Prefix-Filter für schnelle Suche
- Case-sensitive Matching

#### 4. 📤 Message Publisher
**MQTT Messages senden:**
- Topic-Eingabe mit Validierung
- Payload Editor mit Text/JSON Modus
- QoS Selector (0, 1, 2)
- Retain Flag Toggle
- JSON Templates (Object, Array, Sensor Data)
- JSON Formatierung und Minification
- JSON Validierung mit Fehleranzeige
- Success/Error Feedback

**Einschränkungen:**
- ❌ Keine Wildcards (`#`, `+`) im Topic erlaubt
- ❌ Keine `$SYS` Topics publishbar
- ✅ Maximale Payload-Größe: 256KB

#### 5. 🔍 Live Monitor
**Echtzeit Message Feed:**
- Multi-Topic Subscription Management
- Live Message Feed mit Topic, Payload, Timestamp
- Pause/Resume Funktion
- Clear Message History
- Message Count Indicator
- Expandable Message Details
- JSON Payload Formatierung
- Preset Topic Subscriptions:
  - All Topics (`#`)
  - System Topics (`$SYS/#`)
  - All Sensors (`sensors/#`)
  - Room Temperatures (`sensors/+/temperature`)
- Wildcard Pattern Matching
- Per-Subscription Message Counts

**Features:**
- ⏸️ Pause/Resume für Message Feed
- 🗑️ Clear History Button
- 📊 Message Count Tracking
- 🔍 Expandable Payloads (Click to expand/collapse)
- 🎨 Topic Badge Color Coding
- 📈 Message Limit (500 max)

#### 6. ⚙️ Settings
**Broker-Konfiguration anzeigen:**
- Connection Details (Host, Port, Protocol)
- Listener Configuration
- Persistence Settings
- Security Settings (TLS/SSL, Authentication)
- Connection Test Button
- Real-Time Status Updates

**Hinweis:** Konfigurationsänderungen erfolgen über `mosquitto/config/mosquitto.conf` (read-only im Dashboard).

### Installation & Startup

#### Schritt 1: Umgebungsvariablen konfigurieren

```bash
# .env Datei bearbeiten
nano .env
```

**Dashboard-spezifische Variablen:**
```bash
# Dashboard Port
MQTT_DASHBOARD_PORT=8082

# Flask Konfiguration (Development)
FLASK_ENV=development
FLASK_DEBUG=1

# MQTT Broker Connection
MQTT_BROKER_HOST=mosquitto
MQTT_BROKER_PORT=1883
MQTT_CLIENT_ID=mqtt-dashboard
MQTT_KEEPALIVE=60

# Optional: MQTT Authentifizierung
MQTT_USERNAME=
MQTT_PASSWORD=

# Optional: TLS/SSL
MQTT_USE_TLS=false
MQTT_TLS_INSECURE=false

# WebSocket Backend (eventlet für Production)
SOCKETIO_ASYNC_MODE=threading
```

#### Schritt 2: Dashboard starten

```bash
# Alle Services inkl. Dashboard starten
docker compose up -d

# Nur Dashboard neu starten
docker compose restart mqtt-dashboard

# Dashboard Logs anzeigen
docker compose logs -f mqtt-dashboard
```

#### Schritt 3: Dashboard aufrufen

```
Öffne Browser: http://localhost:8082
```

**Erwartete Ausgabe (Logs):**
```
mqtt-dashboard | ========================================
mqtt-dashboard | Starting MQTT Dashboard...
mqtt-dashboard | ========================================
mqtt-dashboard | Configuration:
mqtt-dashboard | - Flask Environment: development
mqtt-dashboard | - MQTT Broker: mosquitto:1883
mqtt-dashboard | - MQTT Client ID: mqtt-dashboard
mqtt-dashboard | - Authentication: Disabled
mqtt-dashboard | - TLS/SSL: Disabled
mqtt-dashboard | - SocketIO Mode: threading
mqtt-dashboard | ========================================
mqtt-dashboard | Waiting for MQTT broker to be ready...
mqtt-dashboard | Successfully connected to mosquitto:1883
mqtt-dashboard | ========================================
mqtt-dashboard | Starting Gunicorn server...
mqtt-dashboard | [INFO] Listening at: http://0.0.0.0:5000
```

### API Dokumentation

Das Dashboard bietet eine vollständige REST API und WebSocket-Schnittstelle.

#### REST API Endpoints

**Broker Status & Statistiken:**
```bash
# Health Check
GET /health
Response: {"status": "healthy", "mqtt_connected": true}

# Broker Status
GET /api/broker/status
Response: {"connected": true, "host": "mosquitto", "port": 1883}

# Broker Statistiken (vollständig)
GET /api/broker/stats
Response: {
  "version": "2.0.22",
  "uptime": 3600,
  "clients": {"connected": 5, "maximum": 10, "total": 15},
  "messages": {"received": 1000, "sent": 950},
  ...
}

# Broker Statistiken (Summary)
GET /api/broker/stats/summary
Response: {"version": "2.0.22", "uptime": "1 hour", "clients": 5}

# Broker Version
GET /api/broker/version
Response: {"version": "mosquitto version 2.0.22", "uptime": "1 hour 23 minutes"}
```

**Client Monitoring:**
```bash
# Client-Liste (Kategorien)
GET /api/clients
Response: {
  "categories": {
    "connected": {"name": "Connected", "count": 5},
    "disconnected": {"name": "Disconnected", "count": 2}
  },
  "summary": {"connected": 5, "total": 15}
}

# Client Count
GET /api/clients/count
Response: {"connected": 5, "disconnected": 2, "total": 7, "maximum": 10}

# Active Clients
GET /api/clients/active
Response: {"active": 5, "connect_rate_1min": 0.5}

# Client Statistiken (detailliert)
GET /api/clients/stats
Response: {...}
```

**Topic Management:**
```bash
# Active Topics
GET /api/topics?filter=sensors/*&limit=50
Response: {
  "topics": [
    {
      "topic": "sensors/temp/living_room",
      "message_count": 150,
      "last_seen": "2026-01-02T21:30:00Z",
      "qos": 1,
      "retained": false
    }
  ],
  "count": 1
}

# Topic Details
GET /api/topics/{topic_name}
Response: {...}

# Topic Count
GET /api/topics/count
Response: {"count": 42}

# Topic Summary
GET /api/topics/summary
Response: [{"topic": "...", "message_count": 10}]
```

**Message Publishing:**
```bash
# Publish Message
POST /api/messages/publish
Content-Type: application/json

Request Body:
{
  "topic": "sensors/temp/bedroom",
  "payload": "{\"temperature\": 22.5, \"humidity\": 45}",
  "qos": 1,
  "retain": false
}

Response: {
  "success": true,
  "message": "Message published successfully",
  "topic": "sensors/temp/bedroom"
}
```

#### WebSocket Events

**Verbindung:**
```javascript
// Socket.IO Client
import io from 'socket.io-client';
const socket = io('http://localhost:8082');

socket.on('connect', () => {
  console.log('Connected to MQTT Dashboard');
});
```

**Event Handlers:**

```javascript
// Subscribe to metric channel
socket.emit('subscribe', 'broker_stats');

// Available channels:
// - broker_stats: Vollständige Broker-Statistiken (alle 5s)
// - broker_summary: Leichtgewichtige Summary
// - clients: Client-Statistiken
// - messages: Message-Metriken
// - bytes: Bytes Transferred
// - load: Broker Load Metriken

// Receive broker stats
socket.on('broker_stats', (data) => {
  console.log('Broker Stats:', data);
});

// Unsubscribe from channel
socket.emit('unsubscribe', 'broker_stats');

// Get list of available channels
socket.emit('get_channels', (channels) => {
  console.log('Available channels:', channels);
});

// Test broker connection
socket.emit('ping_broker', (response) => {
  console.log('Broker ping:', response);
});
```

**Topic Subscriptions:**

```javascript
// Subscribe to MQTT topic
socket.emit('subscribe_topic', 'sensors/+/temperature');

// Receive messages from subscribed topics
socket.on('topic_message', (data) => {
  console.log('Topic:', data.topic);
  console.log('Payload:', data.payload);
  console.log('QoS:', data.qos);
  console.log('Retained:', data.retained);
  console.log('Timestamp:', data.timestamp);
});

// Unsubscribe from topic
socket.emit('unsubscribe_topic', 'sensors/+/temperature');

// Get active topic subscriptions
socket.emit('get_topic_subscriptions', (topics) => {
  console.log('Subscribed topics:', topics);
});
```

### Konfiguration

#### Umgebungsvariablen (.env)

```bash
# ============================================
# MQTT Dashboard Configuration
# ============================================

# Dashboard Port (Standard: 8082)
MQTT_DASHBOARD_PORT=8082

# Flask Application Settings
FLASK_ENV=development           # Options: development, production
FLASK_DEBUG=1                   # 0 = disabled, 1 = enabled (nur development!)

# MQTT Broker Connection
MQTT_BROKER_HOST=mosquitto      # Hostname des MQTT Brokers
MQTT_BROKER_PORT=1883           # MQTT Port (1883 unencrypted, 8883 TLS)
MQTT_CLIENT_ID=mqtt-dashboard   # Eindeutige Client-ID
MQTT_KEEPALIVE=60               # Keep-alive interval in seconds

# Optional: MQTT Authentication
MQTT_USERNAME=                  # MQTT Username (leer = keine Auth)
MQTT_PASSWORD=                  # MQTT Password (leer = keine Auth)

# Optional: TLS/SSL Configuration
MQTT_USE_TLS=false              # true = TLS aktivieren, false = deaktiviert
MQTT_TLS_INSECURE=false         # true = Zertifikat nicht validieren (nur Development!)

# WebSocket Backend
SOCKETIO_ASYNC_MODE=threading   # Options: threading, eventlet
                                # threading = Development
                                # eventlet = Production (bessere Performance)
```

**Wichtig für Production:**
```bash
FLASK_ENV=production
FLASK_DEBUG=0
MQTT_USE_TLS=true
MQTT_TLS_INSECURE=false
MQTT_USERNAME=admin
MQTT_PASSWORD=CHANGE_ME_TO_SECURE_PASSWORD
SOCKETIO_ASYNC_MODE=eventlet
```

#### Docker Compose Konfiguration

```yaml
mqtt-dashboard:
  build:
    context: ./mqtt-dashboard
    dockerfile: Dockerfile
  container_name: app_mqtt_dashboard
  restart: unless-stopped

  ports:
    - "${MQTT_DASHBOARD_PORT:-8082}:5000"

  environment:
    FLASK_ENV: ${FLASK_ENV:-production}
    FLASK_DEBUG: ${FLASK_DEBUG:-0}
    MQTT_BROKER_HOST: ${MQTT_BROKER_HOST:-mosquitto}
    MQTT_BROKER_PORT: ${MQTT_BROKER_PORT:-1883}
    MQTT_CLIENT_ID: ${MQTT_CLIENT_ID:-mqtt-dashboard}
    MQTT_KEEPALIVE: ${MQTT_KEEPALIVE:-60}
    MQTT_USERNAME: ${MQTT_USERNAME:-}
    MQTT_PASSWORD: ${MQTT_PASSWORD:-}
    MQTT_USE_TLS: ${MQTT_USE_TLS:-false}
    MQTT_TLS_INSECURE: ${MQTT_TLS_INSECURE:-false}
    SOCKETIO_ASYNC_MODE: ${SOCKETIO_ASYNC_MODE:-eventlet}

  depends_on:
    mosquitto:
      condition: service_healthy

  networks:
    - app_network

  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 20s
```

### Development Setup

#### Lokale Entwicklung (ohne Docker)

**Backend:**
```bash
cd mqtt-dashboard/backend

# Virtual Environment erstellen
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# oder
venv\Scripts\activate     # Windows

# Dependencies installieren
pip install -r requirements.txt

# Environment Variables setzen
export FLASK_ENV=development
export FLASK_DEBUG=1
export MQTT_BROKER_HOST=localhost
export MQTT_BROKER_PORT=1883

# Flask Server starten
python -m app.main
```

**Frontend:**
```bash
cd mqtt-dashboard/frontend

# Dependencies installieren
npm install

# Dev Server starten
npm run dev

# Build für Production
npm run build
```

**URLs (Development):**
- Frontend: http://localhost:5173 (Vite Dev Server)
- Backend API: http://localhost:5000
- WebSocket: ws://localhost:5000/socket.io

### Troubleshooting

#### Problem: Dashboard zeigt "Broker Disconnected"

**Symptom:**
```
Dashboard UI: "Broker: Offline"
API Response: {"connected": false}
```

**Lösung:**
```bash
# 1. Mosquitto Status prüfen
docker compose ps mosquitto
# Sollte zeigen: "healthy"

# 2. Dashboard Logs prüfen
docker compose logs mqtt-dashboard
# Suche nach: "Failed to connect to MQTT broker"

# 3. MQTT Broker Connection testen
docker exec app_mqtt_dashboard curl -f http://localhost:5000/api/broker/status

# 4. Environment Variables prüfen
docker compose exec mqtt-dashboard env | grep MQTT_

# 5. Dashboard neu starten
docker compose restart mqtt-dashboard
```

**Häufige Ursachen:**
- ❌ Mosquitto Container nicht gestartet
- ❌ Falsche `MQTT_BROKER_HOST` (sollte `mosquitto` sein)
- ❌ Falscher `MQTT_BROKER_PORT` (1883 oder 8883)
- ❌ Authentifizierung aktiviert, aber keine Credentials
- ❌ TLS aktiviert, aber Zertifikate fehlen

#### Problem: WebSocket Verbindung fehlgeschlagen

**Symptom:**
```
Browser Console: "WebSocket connection to 'ws://localhost:8082' failed"
Dashboard: Keine Echtzeit-Updates
```

**Lösung:**
```bash
# 1. Browser Console öffnen und prüfen
# Chrome/Firefox: F12 -> Console

# 2. WebSocket Endpoint testen
curl -i http://localhost:8082/socket.io/

# 3. CORS-Fehler?
# Prüfe ob Frontend und Backend auf gleicher Origin laufen

# 4. Container Logs prüfen
docker compose logs -f mqtt-dashboard | grep -i websocket

# 5. Firewall/Proxy-Probleme?
# Prüfe ob Port 8082 erreichbar ist
telnet localhost 8082
```

**Lösung:**
```bash
# WebSocket-Modus auf eventlet umstellen (.env)
SOCKETIO_ASYNC_MODE=eventlet

# Dashboard neu starten
docker compose restart mqtt-dashboard
```

#### Problem: "No module named 'app'" beim Start

**Symptom:**
```
ModuleNotFoundError: No module named 'app'
```

**Lösung:**
```bash
# 1. Dockerfile neu bauen
docker compose build mqtt-dashboard

# 2. Container neu starten
docker compose up -d mqtt-dashboard

# 3. Falls immer noch Fehler:
# Alte Images entfernen und neu bauen
docker compose down
docker rmi $(docker images 'claude-mqtt-dashboard' -q)
docker compose up -d --build
```

#### Problem: Dashboard lädt langsam oder zeigt leere Daten

**Symptom:**
- Dashboard UI zeigt "Loading..." dauerhaft
- API Endpoints returnen `503 Service Unavailable`
- Metriken zeigen `0` oder `null`

**Ursache:**
```
SysMonitor oder TopicTracker nicht gestartet/subscribed
```

**Lösung:**
```bash
# 1. Backend Logs prüfen
docker compose logs mqtt-dashboard | grep -i "sys_monitor\|topic_tracker"

# Sollte zeigen:
# "Successfully subscribed to $SYS/#"
# "Successfully subscribed to # (all topics)"

# 2. API Status prüfen
curl http://localhost:8082/api/broker/status

# Response sollte enthalten:
# "sys_monitor_subscribed": true

# 3. Manuell reconnecten
docker compose restart mqtt-dashboard

# 4. Mosquitto $SYS Topics prüfen
docker exec app_mosquitto mosquitto_sub -h localhost -p 1883 -t '$SYS/#' -C 5
```

#### Problem: Charts werden nicht angezeigt

**Symptom:**
- Performance Trends Section leer
- "Waiting for data..." dauerhaft

**Lösung:**
```bash
# Charts benötigen Zeit zum Sammeln von Datenpunkten
# Warte mindestens 30 Sekunden nach Dashboard-Start

# 1. Browser Console öffnen
# Prüfe auf JavaScript Fehler

# 2. WebSocket Subscription prüfen
# Console sollte zeigen: "Subscribed to broker_stats"

# 3. Browser Cache leeren
# Chrome: Ctrl+Shift+Del
# Firefox: Ctrl+Shift+Del

# 4. Hard Reload
# Chrome/Firefox: Ctrl+Shift+R
```

#### Problem: "Permission denied" bei Zertifikaten

**Symptom:**
```
Error: SSL/TLS connection failed
Permission denied: /mosquitto/certs/...
```

**Lösung:**
```bash
# Zertifikats-Berechtigungen korrigieren
chmod 644 mosquitto/certs/*.crt
chmod 644 mosquitto/certs/*.key

# Dashboard mit TLS-Support neu starten
docker compose restart mqtt-dashboard
```

### Performance Optimierung

**Empfehlungen für Production:**

```bash
# 1. WebSocket Backend auf eventlet umstellen
SOCKETIO_ASYNC_MODE=eventlet

# 2. Flask Debug Mode deaktivieren
FLASK_ENV=production
FLASK_DEBUG=0

# 3. Frontend Build optimieren
cd mqtt-dashboard/frontend
npm run build  # Bereits im Dockerfile

# 4. Gunicorn Worker anpassen (wsgi.py)
# Derzeit: 1 Worker, 4 Threads
# Für bessere Performance: 2-4 Worker
gunicorn --workers 4 --threads 2 --bind 0.0.0.0:5000 ...
```

**Resource Limits:**
```yaml
# docker-compose.yml
mqtt-dashboard:
  # ...
  deploy:
    resources:
      limits:
        cpus: '1.0'
        memory: 512M
      reservations:
        cpus: '0.5'
        memory: 256M
```

### Sicherheitshinweise

**Production Checklist:**

- [ ] `FLASK_ENV=production` und `FLASK_DEBUG=0`
- [ ] MQTT Authentifizierung aktiviert (`MQTT_USERNAME`, `MQTT_PASSWORD`)
- [ ] TLS/SSL aktiviert (`MQTT_USE_TLS=true`)
- [ ] Starke Passwörter verwenden
- [ ] Dashboard nur im internen Netzwerk zugänglich
- [ ] Reverse Proxy (nginx) mit HTTPS verwenden
- [ ] Rate Limiting für API Endpoints
- [ ] WebSocket CORS korrekt konfigurieren

**Reverse Proxy Beispiel (nginx):**
```nginx
server {
    listen 443 ssl;
    server_name mqtt-dashboard.example.com;

    ssl_certificate /etc/ssl/certs/dashboard.crt;
    ssl_certificate_key /etc/ssl/private/dashboard.key;

    location / {
        proxy_pass http://localhost:8082;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Weitere Informationen

**Projekt-Struktur:**
```
mqtt-dashboard/
├── backend/
│   ├── app/
│   │   ├── __init__.py           # Flask app factory
│   │   ├── main.py               # Application entry point
│   │   ├── config.py             # Configuration
│   │   ├── mqtt_client.py        # MQTT client wrapper
│   │   ├── websocket.py          # Flask-SocketIO handlers
│   │   ├── routes/               # API blueprints
│   │   ├── services/             # Business logic
│   │   └── models/               # Data models
│   ├── tests/                    # Unit tests
│   ├── requirements.txt          # Python dependencies
│   └── wsgi.py                   # Gunicorn entry point
├── frontend/
│   ├── src/
│   │   ├── main.js               # Vue.js entry point
│   │   ├── App.vue               # Root component
│   │   ├── router/               # Vue Router
│   │   ├── api/                  # API client
│   │   ├── components/           # Reusable components
│   │   ├── views/                # Page components
│   │   └── assets/               # CSS, images
│   ├── package.json              # Node.js dependencies
│   └── vite.config.js            # Vite configuration
├── Dockerfile                     # Multi-stage build
├── docker-entrypoint.sh          # Container startup script
└── README.md                      # Dashboard documentation
```

**Links:**
- [Vue.js Dokumentation](https://vuejs.org/)
- [Flask Dokumentation](https://flask.palletsprojects.com/)
- [Flask-SocketIO Dokumentation](https://flask-socketio.readthedocs.io/)
- [paho-mqtt Python Client](https://www.eclipse.org/paho/index.php?page=clients/python/index.php)
- [Tailwind CSS Dokumentation](https://tailwindcss.com/)

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

### Version 2.1 (Januar 2026)

**Neue Features:**
- ✨ **MQTT Dashboard** - Web-basierte Broker-Verwaltung
  - Vue.js 3 + Python Flask Stack
  - Echtzeit-Monitoring via WebSocket
  - 6 Dashboard-Views (Overview, Clients, Topics, Publish, Monitor, Settings)
  - REST API + WebSocket Interface
  - Docker Multi-Stage Build
- ✨ Performance Charts (Message Throughput, Client Connections)
- ✨ Live Topic Explorer mit Message History
- ✨ Message Publisher mit JSON Editor
- ✨ Real-Time Message Monitor mit Subscriptions
- ✨ Comprehensive Unit Tests (40+ tests, 87%+ coverage)

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
