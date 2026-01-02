<script setup>
import { computed } from "vue";

const props = defineProps({
  title: {
    type: String,
    required: true,
  },
  value: {
    type: [String, Number],
    required: true,
  },
  unit: {
    type: String,
    default: "",
  },
  icon: {
    type: String,
    default: "",
  },
  trend: {
    type: String,
    validator: (value) => ["up", "down", "neutral", ""].includes(value),
    default: "",
  },
  trendValue: {
    type: String,
    default: "",
  },
  status: {
    type: String,
    validator: (value) => ["online", "offline", "warning", ""].includes(value),
    default: "",
  },
  loading: {
    type: Boolean,
    default: false,
  },
});

const trendIcon = computed(() => {
  if (props.trend === "up") return "↑";
  if (props.trend === "down") return "↓";
  if (props.trend === "neutral") return "→";
  return "";
});

const trendClass = computed(() => {
  if (props.trend === "up") return "text-mqtt-green";
  if (props.trend === "down") return "text-mqtt-red";
  if (props.trend === "neutral") return "text-gray-500";
  return "";
});

const statusDotClass = computed(() => {
  if (props.status === "online") return "status-online";
  if (props.status === "offline") return "status-offline";
  if (props.status === "warning") return "status-warning";
  return "";
});
</script>

<template>
  <div class="card">
    <!-- Header with title and status indicator -->
    <div class="flex items-start justify-between mb-2">
      <div class="flex items-center space-x-2">
        <span v-if="icon" class="text-2xl">{{ icon }}</span>
        <h3 class="text-sm font-medium text-gray-600">{{ title }}</h3>
      </div>
      <span
        v-if="status"
        :class="['status-dot', statusDotClass]"
        :title="status.charAt(0).toUpperCase() + status.slice(1)"
      ></span>
    </div>

    <!-- Value display -->
    <div class="mb-1">
      <div v-if="loading" class="animate-pulse">
        <div class="h-8 bg-gray-200 rounded w-24"></div>
      </div>
      <div v-else class="flex items-baseline space-x-1">
        <span class="text-3xl font-bold text-gray-900">{{ value }}</span>
        <span v-if="unit" class="text-sm font-medium text-gray-500">{{ unit }}</span>
      </div>
    </div>

    <!-- Trend indicator -->
    <div v-if="trend && trendValue" class="flex items-center space-x-1">
      <span :class="['text-sm font-medium', trendClass]">
        {{ trendIcon }} {{ trendValue }}
      </span>
    </div>
  </div>
</template>
