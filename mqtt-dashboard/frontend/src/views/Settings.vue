<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { brokerApi, getSocket, connectSocket } from "../api/client.js";
import ConnectionInfo from "../components/ConnectionInfo.vue";
import StatCard from "../components/StatCard.vue";

// State
const loading = ref(true);
const testing = ref(false);
const testResult = ref(null);
const brokerStatus = ref(null);
const brokerStats = ref(null);
const brokerVersion = ref(null);
const wsConnected = ref(false);

// Fetch broker settings
const fetchSettings = async () => {
  try {
    loading.value = true;
    const [status, stats, version] = await Promise.all([
      brokerApi.getStatus(),
      brokerApi.getStats().catch(() => null), // Stats might fail if broker is disconnected
      brokerApi.getVersion().catch(() => null),
    ]);

    brokerStatus.value = status;
    brokerStats.value = stats;
    brokerVersion.value = version;
  } catch (error) {
    console.error("Failed to fetch broker settings:", error);
  } finally {
    loading.value = false;
  }
};

// Test broker connection
const testConnection = async () => {
  try {
    testing.value = true;
    testResult.value = null;

    const status = await brokerApi.getStatus();

    if (status.connected) {
      testResult.value = {
        success: true,
        message: "Successfully connected to MQTT broker",
        details: `Connected to ${status.broker.host}:${status.broker.port}`,
      };
    } else {
      testResult.value = {
        success: false,
        message: "Failed to connect to MQTT broker",
        details: "Broker is not connected",
      };
    }
  } catch (error) {
    testResult.value = {
      success: false,
      message: "Connection test failed",
      details: error.message,
    };
  } finally {
    testing.value = false;
  }
};

// Initialize WebSocket connection for real-time updates
const initWebSocket = async () => {
  try {
    await connectSocket();
    const socket = getSocket();

    socket.on("connect", () => {
      wsConnected.value = true;
      // Subscribe to broker stats channel for real-time updates
      socket.emit("subscribe", { channel: "broker_stats" });
    });

    socket.on("disconnect", () => {
      wsConnected.value = false;
    });

    // Listen for real-time broker stats updates
    socket.on("broker_stats", (data) => {
      if (data && data.stats) {
        brokerStats.value = data.stats;
      }
    });

    wsConnected.value = socket.connected;
  } catch (error) {
    console.error("WebSocket connection failed:", error);
  }
};

// Computed values
const connectionDetails = computed(() => {
  if (!brokerStatus.value) {
    return {
      connected: false,
      host: "Unknown",
      port: 1883,
      clientId: "mqtt-dashboard",
      useTls: false,
      keepalive: 60,
    };
  }

  return {
    connected: brokerStatus.value.connected,
    host: brokerStatus.value.broker.host || "Unknown",
    port: brokerStatus.value.broker.port || 1883,
    clientId: "mqtt-dashboard", // From config, not in API response
    useTls: false, // From config, not in API response
    keepalive: 60, // From config, not in API response
  };
});

const versionInfo = computed(() => {
  if (!brokerVersion.value) {
    return {
      version: "Unknown",
      uptime: "Unknown",
    };
  }

  return {
    version: brokerVersion.value.version || "Unknown",
    uptime: brokerVersion.value.uptime_formatted || "Unknown",
  };
});

// Persistence settings (from $SYS topics)
const persistenceEnabled = computed(() => {
  // Check if we have retained messages, which indicates persistence
  return brokerStats.value?.messages_stored !== undefined;
});

const retainedMessagesCount = computed(() => {
  return brokerStats.value?.messages_stored || 0;
});

// Listener configuration (estimated from available data)
const listenerCount = computed(() => {
  // Most brokers have at least 1 listener (MQTT) and potentially WebSocket
  return 2; // Default: MQTT + WebSocket
});

const authenticationEnabled = computed(() => {
  // This would require additional API endpoint to determine
  return "Unknown";
});

// Lifecycle hooks
onMounted(() => {
  fetchSettings();
  initWebSocket();
});

onUnmounted(() => {
  const socket = getSocket();
  if (socket.connected) {
    socket.emit("unsubscribe", { channel: "broker_stats" });
  }
});
</script>

<template>
  <div class="space-y-6">
    <!-- Page header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Broker Settings</h1>
        <p class="text-sm text-gray-600 mt-1">
          View broker configuration and connection settings
        </p>
      </div>
      <button
        @click="testConnection"
        :disabled="testing"
        class="btn-primary flex items-center space-x-2"
      >
        <span v-if="testing">🔄</span>
        <span v-else>🔌</span>
        <span>{{ testing ? "Testing..." : "Test Connection" }}</span>
      </button>
    </div>

    <!-- Test result alert -->
    <div
      v-if="testResult"
      :class="[
        'rounded-lg p-4 border-2',
        testResult.success
          ? 'bg-green-50 border-mqtt-green text-green-900'
          : 'bg-red-50 border-mqtt-red text-red-900',
      ]"
    >
      <div class="flex items-start">
        <span class="text-2xl mr-3">
          {{ testResult.success ? "✅" : "❌" }}
        </span>
        <div class="flex-1">
          <h4 class="font-semibold mb-1">{{ testResult.message }}</h4>
          <p class="text-sm opacity-90">{{ testResult.details }}</p>
        </div>
        <button
          @click="testResult = null"
          class="text-gray-400 hover:text-gray-600 ml-2"
        >
          ✕
        </button>
      </div>
    </div>

    <!-- Configuration note -->
    <div class="bg-blue-50 border-2 border-blue-200 rounded-lg p-4">
      <div class="flex items-start">
        <span class="text-2xl mr-3">ℹ️</span>
        <div class="flex-1">
          <h4 class="font-semibold text-blue-900 mb-1">Read-Only Configuration</h4>
          <p class="text-sm text-blue-800">
            Settings are read-only and can only be modified by editing the
            <code class="bg-blue-100 px-1.5 py-0.5 rounded font-mono text-xs">mosquitto.conf</code>
            file and restarting the broker.
          </p>
        </div>
      </div>
    </div>

    <!-- Connection Information -->
    <ConnectionInfo
      :connected="connectionDetails.connected"
      :host="connectionDetails.host"
      :port="connectionDetails.port"
      :client-id="connectionDetails.clientId"
      :use-tls="connectionDetails.useTls"
      :keepalive="connectionDetails.keepalive"
      :version="versionInfo.version"
      :uptime="versionInfo.uptime"
      :loading="loading"
    />

    <!-- Listener Configuration -->
    <div class="card">
      <h3 class="card-header">Listener Configuration</h3>

      <!-- Loading state -->
      <div v-if="loading" class="space-y-3">
        <div class="animate-pulse">
          <div class="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
          <div class="h-4 bg-gray-200 rounded w-1/2"></div>
        </div>
      </div>

      <!-- Listener details -->
      <div v-else class="space-y-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <StatCard
            title="Active Listeners"
            :value="listenerCount"
            icon="🎧"
            :loading="loading"
          />
          <StatCard
            title="Default Port"
            :value="connectionDetails.port"
            icon="🔌"
            :loading="loading"
          />
        </div>

        <div class="pt-3 border-t border-gray-200">
          <div class="text-xs text-gray-500 mb-2">Configured Listeners</div>
          <div class="space-y-2">
            <div class="flex items-center justify-between p-2 bg-gray-50 rounded border border-gray-200">
              <div class="flex items-center space-x-3">
                <span class="text-sm font-medium text-gray-700">MQTT</span>
                <span class="text-xs font-mono text-gray-600">Port {{ connectionDetails.port }}</span>
              </div>
              <span
                :class="[
                  'px-2 py-1 rounded-full text-xs font-medium',
                  connectionDetails.connected
                    ? 'bg-green-100 text-green-800'
                    : 'bg-gray-100 text-gray-600',
                ]"
              >
                {{ connectionDetails.connected ? "Active" : "Inactive" }}
              </span>
            </div>
            <div class="flex items-center justify-between p-2 bg-gray-50 rounded border border-gray-200">
              <div class="flex items-center space-x-3">
                <span class="text-sm font-medium text-gray-700">WebSocket</span>
                <span class="text-xs font-mono text-gray-600">Port 9001</span>
              </div>
              <span class="px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                Configured
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Persistence Settings -->
    <div class="card">
      <h3 class="card-header">Persistence Settings</h3>

      <!-- Loading state -->
      <div v-if="loading" class="space-y-3">
        <div class="animate-pulse">
          <div class="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
          <div class="h-4 bg-gray-200 rounded w-1/2"></div>
        </div>
      </div>

      <!-- Persistence details -->
      <div v-else class="space-y-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <StatCard
            title="Persistence"
            :value="persistenceEnabled ? 'Enabled' : 'Disabled'"
            icon="💾"
            :status="persistenceEnabled ? 'online' : ''"
            :loading="loading"
          />
          <StatCard
            title="Retained Messages"
            :value="retainedMessagesCount"
            icon="📌"
            :loading="loading"
          />
        </div>

        <div class="pt-3 border-t border-gray-200">
          <div class="text-xs text-gray-500 mb-2">Persistence Information</div>
          <p class="text-sm text-gray-700">
            Persistence allows the broker to store QoS 1 and QoS 2 messages, subscriptions,
            and retained messages to disk. This ensures messages are not lost on broker restart.
          </p>
        </div>
      </div>
    </div>

    <!-- Security Settings -->
    <div class="card">
      <h3 class="card-header">Security Settings</h3>

      <!-- Loading state -->
      <div v-if="loading" class="space-y-3">
        <div class="animate-pulse">
          <div class="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
          <div class="h-4 bg-gray-200 rounded w-1/2"></div>
        </div>
      </div>

      <!-- Security details -->
      <div v-else class="space-y-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <StatCard
            title="TLS/SSL"
            :value="connectionDetails.useTls ? 'Enabled' : 'Disabled'"
            icon="🔒"
            :status="connectionDetails.useTls ? 'online' : ''"
            :loading="loading"
          />
          <StatCard
            title="Authentication"
            :value="authenticationEnabled"
            icon="🔑"
            :loading="loading"
          />
        </div>

        <div class="pt-3 border-t border-gray-200">
          <div class="text-xs text-gray-500 mb-2">Security Information</div>
          <p class="text-sm text-gray-700">
            Security settings control access to the broker through TLS encryption and authentication.
            Configure these in the <code class="bg-gray-100 px-1.5 py-0.5 rounded font-mono text-xs">mosquitto.conf</code> file.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
