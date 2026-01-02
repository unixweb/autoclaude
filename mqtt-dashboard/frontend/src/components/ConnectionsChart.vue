<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { Bar } from "vue-chartjs";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { useChartData } from "../composables/useChartData.js";

// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const props = defineProps({
  brokerStats: {
    type: Object,
    default: null,
  },
  timeWindow: {
    type: Number,
    default: 60, // 60 seconds = 1 minute
  },
});

// Time window options
const timeWindows = [
  { label: "1 min", value: 60 },
  { label: "5 min", value: 300 },
  { label: "15 min", value: 900 },
];

const selectedTimeWindow = ref(props.timeWindow);

// Create chart data manager
const maxDataPoints = computed(() => {
  // Adjust max data points based on time window
  // Assuming updates every 5 seconds
  return Math.ceil(selectedTimeWindow.value / 5);
});

const chartData = useChartData({
  maxDataPoints: maxDataPoints.value,
  timeWindow: selectedTimeWindow.value,
});

// Watch for broker stats changes and add data points
watch(
  () => props.brokerStats,
  (newStats) => {
    if (newStats) {
      chartData.addDataPoint({
        value: {
          connected: newStats.clients_connected || 0,
          disconnected: newStats.clients_disconnected || 0,
          total: newStats.clients_total || 0,
        },
      });
    }
  }
);

// Watch for time window changes
watch(selectedTimeWindow, (newWindow) => {
  chartData.setTimeWindow(newWindow);
});

// Chart configuration
const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: "index",
    intersect: false,
  },
  plugins: {
    legend: {
      display: true,
      position: "top",
    },
    title: {
      display: false,
    },
    tooltip: {
      enabled: true,
      mode: "index",
      intersect: false,
    },
  },
  scales: {
    x: {
      display: true,
      title: {
        display: true,
        text: "Time",
      },
      ticks: {
        maxRotation: 45,
        minRotation: 45,
        autoSkip: true,
        maxTicksLimit: 10,
      },
      stacked: true,
    },
    y: {
      display: true,
      title: {
        display: true,
        text: "Client Count",
      },
      beginAtZero: true,
      ticks: {
        precision: 0,
      },
      stacked: true,
    },
  },
};

// Computed chart data
const chartDataset = computed(() => ({
  labels: chartData.labels.value,
  datasets: [
    {
      label: "Connected",
      data: chartData.getValues("connected"),
      backgroundColor: "rgba(16, 185, 129, 0.8)", // mqtt-green
      borderColor: "rgb(16, 185, 129)",
      borderWidth: 1,
    },
    {
      label: "Disconnected",
      data: chartData.getValues("disconnected"),
      backgroundColor: "rgba(239, 68, 68, 0.8)", // red-500
      borderColor: "rgb(239, 68, 68)",
      borderWidth: 1,
    },
  ],
}));

// Handle time window change
const changeTimeWindow = (window) => {
  selectedTimeWindow.value = window;
};

// Current client stats
const currentStats = computed(() => {
  if (!chartData.latestValue.value) {
    return {
      connected: 0,
      disconnected: 0,
      total: 0,
    };
  }
  return chartData.latestValue.value;
});
</script>

<template>
  <div class="card">
    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <div>
        <h3 class="text-lg font-semibold text-gray-900">Client Connections</h3>
        <p class="text-sm text-gray-600">
          Connected and disconnected clients over time
        </p>
      </div>

      <!-- Time window selector -->
      <div class="flex items-center space-x-2">
        <span class="text-sm text-gray-600">Window:</span>
        <div class="inline-flex rounded-lg border border-gray-200 bg-white p-1">
          <button
            v-for="window in timeWindows"
            :key="window.value"
            @click="changeTimeWindow(window.value)"
            :class="[
              'px-3 py-1 text-sm font-medium rounded-md transition-colors',
              selectedTimeWindow === window.value
                ? 'bg-mqtt-green text-white'
                : 'text-gray-700 hover:bg-gray-100',
            ]"
          >
            {{ window.label }}
          </button>
        </div>
      </div>
    </div>

    <!-- Current stats summary -->
    <div class="flex items-center justify-around mb-4 p-3 bg-gray-50 rounded-lg">
      <div class="text-center">
        <p class="text-sm text-gray-600">Connected</p>
        <p class="text-2xl font-bold text-mqtt-green">
          {{ currentStats.connected }}
        </p>
      </div>
      <div class="text-center">
        <p class="text-sm text-gray-600">Disconnected</p>
        <p class="text-2xl font-bold text-red-500">
          {{ currentStats.disconnected }}
        </p>
      </div>
      <div class="text-center">
        <p class="text-sm text-gray-600">Total</p>
        <p class="text-2xl font-bold text-gray-700">
          {{ currentStats.total }}
        </p>
      </div>
    </div>

    <!-- Chart -->
    <div class="h-64 w-full">
      <Bar
        v-if="!chartData.isEmpty.value"
        :data="chartDataset"
        :options="chartOptions"
      />
      <div
        v-else
        class="h-full flex items-center justify-center text-gray-400"
      >
        <div class="text-center">
          <p class="text-lg">📊</p>
          <p class="text-sm mt-2">Waiting for data...</p>
        </div>
      </div>
    </div>
  </div>
</template>
