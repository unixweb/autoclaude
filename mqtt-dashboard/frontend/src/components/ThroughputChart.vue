<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { Line } from "vue-chartjs";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import { useChartData } from "../composables/useChartData.js";

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

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

// Create chart data managers for received and sent messages
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
          received: newStats.messages_received_1min || 0,
          sent: newStats.messages_sent_1min || 0,
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
    },
    y: {
      display: true,
      title: {
        display: true,
        text: "Messages/min",
      },
      beginAtZero: true,
      ticks: {
        precision: 0,
      },
    },
  },
};

// Computed chart data
const chartDataset = computed(() => ({
  labels: chartData.labels.value,
  datasets: [
    {
      label: "Received",
      data: chartData.getValues("received"),
      borderColor: "rgb(16, 185, 129)", // mqtt-green
      backgroundColor: "rgba(16, 185, 129, 0.1)",
      fill: true,
      tension: 0.4,
      pointRadius: 2,
      pointHoverRadius: 4,
    },
    {
      label: "Sent",
      data: chartData.getValues("sent"),
      borderColor: "rgb(59, 130, 246)", // blue-500
      backgroundColor: "rgba(59, 130, 246, 0.1)",
      fill: true,
      tension: 0.4,
      pointRadius: 2,
      pointHoverRadius: 4,
    },
  ],
}));

// Handle time window change
const changeTimeWindow = (window) => {
  selectedTimeWindow.value = window;
};
</script>

<template>
  <div class="card">
    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <div>
        <h3 class="text-lg font-semibold text-gray-900">Message Throughput</h3>
        <p class="text-sm text-gray-600">Messages per minute over time</p>
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

    <!-- Chart -->
    <div class="h-64 w-full">
      <Line
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
