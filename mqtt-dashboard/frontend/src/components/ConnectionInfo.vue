<script setup>
import { computed } from "vue";

const props = defineProps({
  connected: {
    type: Boolean,
    required: true,
  },
  host: {
    type: String,
    default: "Unknown",
  },
  port: {
    type: Number,
    default: 1883,
  },
  clientId: {
    type: String,
    default: "mqtt-dashboard",
  },
  useTls: {
    type: Boolean,
    default: false,
  },
  keepalive: {
    type: Number,
    default: 60,
  },
  version: {
    type: String,
    default: "Unknown",
  },
  uptime: {
    type: String,
    default: "Unknown",
  },
  loading: {
    type: Boolean,
    default: false,
  },
});

const connectionStatus = computed(() => {
  return props.connected ? "connected" : "disconnected";
});

const statusIcon = computed(() => {
  return props.connected ? "✅" : "🔴";
});

const statusText = computed(() => {
  return props.connected ? "Connected" : "Disconnected";
});

const statusClass = computed(() => {
  return props.connected
    ? "bg-green-50 border-mqtt-green"
    : "bg-red-50 border-mqtt-red";
});

const statusTextClass = computed(() => {
  return props.connected ? "text-mqtt-green" : "text-mqtt-red";
});

const protocolDisplay = computed(() => {
  return props.useTls ? "MQTTS (TLS)" : "MQTT";
});

const connectionUrl = computed(() => {
  const protocol = props.useTls ? "mqtts" : "mqtt";
  return `${protocol}://${props.host}:${props.port}`;
});
</script>

<template>
  <div :class="['card border-2 transition-colors duration-300', statusClass]">
    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <h3 class="card-header mb-0">Connection Information</h3>
      <div class="flex items-center space-x-2">
        <span class="text-2xl">{{ statusIcon }}</span>
        <span :class="['text-sm font-semibold', statusTextClass]">
          {{ statusText }}
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

    <!-- Connection details -->
    <div v-else class="space-y-4">
      <!-- Broker endpoint -->
      <div>
        <div class="text-xs text-gray-500 mb-1">Broker Endpoint</div>
        <div class="text-sm font-medium text-gray-900 font-mono bg-gray-50 px-3 py-2 rounded border border-gray-200">
          {{ connectionUrl }}
        </div>
      </div>

      <!-- Connection details grid -->
      <div class="grid grid-cols-2 gap-4 pt-3 border-t border-gray-200">
        <!-- Host -->
        <div>
          <div class="text-xs text-gray-500 mb-1">Host</div>
          <div class="text-sm font-medium text-gray-900 font-mono">
            {{ host }}
          </div>
        </div>

        <!-- Port -->
        <div>
          <div class="text-xs text-gray-500 mb-1">Port</div>
          <div class="text-sm font-medium text-gray-900 font-mono">
            {{ port }}
          </div>
        </div>

        <!-- Protocol -->
        <div>
          <div class="text-xs text-gray-500 mb-1">Protocol</div>
          <div class="text-sm font-medium text-gray-900">
            {{ protocolDisplay }}
          </div>
        </div>

        <!-- Client ID -->
        <div>
          <div class="text-xs text-gray-500 mb-1">Client ID</div>
          <div class="text-sm font-medium text-gray-900 font-mono truncate" :title="clientId">
            {{ clientId }}
          </div>
        </div>

        <!-- Keepalive -->
        <div>
          <div class="text-xs text-gray-500 mb-1">Keepalive</div>
          <div class="text-sm font-medium text-gray-900">
            {{ keepalive }}s
          </div>
        </div>

        <!-- Version -->
        <div>
          <div class="text-xs text-gray-500 mb-1">Version</div>
          <div class="text-sm font-medium text-gray-900 font-mono">
            {{ version }}
          </div>
        </div>
      </div>

      <!-- Uptime -->
      <div class="pt-3 border-t border-gray-200">
        <div class="text-xs text-gray-500 mb-1">Uptime</div>
        <div class="text-sm font-medium text-gray-900">
          {{ uptime }}
        </div>
      </div>
    </div>
  </div>
</template>
