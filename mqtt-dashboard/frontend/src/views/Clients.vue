<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { clientsApi, getSocket, connectSocket } from "../api/client.js";
import ClientsTable from "../components/ClientsTable.vue";
import StatCard from "../components/StatCard.vue";

// State
const loading = ref(true);
const clientData = ref(null);
const wsConnected = ref(false);
const searchQuery = ref("");

// Previous stats for trend calculation
const previousStats = ref({
  currently_connected: 0,
  total_tracked: 0,
  persistent_disconnected: 0,
  expired_sessions: 0,
});

// Fetch client data
const fetchClients = async () => {
  try {
    loading.value = true;
    const data = await clientsApi.getClients();

    // Store previous values before updating
    if (clientData.value?.summary) {
      previousStats.value = {
        currently_connected: clientData.value.summary.currently_connected || 0,
        total_tracked: clientData.value.summary.total_tracked || 0,
        persistent_disconnected: clientData.value.summary.persistent_disconnected || 0,
        expired_sessions: clientData.value.summary.expired_sessions || 0,
      };
    }

    clientData.value = data;
  } catch (error) {
    console.error("Failed to fetch client data:", error);
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
      // Subscribe to clients channel
      socket.emit("subscribe", { channel: "clients" });
    });

    socket.on("disconnect", () => {
      wsConnected.value = false;
    });

    // Listen for real-time client updates
    socket.on("clients", (data) => {
      if (data && data.stats) {
        // Store previous values before updating
        if (clientData.value?.summary) {
          previousStats.value = {
            currently_connected: clientData.value.summary.currently_connected || 0,
            total_tracked: clientData.value.summary.total_tracked || 0,
            persistent_disconnected: clientData.value.summary.persistent_disconnected || 0,
            expired_sessions: clientData.value.summary.expired_sessions || 0,
          };
        }

        // Update client data from WebSocket
        fetchClients();
      }
    });

    wsConnected.value = socket.connected;
  } catch (error) {
    console.error("WebSocket connection failed:", error);
  }
};

// Computed values
const summary = computed(() => clientData.value?.summary || {});

const categories = computed(() => clientData.value?.categories || []);

const connectionActivity = computed(() => clientData.value?.connection_activity || {});

const connectedCount = computed(() => summary.value.currently_connected || 0);

const totalCount = computed(() => summary.value.total_tracked || 0);

const disconnectedCount = computed(() => summary.value.persistent_disconnected || 0);

const expiredCount = computed(() => summary.value.expired_sessions || 0);

const peakConnections = computed(() => summary.value.peak_connections || 0);

// Trend calculation
const connectedTrend = computed(() => {
  if (!clientData.value || !previousStats.value) return "";
  const current = summary.value.currently_connected || 0;
  const previous = previousStats.value.currently_connected || 0;
  if (current > previous) return "up";
  if (current < previous) return "down";
  return "neutral";
});

// Filtered categories based on search
const filteredCategories = computed(() => {
  if (!searchQuery.value) return categories.value;

  const query = searchQuery.value.toLowerCase();
  return categories.value.filter((category) =>
    category.name.toLowerCase().includes(query) ||
    category.description.toLowerCase().includes(query)
  );
});

// Format connection rate
const formatRate = (rate) => {
  if (rate === null || rate === undefined) return "0.0";
  return rate.toFixed(1);
};

// Lifecycle hooks
onMounted(() => {
  fetchClients();
  initWebSocket();
});

onUnmounted(() => {
  const socket = getSocket();
  if (socket.connected) {
    socket.emit("unsubscribe", { channel: "clients" });
  }
});
</script>

<template>
  <div class="space-y-6">
    <!-- Page header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Connected Clients</h1>
        <p class="text-sm text-gray-600 mt-1">
          Monitor MQTT client connections and statistics
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

    <!-- Client Statistics Cards -->
    <div>
      <h2 class="text-lg font-semibold text-gray-900 mb-3">Summary</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Connected Clients"
          :value="connectedCount"
          icon="👥"
          :trend="connectedTrend"
          :trend-value="connectedTrend ? 'from last update' : ''"
          status="online"
          :loading="loading"
        />
        <StatCard
          title="Total Tracked"
          :value="totalCount"
          icon="📊"
          :loading="loading"
        />
        <StatCard
          title="Disconnected"
          :value="disconnectedCount"
          icon="👤"
          status="offline"
          :loading="loading"
        />
        <StatCard
          title="Peak Connections"
          :value="peakConnections"
          icon="📈"
          :loading="loading"
        />
      </div>
    </div>

    <!-- Connection Activity -->
    <div>
      <h2 class="text-lg font-semibold text-gray-900 mb-3">Connection Activity</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          title="1 Min Rate"
          :value="formatRate(connectionActivity.rate_1min)"
          unit="conn/min"
          icon="⏱️"
          :loading="loading"
        />
        <StatCard
          title="5 Min Rate"
          :value="formatRate(connectionActivity.rate_5min)"
          unit="conn/min"
          icon="⏱️"
          :loading="loading"
        />
        <StatCard
          title="15 Min Rate"
          :value="formatRate(connectionActivity.rate_15min)"
          unit="conn/min"
          icon="⏱️"
          :loading="loading"
        />
      </div>
    </div>

    <!-- Search and Filter -->
    <div class="card">
      <div class="flex items-center justify-between mb-4">
        <h2 class="card-header mb-0">Client Categories</h2>
        <div class="w-64">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search categories..."
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-mqtt-blue focus:border-transparent"
          />
        </div>
      </div>

      <!-- Clients Table -->
      <ClientsTable
        :categories="filteredCategories"
        :loading="loading"
      />
    </div>

    <!-- Info Note -->
    <div class="card bg-blue-50 border border-blue-200">
      <div class="flex items-start space-x-3">
        <span class="text-2xl">ℹ️</span>
        <div class="flex-1">
          <h3 class="text-sm font-semibold text-blue-900 mb-1">
            About Client Statistics
          </h3>
          <p class="text-sm text-blue-800">
            Mosquitto's $SYS topics provide aggregate client statistics rather than individual client identifiers.
            The data shown here represents categories of clients based on their connection state and session persistence.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
