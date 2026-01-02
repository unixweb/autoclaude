<script setup>
import { computed } from "vue";

const props = defineProps({
  connected: {
    type: Boolean,
    required: true,
  },
  version: {
    type: String,
    default: "Unknown",
  },
  uptime: {
    type: String,
    default: "Unknown",
  },
  clientsConnected: {
    type: Number,
    default: 0,
  },
  clientsMax: {
    type: Number,
    default: 0,
  },
  messagesReceived: {
    type: Number,
    default: 0,
  },
  messagesSent: {
    type: Number,
    default: 0,
  },
  subscriptionsCount: {
    type: Number,
    default: 0,
  },
  loading: {
    type: Boolean,
    default: false,
  },
});

const healthStatus = computed(() => {
  if (!props.connected) return "offline";
  if (props.clientsMax > 0 && props.clientsConnected >= props.clientsMax * 0.9) {
    return "warning";
  }
  return "healthy";
});

const healthIcon = computed(() => {
  if (healthStatus.value === "offline") return "🔴";
  if (healthStatus.value === "warning") return "⚠️";
  return "✅";
});

const healthText = computed(() => {
  if (healthStatus.value === "offline") return "Disconnected";
  if (healthStatus.value === "warning") return "Capacity Warning";
  return "Healthy";
});

const healthClass = computed(() => {
  if (healthStatus.value === "offline") return "bg-red-50 border-mqtt-red";
  if (healthStatus.value === "warning") return "bg-yellow-50 border-mqtt-yellow";
  return "bg-green-50 border-mqtt-green";
});

const statusTextClass = computed(() => {
  if (healthStatus.value === "offline") return "text-mqtt-red";
  if (healthStatus.value === "warning") return "text-mqtt-yellow";
  return "text-mqtt-green";
});

const formatNumber = (num) => {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + "M";
  if (num >= 1000) return (num / 1000).toFixed(1) + "K";
  return num.toString();
};
</script>

<template>
  <div :class="['card border-2 transition-colors duration-300', healthClass]">
    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <h3 class="card-header mb-0">Broker Health</h3>
      <div class="flex items-center space-x-2">
        <span class="text-2xl">{{ healthIcon }}</span>
        <span :class="['text-sm font-semibold', statusTextClass]">
          {{ healthText }}
        </span>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="space-y-3">
      <div class="animate-pulse">
        <div class="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
        <div class="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
        <div class="h-4 bg-gray-200 rounded w-2/3"></div>
      </div>
    </div>

    <!-- Health details -->
    <div v-else class="space-y-3">
      <!-- Version and uptime -->
      <div class="grid grid-cols-2 gap-4">
        <div>
          <div class="text-xs text-gray-500 mb-1">Version</div>
          <div class="text-sm font-medium text-gray-900 font-mono">
            {{ version }}
          </div>
        </div>
        <div>
          <div class="text-xs text-gray-500 mb-1">Uptime</div>
          <div class="text-sm font-medium text-gray-900">
            {{ uptime }}
          </div>
        </div>
      </div>

      <!-- Metrics grid -->
      <div class="grid grid-cols-2 gap-4 pt-3 border-t border-gray-200">
        <!-- Clients -->
        <div>
          <div class="text-xs text-gray-500 mb-1">Clients</div>
          <div class="flex items-baseline space-x-1">
            <span class="text-lg font-bold text-gray-900">
              {{ clientsConnected }}
            </span>
            <span v-if="clientsMax > 0" class="text-xs text-gray-500">
              / {{ clientsMax }} max
            </span>
          </div>
        </div>

        <!-- Subscriptions -->
        <div>
          <div class="text-xs text-gray-500 mb-1">Subscriptions</div>
          <div class="text-lg font-bold text-gray-900">
            {{ formatNumber(subscriptionsCount) }}
          </div>
        </div>

        <!-- Messages received -->
        <div>
          <div class="text-xs text-gray-500 mb-1">Messages In</div>
          <div class="text-lg font-bold text-gray-900">
            {{ formatNumber(messagesReceived) }}
          </div>
        </div>

        <!-- Messages sent -->
        <div>
          <div class="text-xs text-gray-500 mb-1">Messages Out</div>
          <div class="text-lg font-bold text-gray-900">
            {{ formatNumber(messagesSent) }}
          </div>
        </div>
      </div>

      <!-- Connection status bar -->
      <div v-if="connected && clientsMax > 0" class="pt-3 border-t border-gray-200">
        <div class="flex items-center justify-between text-xs text-gray-500 mb-1">
          <span>Capacity</span>
          <span>{{ Math.round((clientsConnected / clientsMax) * 100) }}%</span>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-2">
          <div
            :class="[
              'h-2 rounded-full transition-all duration-300',
              clientsConnected / clientsMax > 0.9
                ? 'bg-mqtt-yellow'
                : 'bg-mqtt-green',
            ]"
            :style="{ width: `${Math.min((clientsConnected / clientsMax) * 100, 100)}%` }"
          ></div>
        </div>
      </div>
    </div>
  </div>
</template>
