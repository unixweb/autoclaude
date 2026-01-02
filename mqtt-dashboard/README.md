# MQTT Dashboard

Web-basierte Verwaltungsoberfläche für Eclipse Mosquitto MQTT Broker mit Echtzeit-Monitoring, Topic-Explorer und Message-Publisher.

## 📋 Inhaltsverzeichnis

- [Übersicht](#übersicht)
- [Features](#features)
- [Architektur](#architektur)
- [Technologie-Stack](#technologie-stack)
- [Projektstruktur](#projektstruktur)
- [Schnellstart](#schnellstart)
- [Development Setup](#development-setup)
- [API Dokumentation](#api-dokumentation)
- [Konfiguration](#konfiguration)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

## 🎯 Übersicht

Das MQTT Dashboard ist eine vollständige Web-Anwendung zur Verwaltung und Überwachung von Eclipse Mosquitto MQTT Brokern. Es bietet eine intuitive grafische Oberfläche für Aufgaben, die sonst über die Kommandozeile oder durch Bearbeitung von Konfigurationsdateien durchgeführt werden müssten.

**Hauptfunktionen:**
- 📊 Echtzeit-Monitoring von Broker-Metriken (Clients, Messages, Bytes)
- 👥 Überwachung verbundener MQTT-Clients
- 🔍 Topic-Explorer mit Live-Message-Historie
- 📤 Message-Publisher mit JSON-Editor
- 📡 Live-Monitor mit Wildcard-Subscriptions
- ⚙️ Broker-Konfiguration und Connection-Testing
- 📈 Performance-Charts (Throughput, Connections)

## ✨ Features

### 1. Broker Overview
- Echtzeit-Statistiken zu Clients, Messages und Bytes
- Broker-Version und Uptime
- Performance-Charts (Message Throughput, Client Connections)
- Health-Status mit visuellen Indikatoren
- Load-Metriken (1min, 5min, 15min)

### 2. Client Monitoring
- Liste verbundener, disconnected und expired Clients
- Client Connection Rates (1min, 5min, 15min)
- Peak Connection Tracking
- Auto-Refresh mit WebSocket-Updates

### 3. Topic Explorer
- Übersicht aller aktiven Topics
- Message-Anzahl pro Topic
- Letzte Nachricht und Timestamp
- QoS und Retained-Status
- MQTT Wildcard-Filter (`#`, `+`)
- Live-Subscription zu einzelnen Topics
- JSON Payload Formatting

### 4. Message Publisher
- Publish zu beliebigen Topics
- JSON-Editor mit Syntax-Highlighting
- QoS-Auswahl (0, 1, 2)
- Retain-Flag
- JSON-Templates (Object, Array, Sensor Data)
- Topic-Validierung (keine Wildcards in $SYS Topics)

### 5. Live Monitor
- Echtzeit-Message-Feed für mehrere Topics gleichzeitig
- Preset-Subscriptions (All Topics, System Topics, Sensors)
- Pause/Resume Feed
- Message-Details expandable
- JSON Payload Detection und Formatting
- Message-Counter pro Subscription
- Wildcard-Support (`#`, `+`)

### 6. Settings
- Broker-Verbindungsdetails (Host, Port, Protocol)
- Connection-Test mit Live-Feedback
- Listener-Konfiguration
- Persistence-Settings
- Security-Einstellungen (TLS, Auth)

## 🏗️ Architektur

Das Dashboard verwendet eine moderne Client-Server-Architektur:

```
┌─────────────────────────────────────────────────────────────┐
│                     Browser (Client)                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Vue.js 3 Frontend                                   │    │
│  │  - Router (6 Views)                                  │    │
│  │  - Components (14+ reusable)                         │    │
│  │  - Tailwind CSS                                      │    │
│  │  - Chart.js                                          │    │
│  └─────────────────────────────────────────────────────┘    │
│           │                                    │              │
│      REST API                           WebSocket            │
│    (HTTP/HTTPS)                        (Socket.IO)           │
└───────────┼────────────────────────────────┼─────────────────┘
            │                                │
            ▼                                ▼
┌───────────────────────────────────────────────────────────┐
│              Flask Backend (Python)                        │
│  ┌──────────────────────────────────────────────────┐    │
│  │  Flask Application                                │    │
│  │  - Routes (4 blueprints)                          │    │
│  │  - Services (SysMonitor, TopicTracker, etc.)      │    │
│  │  - WebSocket Server (Flask-SocketIO)             │    │
│  └──────────────────────────────────────────────────┘    │
│           │                                                │
│      MQTT Client                                          │
│     (paho-mqtt)                                           │
└───────────┼───────────────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────────────────────────┐
│           Eclipse Mosquitto MQTT Broker                    │
│  - $SYS/# Topics (Broker Statistics)                      │
│  - User Topics (Application Messages)                     │
└───────────────────────────────────────────────────────────┘
```

**Komponenten:**

1. **Frontend (Vue.js 3)**
   - Single Page Application (SPA)
   - Vue Router für Navigation
   - Socket.IO Client für WebSocket
   - Axios für REST API Calls
   - Chart.js für Visualisierungen

2. **Backend (Flask)**
   - REST API Endpoints (15+)
   - WebSocket Server (Flask-SocketIO)
   - MQTT Client (paho-mqtt)
   - Services für Monitoring und Tracking

3. **MQTT Integration**
   - $SYS Topic Subscription (Broker Stats)
   - Wildcard Subscription (# für alle Topics)
   - Message Publishing
   - Dynamic Topic Subscriptions

## 🛠️ Technologie-Stack

### Frontend
| Technologie | Version | Verwendung |
|------------|---------|------------|
| **Vue.js** | 3.4.0+ | UI Framework |
| **Vue Router** | 4.2.0+ | Client-side Routing |
| **Vite** | 5.0.0+ | Build Tool & Dev Server |
| **Tailwind CSS** | 3.4.0+ | Styling Framework |
| **Socket.IO Client** | 4.7.0+ | WebSocket Client |
| **Axios** | 1.6.0+ | HTTP Client |
| **Chart.js** | 4.4.0+ | Datenvisualisierung |
| **Vue ChartJS** | 5.3.0+ | Chart.js Vue Wrapper |

### Backend
| Technologie | Version | Verwendung |
|------------|---------|------------|
| **Python** | 3.12+ | Runtime |
| **Flask** | 3.0.0+ | Web Framework |
| **Flask-SocketIO** | 5.3.0+ | WebSocket Server |
| **paho-mqtt** | 2.0.0+ | MQTT Client |
| **Eventlet** | 0.35.0+ | Async I/O für WebSockets |
| **Gunicorn** | 21.0.0+ | Production WSGI Server |
| **pytest** | 8.0.0+ | Unit Testing |

### Infrastruktur
- **Docker**: Multi-stage Build (Node.js + Python)
- **Docker Compose**: Orchestrierung mit Mosquitto
- **nginx**: Optional als Reverse Proxy

## 📁 Projektstruktur

```
mqtt-dashboard/
├── backend/
│   ├── app/
│   │   ├── __init__.py              # Flask App Factory
│   │   ├── main.py                  # Application Entry Point
│   │   ├── config.py                # Configuration Management
│   │   ├── mqtt_client.py           # MQTT Client Wrapper
│   │   ├── websocket.py             # WebSocket Event Handlers
│   │   ├── routes/
│   │   │   ├── __init__.py          # Blueprint Registry
│   │   │   ├── broker.py            # Broker API Endpoints
│   │   │   ├── clients.py           # Client Monitoring API
│   │   │   ├── topics.py            # Topic Management API
│   │   │   └── messages.py          # Message Publishing API
│   │   ├── services/
│   │   │   ├── sys_monitor.py       # $SYS Topic Monitor
│   │   │   ├── topic_tracker.py     # Active Topic Tracker
│   │   │   ├── client_monitor.py    # Client Statistics Service
│   │   │   └── subscription_manager.py  # Per-Client Subscriptions
│   │   └── models/
│   │       ├── broker_stats.py      # Broker Statistics Model
│   │       └── topic.py             # Topic Information Model
│   ├── tests/
│   │   ├── conftest.py              # Pytest Configuration
│   │   ├── test_broker_api.py       # Broker API Tests
│   │   └── test_mqtt_client.py      # MQTT Client Tests
│   ├── requirements.txt             # Python Dependencies
│   └── wsgi.py                      # Production Entry Point
│
├── frontend/
│   ├── src/
│   │   ├── main.js                  # Vue App Entry Point
│   │   ├── App.vue                  # Root Component
│   │   ├── router/
│   │   │   └── index.js             # Route Definitions
│   │   ├── layouts/
│   │   │   └── DashboardLayout.vue  # Main Layout
│   │   ├── views/
│   │   │   ├── Overview.vue         # Broker Overview Dashboard
│   │   │   ├── Clients.vue          # Client Monitoring View
│   │   │   ├── Topics.vue           # Topic Explorer View
│   │   │   ├── Publish.vue          # Message Publisher View
│   │   │   ├── Monitor.vue          # Live Monitor View
│   │   │   └── Settings.vue         # Settings View
│   │   ├── components/
│   │   │   ├── Sidebar.vue          # Navigation Sidebar
│   │   │   ├── Header.vue           # Top Header
│   │   │   ├── StatCard.vue         # Statistics Card
│   │   │   ├── BrokerHealth.vue     # Broker Health Widget
│   │   │   ├── ClientsTable.vue     # Clients Table
│   │   │   ├── TopicList.vue        # Topic List
│   │   │   ├── TopicSubscriber.vue  # Topic Subscription Modal
│   │   │   ├── MessagePublisher.vue # Message Publishing Form
│   │   │   ├── PayloadEditor.vue    # JSON Payload Editor
│   │   │   ├── MessageFeed.vue      # Live Message Feed
│   │   │   ├── SubscriptionManager.vue  # Subscription Management
│   │   │   ├── ConnectionInfo.vue   # Connection Details
│   │   │   ├── ThroughputChart.vue  # Message Throughput Chart
│   │   │   └── ConnectionsChart.vue # Client Connections Chart
│   │   ├── composables/
│   │   │   └── useChartData.js      # Chart Data Management
│   │   ├── api/
│   │   │   └── client.js            # API Client (REST + WebSocket)
│   │   └── assets/
│   │       └── main.css             # Tailwind Styles
│   ├── public/
│   │   └── index.html               # HTML Entry Point
│   ├── package.json                 # Node.js Dependencies
│   ├── vite.config.js               # Vite Configuration
│   ├── tailwind.config.js           # Tailwind Configuration
│   └── postcss.config.js            # PostCSS Configuration
│
├── Dockerfile                        # Multi-stage Build
├── .dockerignore                     # Docker Ignore Rules
├── docker-entrypoint.sh              # Container Startup Script
└── README.md                         # This File
```

## 🚀 Schnellstart

### Voraussetzungen

- Docker & Docker Compose
- Mosquitto MQTT Broker (läuft bereits)
- Ports: 8082 (Dashboard)

### Mit Docker Compose

```bash
# 1. Umgebungsvariablen konfigurieren (siehe Konfiguration)
cp ../.env.example ../.env
nano ../.env

# 2. Container starten (aus Haupt-Verzeichnis)
cd ..
docker compose up -d mqtt-dashboard

# 3. Dashboard öffnen
open http://localhost:8082
```

### Status prüfen

```bash
# Container Status
docker compose ps mqtt-dashboard

# Logs anzeigen
docker compose logs -f mqtt-dashboard

# Health Check
curl http://localhost:8082/health
```

**Erwartete Ausgabe:**
```json
{
  "status": "healthy",
  "mqtt_connected": true,
  "mqtt_broker": "mosquitto:1883",
  "websocket_clients": 0,
  "sys_monitor_subscribed": true,
  "topic_tracker_subscribed": true
}
```

## 💻 Development Setup

### Backend (Python)

```bash
cd backend

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

# Tests ausführen
pytest

# Code Coverage
pytest --cov=app --cov-report=html

# Flask Server starten
python -m app.main
```

**Backend läuft auf:** http://localhost:5000

### Frontend (Node.js)

```bash
cd frontend

# Dependencies installieren
npm install

# Dev Server starten (mit Hot Reload)
npm run dev

# Linting
npm run lint

# Production Build
npm run build

# Build Preview
npm run preview
```

**Frontend läuft auf:** http://localhost:5173

### Development URLs

| Service | URL | Beschreibung |
|---------|-----|--------------|
| Frontend Dev | http://localhost:5173 | Vite Dev Server |
| Backend API | http://localhost:5000 | Flask Development Server |
| WebSocket | ws://localhost:5000/socket.io | Socket.IO Endpoint |
| API Docs | http://localhost:5000/api | API Endpoint List |

### Entwicklungsworkflow

1. **Backend Changes:**
   ```bash
   # Code bearbeiten in backend/app/
   # Flask lädt automatisch neu (FLASK_DEBUG=1)
   # Tests ausführen
   pytest tests/test_*.py
   ```

2. **Frontend Changes:**
   ```bash
   # Code bearbeiten in frontend/src/
   # Vite aktualisiert Browser automatisch
   # Lint prüfen
   npm run lint
   ```

3. **Docker Build testen:**
   ```bash
   # Aus Haupt-Verzeichnis
   docker compose build mqtt-dashboard
   docker compose up -d mqtt-dashboard
   ```

## 📚 API Dokumentation

### REST API Endpoints

#### Broker API (`/api/broker`)

```bash
# Health Check
GET /health
Response: {
  "status": "healthy",
  "mqtt_connected": true,
  "mqtt_broker": "mosquitto:1883"
}

# Broker Status
GET /api/broker/status
Response: {
  "connected": true,
  "host": "mosquitto",
  "port": 1883,
  "sys_monitor_subscribed": true
}

# Broker Statistiken (vollständig)
GET /api/broker/stats
Response: {
  "version": "2.0.22",
  "uptime": 3600,
  "clients": {
    "connected": 5,
    "maximum": 10,
    "total": 15,
    "disconnected": 2,
    "expired": 1
  },
  "messages": {
    "received": 1000,
    "sent": 950,
    "received_1min": 50,
    "sent_1min": 48
  },
  "bytes": {
    "received": 102400,
    "sent": 98304
  },
  "subscriptions": {
    "count": 25
  },
  "load": {
    "messages_received_1min": 50.5,
    "messages_received_5min": 45.2,
    "messages_received_15min": 42.8
  }
}

# Broker Statistiken (Zusammenfassung)
GET /api/broker/stats/summary
Response: {
  "version": "2.0.22",
  "uptime": "1 hour",
  "clients_connected": 5,
  "messages_received": 1000,
  "messages_sent": 950
}

# Broker Version
GET /api/broker/version
Response: {
  "version": "mosquitto version 2.0.22",
  "uptime": "1 hour 23 minutes"
}
```

#### Client API (`/api/clients`)

```bash
# Client-Liste (Kategorien)
GET /api/clients
Response: {
  "categories": {
    "connected": {
      "name": "Connected",
      "description": "Currently connected clients",
      "count": 5
    },
    "disconnected": {
      "name": "Disconnected",
      "description": "Disconnected clients",
      "count": 2
    }
  },
  "summary": {
    "connected": 5,
    "total": 15,
    "disconnected": 2
  },
  "activity": {
    "connect_rate_1min": 0.5,
    "connect_rate_5min": 0.4
  }
}

# Client Count
GET /api/clients/count
Response: {
  "connected": 5,
  "disconnected": 2,
  "total": 7,
  "maximum": 10
}

# Active Clients
GET /api/clients/active
Response: {
  "active": 5,
  "connect_rate_1min": 0.5,
  "connect_rate_5min": 0.4,
  "connect_rate_15min": 0.35
}

# Client Statistiken (detailliert)
GET /api/clients/stats
Response: {
  "connected": 5,
  "disconnected": 2,
  "maximum": 10,
  "total": 15,
  "expired": 1,
  "connect_rate_1min": 0.5
}
```

#### Topic API (`/api/topics`)

```bash
# Active Topics (mit Filter)
GET /api/topics?filter=sensors/*&limit=50&include_inactive=false
Response: {
  "topics": [
    {
      "topic": "sensors/temp/living_room",
      "message_count": 150,
      "first_seen": "2026-01-02T20:00:00Z",
      "last_seen": "2026-01-02T21:30:00Z",
      "last_payload": "{\"temperature\": 22.5}",
      "qos": 1,
      "retained": false
    }
  ],
  "count": 1
}

# Query Parameters:
# - filter: MQTT wildcard pattern (+ wird zu ?, # wird zu *)
# - prefix: Topic prefix filter
# - limit: Max anzahl Topics (default: 100)
# - include_inactive: Auch inaktive Topics (default: false)

# Topic Details
GET /api/topics/{topic_name}
Response: {
  "topic": "sensors/temp/living_room",
  "message_count": 150,
  "first_seen": "2026-01-02T20:00:00Z",
  "last_seen": "2026-01-02T21:30:00Z",
  "last_payload": "{\"temperature\": 22.5}",
  "qos": 1,
  "retained": false
}

# Topic Count
GET /api/topics/count
Response: {
  "count": 42
}

# Topic Summary
GET /api/topics/summary
Response: [
  {
    "topic": "sensors/temp/living_room",
    "message_count": 150,
    "last_seen": "2026-01-02T21:30:00Z"
  }
]
```

#### Message API (`/api/messages`)

```bash
# Publish Message
POST /api/messages/publish
Content-Type: application/json

Request Body:
{
  "topic": "sensors/temp/bedroom",
  "payload": "{\"temperature\": 22.5, \"humidity\": 45}",
  "qos": 1,           // Optional: 0, 1, 2 (default: 0)
  "retain": false     // Optional: true, false (default: false)
}

Response (Success):
{
  "success": true,
  "message": "Message published successfully",
  "topic": "sensors/temp/bedroom",
  "qos": 1,
  "retained": false
}

Response (Error):
{
  "success": false,
  "error": "Topic cannot contain wildcards",
  "error_code": "invalid_topic"
}

# Error Codes:
# - missing_topic: Topic fehlt
# - missing_payload: Payload fehlt
# - invalid_topic: Topic ungültig (Wildcards oder $SYS)
# - invalid_qos: QoS ungültig (nicht 0, 1, 2)
# - invalid_retain: Retain ungültig (nicht boolean)
# - broker_disconnected: Broker nicht verbunden
# - publish_failed: Publish fehlgeschlagen
```

### WebSocket API (Socket.IO)

#### Connection

```javascript
import io from 'socket.io-client';

const socket = io('http://localhost:8082');

socket.on('connect', () => {
  console.log('Connected:', socket.id);
});

socket.on('disconnect', () => {
  console.log('Disconnected');
});
```

#### Events: Metric Channels

```javascript
// Subscribe to metric channel
socket.emit('subscribe', 'broker_stats');

// Available channels:
const channels = [
  'broker_stats',     // Vollständige Broker-Statistiken (alle 5s)
  'broker_summary',   // Leichtgewichtige Summary
  'clients',          // Client-Statistiken
  'messages',         // Message-Metriken
  'bytes',            // Bytes Transferred
  'load'              // Broker Load Metriken
];

// Receive broker stats
socket.on('broker_stats', (data) => {
  console.log('Broker Stats:', data);
  // data = { version, uptime, clients, messages, bytes, ... }
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
  // response = { connected: true, latency: 5 }
});
```

#### Events: Topic Subscriptions

```javascript
// Subscribe to MQTT topic (supports wildcards)
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
  // topics = ['sensors/+/temperature', 'home/#']
});
```

#### Broadcast Timing

- **Broker Stats:** Alle 5 Sekunden (konfigurierbar via `STATS_PUSH_INTERVAL`)
- **Topic Messages:** Sofort beim Empfang

## ⚙️ Konfiguration

### Umgebungsvariablen

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

### Production Settings

**Wichtige Änderungen für Production:**

```bash
FLASK_ENV=production
FLASK_DEBUG=0
MQTT_USE_TLS=true
MQTT_TLS_INSECURE=false
MQTT_USERNAME=dashboard_user
MQTT_PASSWORD=CHANGE_ME_TO_SECURE_PASSWORD
SOCKETIO_ASYNC_MODE=eventlet
```

### Backend Configuration (config.py)

```python
import os

class Config:
    """Flask application configuration"""

    # Flask Settings
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = os.getenv('FLASK_DEBUG', '0') == '1'

    # MQTT Broker Settings
    MQTT_BROKER_HOST = os.getenv('MQTT_BROKER_HOST', 'mosquitto')
    MQTT_BROKER_PORT = int(os.getenv('MQTT_BROKER_PORT', '1883'))
    MQTT_CLIENT_ID = os.getenv('MQTT_CLIENT_ID', 'mqtt-dashboard')
    MQTT_KEEPALIVE = int(os.getenv('MQTT_KEEPALIVE', '60'))

    # Optional: Authentication
    MQTT_USERNAME = os.getenv('MQTT_USERNAME')
    MQTT_PASSWORD = os.getenv('MQTT_PASSWORD')

    # Optional: TLS/SSL
    MQTT_USE_TLS = os.getenv('MQTT_USE_TLS', 'false').lower() == 'true'
    MQTT_TLS_INSECURE = os.getenv('MQTT_TLS_INSECURE', 'false').lower() == 'true'

    # WebSocket Settings
    SOCKETIO_ASYNC_MODE = os.getenv('SOCKETIO_ASYNC_MODE', 'threading')
```

### Frontend Configuration (vite.config.js)

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      },
      '/socket.io': {
        target: 'http://localhost:5000',
        ws: true
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    emptyOutDir: true
  }
})
```

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Alle Tests ausführen
pytest

# Mit Output
pytest -v

# Specific Test-Datei
pytest tests/test_broker_api.py

# Coverage Report
pytest --cov=app --cov-report=html
# Öffne htmlcov/index.html im Browser

# Coverage Terminal
pytest --cov=app --cov-report=term-missing
```

**Test Coverage:**
- `app/mqtt_client.py`: 87%
- `app/routes/broker.py`: 96%
- `app/models/broker_stats.py`: 100%
- `app/config.py`: 90%

### Test-Struktur

```
backend/tests/
├── conftest.py              # Pytest Fixtures
├── test_broker_api.py       # Broker API Tests (11 Tests)
└── test_mqtt_client.py      # MQTT Client Tests (29 Tests)
```

### Manuelles Testing

```bash
# API Endpoints testen
curl http://localhost:8082/health
curl http://localhost:8082/api/broker/status
curl http://localhost:8082/api/broker/stats
curl http://localhost:8082/api/clients
curl http://localhost:8082/api/topics

# Message Publishing testen
curl -X POST http://localhost:8082/api/messages/publish \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "test/topic",
    "payload": "Hello MQTT",
    "qos": 1,
    "retain": false
  }'

# WebSocket Connection testen
npm install -g wscat
wscat -c ws://localhost:8082/socket.io/?transport=websocket
```

## 🚢 Deployment

### Docker Build

```bash
# Multi-stage Build (aus Haupt-Verzeichnis)
docker compose build mqtt-dashboard

# Nur Dashboard neu bauen
docker compose build --no-cache mqtt-dashboard

# Image testen
docker compose up mqtt-dashboard
```

### Docker Compose Deployment

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

### Startup Sequence

```bash
# 1. Container starten
docker compose up -d mqtt-dashboard

# 2. Logs verfolgen
docker compose logs -f mqtt-dashboard

# 3. Health Check prüfen
docker compose ps mqtt-dashboard
# Status sollte "healthy" sein

# 4. Dashboard öffnen
open http://localhost:8082
```

### Production Checklist

- [ ] `FLASK_ENV=production`
- [ ] `FLASK_DEBUG=0`
- [ ] `MQTT_USE_TLS=true` (wenn Broker TLS unterstützt)
- [ ] `MQTT_USERNAME` und `MQTT_PASSWORD` gesetzt
- [ ] `SOCKETIO_ASYNC_MODE=eventlet`
- [ ] Health Checks funktionieren
- [ ] Logs werden korrekt geschrieben
- [ ] WebSocket-Verbindungen funktionieren
- [ ] CORS-Einstellungen korrekt

## 🔧 Troubleshooting

### Problem: Dashboard zeigt "Broker Disconnected"

**Symptom:**
```
Dashboard UI: "Broker: Offline"
API Response: {"connected": false}
```

**Diagnose:**
```bash
# 1. Mosquitto Status prüfen
docker compose ps mosquitto
# Sollte "healthy" zeigen

# 2. Dashboard Logs prüfen
docker compose logs mqtt-dashboard | grep -i "mqtt\|error"

# 3. MQTT Broker Connection testen
docker exec app_mqtt_dashboard curl -f http://localhost:5000/api/broker/status

# 4. Environment Variables prüfen
docker compose exec mqtt-dashboard env | grep MQTT_

# 5. Mosquitto Logs prüfen
docker compose logs mosquitto | tail -50
```

**Lösungen:**
```bash
# Mosquitto nicht gestartet
docker compose up -d mosquitto

# Falsche Broker-Adresse
# .env ändern: MQTT_BROKER_HOST=mosquitto

# Authentifizierung fehlt
# .env ergänzen:
MQTT_USERNAME=your_username
MQTT_PASSWORD=your_password

# Dashboard neu starten
docker compose restart mqtt-dashboard
```

### Problem: WebSocket Verbindung fehlgeschlagen

**Symptom:**
```
Browser Console: "WebSocket connection to 'ws://localhost:8082' failed"
Dashboard: Keine Echtzeit-Updates
```

**Diagnose:**
```bash
# 1. Browser Console öffnen (F12)
# 2. Network Tab -> Filter: WS
# 3. Suche nach socket.io Connection

# 4. WebSocket Endpoint testen
curl -i http://localhost:8082/socket.io/

# Sollte returnen:
# HTTP/1.1 200 OK
# {"sid":"...","upgrades":["websocket"],"pingInterval":25000}

# 5. Container Logs prüfen
docker compose logs -f mqtt-dashboard | grep -i "websocket\|socketio"
```

**Lösungen:**
```bash
# SOCKETIO_ASYNC_MODE auf eventlet umstellen
# .env ändern:
SOCKETIO_ASYNC_MODE=eventlet

# eventlet Installation prüfen
docker compose exec mqtt-dashboard pip list | grep eventlet

# Dashboard neu bauen
docker compose build mqtt-dashboard
docker compose up -d mqtt-dashboard

# CORS-Probleme?
# Prüfe ob Frontend und Backend auf gleicher Origin
```

### Problem: "No module named 'app'" beim Start

**Symptom:**
```
ModuleNotFoundError: No module named 'app'
```

**Lösung:**
```bash
# 1. Dockerfile neu bauen
docker compose build --no-cache mqtt-dashboard

# 2. Container neu starten
docker compose up -d mqtt-dashboard

# 3. Falls immer noch Fehler:
# Alte Images entfernen
docker compose down
docker rmi $(docker images '*mqtt-dashboard*' -q)
docker compose up -d --build

# 4. Python Path prüfen
docker compose exec mqtt-dashboard python -c "import sys; print(sys.path)"
# /app sollte in der Liste sein
```

### Problem: Dashboard lädt langsam oder zeigt leere Daten

**Symptom:**
- Dashboard UI zeigt "Loading..." dauerhaft
- API Endpoints returnen `503 Service Unavailable`
- Metriken zeigen `0` oder `null`

**Diagnose:**
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

# 3. Mosquitto $SYS Topics prüfen
docker exec app_mosquitto mosquitto_sub -t '$SYS/#' -C 5
```

**Lösungen:**
```bash
# SysMonitor nicht gestartet
# Dashboard neu starten
docker compose restart mqtt-dashboard

# Mosquitto erlaubt keine $SYS Subscriptions
# mosquitto.conf prüfen:
# allow_anonymous true
# oder User/Pass konfigurieren

# Topic Tracker Timeout
# Backend Logs prüfen auf "timeout" oder "subscription failed"
```

### Problem: Frontend Build schlägt fehl

**Symptom:**
```bash
npm run build
# ERROR: ...
```

**Lösung:**
```bash
# 1. node_modules löschen und neu installieren
cd frontend
rm -rf node_modules package-lock.json
npm install

# 2. Node Version prüfen
node --version
# Sollte >= 18.0.0 sein

# 3. Cache leeren
npm cache clean --force

# 4. Build mit verbose output
npm run build -- --debug

# 5. Docker Build testen
cd ..
docker compose build mqtt-dashboard
```

### Problem: Charts werden nicht angezeigt

**Symptom:**
- Overview zeigt leere Chart-Bereiche
- Browser Console: Chart.js errors

**Lösung:**
```bash
# 1. Chart.js Dependencies prüfen
cd frontend
npm list chart.js vue-chartjs

# 2. Neu installieren falls fehlt
npm install chart.js vue-chartjs

# 3. Browser Cache leeren
# Chrome: Ctrl+Shift+Delete
# Firefox: Ctrl+Shift+Delete

# 4. Frontend neu bauen
npm run build

# 5. Dashboard Container neu starten
cd ..
docker compose restart mqtt-dashboard
```

## 📖 Weitere Dokumentation

- **Haupt-README**: `../README.md` - Vollständige Projekt-Dokumentation
- **API Dokumentation**: http://localhost:8082/api - Live API Endpoint Liste
- **Deployment Guide**: `../DEPLOYMENT_VERIFICATION.md` - Deployment-Checkliste
- **Docker Compose**: `../docker-compose.yml` - Service-Konfiguration

## 📝 Lizenz

Dieses Projekt ist Teil der Claude Docker Compose Umgebung.

## 🤝 Beiträge

Bei Fragen oder Problemen bitte ein Issue erstellen.

---

**Version:** 1.0.0
**Erstellt:** Januar 2026
**Technologie:** Vue.js 3 + Flask + MQTT
