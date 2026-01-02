<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { brokerApi, getSocket, connectSocket } from "../api/client.js";
import StatCard from "../components/StatCard.vue";
import BrokerHealth from "../components/BrokerHealth.vue";
import ThroughputChart from "../components/ThroughputChart.vue";
import ConnectionsChart from "../components/ConnectionsChart.vue";

// State
const loading = ref(true);
const brokerStats = ref(null);
const brokerVersion = ref(null);
const wsConnected = ref(false);

// Previous stats for trend calculation
const previousStats = ref({
  clients_connected: 0,
  messages_received_1min: 0,
  messages_sent_1min: 0,
  bytes_received: 0,
  bytes_sent: 0,
});

// Fetch broker statistics
const fetchStats = async () => {
  try {
    loading.value = true;
    const [stats, version] = await Promise.all([
      brokerApi.getStats(),
      brokerApi.getVersion(),
    ]);

    // Store previous values before updating
    if (brokerStats.value) {
      previousStats.value = {
        clients_connected: brokerStats.value.clients_connected || 0,
        messages_received_1min: brokerStats.value.messages_received_1min || 0,
        messages_sent_1min: brokerStats.value.messages_sent_1min || 0,
        bytes_received: brokerStats.value.bytes_received || 0,
        bytes_sent: brokerStats.value.bytes_sent || 0,
      };
    }

    brokerStats.value = stats;
    brokerVersion.value = version;
  } catch (error) {
    console.error("Failed to fetch broker stats:", error);
  } finally {
    loading.value = false;
  }
};

// Initialize WebSocket connection for real-time updates
const initWebSocket = async () => {
  try {
    await connectSocket();
    const socket = getSocket();

    socket.on("connect", () => {
      wsConnected.value = true;
      // Subscribe to broker stats channel
      socket.emit("subscribe", { channel: "broker_stats" });
    });

    socket.on("disconnect", () => {
      wsConnected.value = false;
    });

    // Listen for real-time broker stats updates
    socket.on("broker_stats", (data) => {
      if (data && data.stats) {
        // Store previous values before updating
        if (brokerStats.value) {
          previousStats.value = {
            clients_connected: brokerStats.value.clients_connected || 0,
            messages_received_1min: brokerStats.value.messages_received_1min || 0,
            messages_sent_1min: brokerStats.value.messages_sent_1min || 0,
            bytes_received: brokerStats.value.bytes_received || 0,
            bytes_sent: brokerStats.value.bytes_sent || 0,
          };
        }
        brokerStats.value = data.stats;
      }
    });

    wsConnected.value = socket.connected;
  } catch (error) {
    console.error("WebSocket connection failed:", error);
  }
};

// Computed values for display
const clientsConnected = computed(() => {
  return brokerStats.value?.clients_connected || 0;
});

const clientsTrend = computed(() => {
  if (!brokerStats.value || !previousStats.value) return "";
  const current = brokerStats.value.clients_connected || 0;
  const previous = previousStats.value.clients_connected || 0;
  if (current > previous) return "up";
  if (current < previous) return "down";
  return "neutral";
});

const messagesReceivedPerMin = computed(() => {
  return brokerStats.value?.messages_received_1min || 0;
});

const messagesSentPerMin = computed(() => {
  return brokerStats.value?.messages_sent_1min || 0;
});

const totalMessages = computed(() => {
  const received = brokerStats.value?.messages_received || 0;
  const sent = brokerStats.value?.messages_sent || 0;
  return received + sent;
});

const bytesReceived = computed(() => {
  const bytes = brokerStats.value?.bytes_received || 0;
  return formatBytes(bytes);
});

const bytesSent = computed(() => {
  const bytes = brokerStats.value?.bytes_sent || 0;
  return formatBytes(bytes);
});

const totalBytes = computed(() => {
  const received = brokerStats.value?.bytes_received || 0;
  const sent = brokerStats.value?.bytes_sent || 0;
  return formatBytes(received + sent);
});

const subscriptionsCount = computed(() => {
  return brokerStats.value?.subscriptions_count || 0;
});

const retainedMessages = computed(() => {
  return brokerStats.value?.messages_stored || 0;
});

// Format bytes to human-readable format
const formatBytes = (bytes) => {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2));
};

const formatBytesWithUnit = (bytes) => {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return {
    value: parseFloat((bytes / Math.pow(k, i)).toFixed(2)),
    unit: sizes[i],
  };
};

const bytesReceivedDisplay = computed(() => {
  const bytes = brokerStats.value?.bytes_received || 0;
  return formatBytesWithUnit(bytes);
});

const bytesSentDisplay = computed(() => {
  const bytes = brokerStats.value?.bytes_sent || 0;
  return formatBytesWithUnit(bytes);
});

const totalBytesDisplay = computed(() => {
  const received = brokerStats.value?.bytes_received || 0;
  const sent = brokerStats.value?.bytes_sent || 0;
  return formatBytesWithUnit(received + sent);
});

// Format large numbers
const formatNumber = (num) => {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + "M";
  if (num >= 1000) return (num / 1000).toFixed(1) + "K";
  return num.toString();
};

// Lifecycle hooks
onMounted(() => {
  fetchStats();
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
        <h1 class="text-2xl font-bold text-gray-900">Broker Overview</h1>
        <p class="text-sm text-gray-600 mt-1">
          Monitor your Mosquitto MQTT broker in real-time
        </p>
      </div>
      <div class="flex items-center space-x-2">
        <span
          :class="[
            'inline-flex items-center px-3 py-1 rounded-full text-xs font-medium',
            wsConnected
              ? 'bg-green-100 text-green-800'
              : 'bg-gray-100 text-gray-800',
          ]"
        >
          <span
            :class="[
              'w-2 h-2 rounded-full mr-2',
              wsConnected ? 'bg-mqtt-green animate-pulse-slow' : 'bg-gray-400',
            ]"
          ></span>
          {{ wsConnected ? "Live" : "Offline" }}
        </span>
      </div>
    </div>

    <!-- Broker Health Card -->
    <BrokerHealth
      :connected="brokerStats?.connected || false"
      :version="brokerVersion?.version || 'Unknown'"
      :uptime="brokerVersion?.uptime || 'Unknown'"
      :clients-connected="clientsConnected"
      :clients-max="brokerStats?.clients_maximum || 0"
      :messages-received="brokerStats?.messages_received || 0"
      :messages-sent="brokerStats?.messages_sent || 0"
      :subscriptions-count="subscriptionsCount"
      :loading="loading"
    />

    <!-- Client Statistics -->
    <div>
      <h2 class="text-lg font-semibold text-gray-900 mb-3">Client Statistics</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Connected Clients"
          :value="clientsConnected"
          icon="👥"
          :trend="clientsTrend"
          :trend-value="clientsTrend ? 'from last update' : ''"
          :status="brokerStats?.connected ? 'online' : 'offline'"
          :loading="loading"
        />
        <StatCard
          title="Total Clients"
          :value="brokerStats?.clients_total || 0"
          icon="📊"
          :loading="loading"
        />
        <StatCard
          title="Disconnected"
          :value="brokerStats?.clients_disconnected || 0"
          icon="👤"
          :loading="loading"
        />
        <StatCard
          title="Subscriptions"
          :value="formatNumber(subscriptionsCount)"
          icon="📌"
          :loading="loading"
        />
      </div>
    </div>

    <!-- Message Throughput -->
    <div>
      <h2 class="text-lg font-semibold text-gray-900 mb-3">Message Throughput</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Received (1 min)"
          :value="messagesReceivedPerMin"
          unit="msg/min"
          icon="📥"
          :loading="loading"
        />
        <StatCard
          title="Sent (1 min)"
          :value="messagesSentPerMin"
          unit="msg/min"
          icon="📤"
          :loading="loading"
        />
        <StatCard
          title="Total Messages"
          :value="formatNumber(totalMessages)"
          icon="💬"
          :loading="loading"
        />
        <StatCard
          title="Retained Messages"
          :value="formatNumber(retainedMessages)"
          icon="💾"
          :loading="loading"
        />
      </div>
    </div>

    <!-- Data Transfer -->
    <div>
      <h2 class="text-lg font-semibold text-gray-900 mb-3">Data Transfer</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard
          title="Bytes Received"
          :value="bytesReceivedDisplay.value"
          :unit="bytesReceivedDisplay.unit"
          icon="⬇️"
          :loading="loading"
        />
        <StatCard
          title="Bytes Sent"
          :value="bytesSentDisplay.value"
          :unit="bytesSentDisplay.unit"
          icon="⬆️"
          :loading="loading"
        />
        <StatCard
          title="Total Transfer"
          :value="totalBytesDisplay.value"
          :unit="totalBytesDisplay.unit"
          icon="🔄"
          :loading="loading"
        />
      </div>
    </div>

    <!-- Additional Metrics -->
    <div>
      <h2 class="text-lg font-semibold text-gray-900 mb-3">Broker Load</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Publish Dropped"
          :value="brokerStats?.messages_publish_dropped || 0"
          icon="⚠️"
          :status="
            (brokerStats?.messages_publish_dropped || 0) > 0 ? 'warning' : ''
          "
          :loading="loading"
        />
        <StatCard
          title="Publish Received"
          :value="formatNumber(brokerStats?.messages_publish_received || 0)"
          icon="📨"
          :loading="loading"
        />
        <StatCard
          title="Publish Sent"
          :value="formatNumber(brokerStats?.messages_publish_sent || 0)"
          icon="📮"
          :loading="loading"
        />
        <StatCard
          title="Heap Current"
          :value="
            brokerStats?.heap_current
              ? Math.round(brokerStats.heap_current / 1024)
              : 0
          "
          unit="KB"
          icon="🧠"
          :loading="loading"
        />
      </div>
    </div>

    <!-- Charts Section -->
    <div>
      <h2 class="text-lg font-semibold text-gray-900 mb-3">Performance Trends</h2>
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Throughput Chart -->
        <ThroughputChart :broker-stats="brokerStats" :time-window="60" />

        <!-- Connections Chart -->
        <ConnectionsChart :broker-stats="brokerStats" :time-window="60" />
      </div>
    </div>
  </div>
</template>
