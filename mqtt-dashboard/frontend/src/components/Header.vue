<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import { brokerApi, getSocket, connectSocket } from "../api/client.js";

const emit = defineEmits(["toggle-sidebar"]);

// Broker connection state
const brokerStatus = ref({
  connected: false,
  host: "mosquitto",
  port: 1883,
});

const loading = ref(true);
const wsConnected = ref(false);

// Fetch broker status
const fetchBrokerStatus = async () => {
  try {
    loading.value = true;
    const data = await brokerApi.getStatus();
    brokerStatus.value = {
      connected: data.connected,
      host: data.host || "mosquitto",
      port: data.port || 1883,
    };
  } catch (error) {
    console.error("Failed to fetch broker status:", error);
    brokerStatus.value.connected = false;
  } finally {
    loading.value = false;
  }
};

// Initialize WebSocket connection
const initWebSocket = async () => {
  try {
    await connectSocket();
    const socket = getSocket();

    socket.on("connect", () => {
      wsConnected.value = true;
    });

    socket.on("disconnect", () => {
      wsConnected.value = false;
    });

    // Subscribe to broker status updates
    socket.emit("subscribe", { channel: "broker_summary" });

    socket.on("broker_summary", (data) => {
      if (data && data.connected !== undefined) {
        brokerStatus.value.connected = data.connected;
      }
    });

    wsConnected.value = socket.connected;
  } catch (error) {
    console.error("WebSocket connection failed:", error);
  }
};

// Get current time for display
const currentTime = ref(new Date().toLocaleTimeString());
let timeInterval = null;

const updateTime = () => {
  currentTime.value = new Date().toLocaleTimeString();
};

onMounted(() => {
  fetchBrokerStatus();
  initWebSocket();

  // Update time every second
  timeInterval = setInterval(updateTime, 1000);
});

onUnmounted(() => {
  if (timeInterval) {
    clearInterval(timeInterval);
  }

  // Unsubscribe from WebSocket channels
  const socket = getSocket();
  if (socket.connected) {
    socket.emit("unsubscribe", { channel: "broker_summary" });
  }
});
</script>

<template>
  <header class="h-16 bg-white border-b border-gray-200 flex items-center px-6 justify-between">
    <!-- Left section: Mobile menu button + Page title -->
    <div class="flex items-center space-x-4">
      <!-- Mobile menu button -->
      <button
        class="lg:hidden p-2 rounded-md text-gray-500 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
        @click="emit('toggle-sidebar')"
        aria-label="Toggle sidebar"
      >
        <svg
          class="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M4 6h16M4 12h16M4 18h16"
          />
        </svg>
      </button>

      <!-- Page title from route -->
      <h2 class="text-lg font-semibold text-gray-900 hidden md:block">
        {{ $route.meta.title || "Dashboard" }}
      </h2>
    </div>

    <!-- Right section: Broker status + Time -->
    <div class="flex items-center space-x-6">
      <!-- Broker connection status -->
      <div class="flex items-center space-x-2">
        <span
          :class="[
            'status-dot',
            loading
              ? 'bg-gray-400'
              : brokerStatus.connected
              ? 'status-online animate-pulse-slow'
              : 'status-offline',
          ]"
          :title="
            loading
              ? 'Loading...'
              : brokerStatus.connected
              ? 'Broker Connected'
              : 'Broker Disconnected'
          "
        ></span>
        <div class="hidden sm:block">
          <div class="text-sm font-medium text-gray-900">
            {{ loading ? "Loading..." : brokerStatus.connected ? "Connected" : "Disconnected" }}
          </div>
          <div class="text-xs text-gray-500">
            {{ brokerStatus.host }}:{{ brokerStatus.port }}
          </div>
        </div>
      </div>

      <!-- WebSocket status indicator -->
      <div
        :title="wsConnected ? 'WebSocket Connected' : 'WebSocket Disconnected'"
        class="hidden lg:flex items-center space-x-1"
      >
        <span
          :class="[
            'w-1.5 h-1.5 rounded-full',
            wsConnected ? 'bg-mqtt-green' : 'bg-gray-400',
          ]"
        ></span>
        <span class="text-xs text-gray-500">WS</span>
      </div>

      <!-- Current time -->
      <div class="hidden md:block text-sm text-gray-600 font-mono">
        {{ currentTime }}
      </div>
    </div>
  </header>
</template>
