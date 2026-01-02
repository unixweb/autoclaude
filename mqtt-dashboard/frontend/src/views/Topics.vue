<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { topicsApi, getSocket, connectSocket } from "../api/client.js";
import TopicList from "../components/TopicList.vue";
import TopicSubscriber from "../components/TopicSubscriber.vue";
import StatCard from "../components/StatCard.vue";

// State
const loading = ref(true);
const topicsData = ref(null);
const wsConnected = ref(false);
const searchQuery = ref("");
const filterPattern = ref("");
const selectedTopic = ref(null);
const showSubscriber = ref(false);

// Fetch topics data
const fetchTopics = async () => {
  try {
    loading.value = true;
    const params = {};

    if (filterPattern.value) {
      params.filter = filterPattern.value;
    }

    const data = await topicsApi.getTopics(params);
    topicsData.value = data;
  } catch (error) {
    console.error("Failed to fetch topics:", error);
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
    });

    socket.on("disconnect", () => {
      wsConnected.value = false;
    });

    wsConnected.value = socket.connected;
  } catch (error) {
    console.error("WebSocket connection failed:", error);
  }
};

// Computed values
const topics = computed(() => topicsData.value?.topics || []);
const totalCount = computed(() => topicsData.value?.total || 0);
const filteredCount = computed(() => topicsData.value?.filtered || 0);

// Filter topics based on search query
const filteredTopics = computed(() => {
  if (!searchQuery.value) return topics.value;

  const query = searchQuery.value.toLowerCase();
  return topics.value.filter((topic) =>
    topic.topic.toLowerCase().includes(query) ||
    (topic.last_payload && topic.last_payload.toLowerCase().includes(query))
  );
});

// Apply filter pattern
const applyFilter = () => {
  fetchTopics();
};

// Clear filter
const clearFilter = () => {
  filterPattern.value = "";
  fetchTopics();
};

// Handle topic selection for subscription
const handleTopicSelect = (topic) => {
  selectedTopic.value = topic;
  showSubscriber.value = true;
};

// Handle subscriber close
const handleSubscriberClose = () => {
  showSubscriber.value = false;
  selectedTopic.value = null;
};

// Format time ago
const formatTimeAgo = (timestamp) => {
  if (!timestamp) return "Never";

  const date = new Date(timestamp);
  const now = new Date();
  const seconds = Math.floor((now - date) / 1000);

  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
};

// Auto-refresh interval
let refreshInterval = null;

// Lifecycle hooks
onMounted(() => {
  fetchTopics();
  initWebSocket();

  // Auto-refresh every 10 seconds
  refreshInterval = setInterval(() => {
    if (!showSubscriber.value) {
      fetchTopics();
    }
  }, 10000);
});

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
});
</script>

<template>
  <div class="space-y-6">
    <!-- Page header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Topics Explorer</h1>
        <p class="text-sm text-gray-600 mt-1">
          Explore and monitor active MQTT topics
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

    <!-- Statistics Cards -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <StatCard
        title="Total Topics"
        :value="totalCount"
        icon="📋"
        :loading="loading"
      />
      <StatCard
        title="Active Topics"
        :value="filteredCount"
        icon="📡"
        status="online"
        :loading="loading"
      />
      <StatCard
        title="Filtered Results"
        :value="filteredTopics.length"
        icon="🔍"
        :loading="loading"
      />
    </div>

    <!-- Filter Controls -->
    <div class="card">
      <h2 class="card-header mb-4">Filter Topics</h2>
      <div class="flex flex-col md:flex-row gap-3">
        <div class="flex-1">
          <label class="block text-xs font-medium text-gray-700 mb-1">
            MQTT Pattern Filter (supports # and + wildcards)
          </label>
          <input
            v-model="filterPattern"
            type="text"
            placeholder="e.g., home/+/temperature or sensor/#"
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-mqtt-blue focus:border-transparent"
            @keyup.enter="applyFilter"
          />
        </div>
        <div class="flex-1">
          <label class="block text-xs font-medium text-gray-700 mb-1">
            Search Topics
          </label>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search by topic name or payload..."
            class="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-mqtt-blue focus:border-transparent"
          />
        </div>
        <div class="flex items-end gap-2">
          <button
            @click="applyFilter"
            class="btn-primary px-4 py-2 text-sm"
          >
            Apply Filter
          </button>
          <button
            v-if="filterPattern"
            @click="clearFilter"
            class="btn-secondary px-4 py-2 text-sm"
          >
            Clear
          </button>
        </div>
      </div>
    </div>

    <!-- Topics List -->
    <div class="card">
      <div class="flex items-center justify-between mb-4">
        <h2 class="card-header mb-0">Active Topics</h2>
        <button
          @click="fetchTopics"
          class="btn-secondary px-3 py-1 text-sm"
          :disabled="loading"
        >
          🔄 Refresh
        </button>
      </div>

      <TopicList
        :topics="filteredTopics"
        :loading="loading"
        @select-topic="handleTopicSelect"
      />
    </div>

    <!-- Topic Subscriber Modal -->
    <TopicSubscriber
      v-if="showSubscriber"
      :topic="selectedTopic"
      @close="handleSubscriberClose"
    />

    <!-- Info Note -->
    <div class="card bg-blue-50 border border-blue-200">
      <div class="flex items-start space-x-3">
        <span class="text-2xl">ℹ️</span>
        <div class="flex-1">
          <h3 class="text-sm font-semibold text-blue-900 mb-1">
            About Topic Tracking
          </h3>
          <p class="text-sm text-blue-800 mb-2">
            Topics are tracked by monitoring message traffic. Only topics that have had recent activity will appear in this list.
            Click on any topic to subscribe and view live messages.
          </p>
          <p class="text-sm text-blue-800">
            <strong>Wildcard patterns:</strong> Use <code class="bg-blue-100 px-1 rounded">#</code> for multi-level wildcard
            and <code class="bg-blue-100 px-1 rounded">+</code> for single-level wildcard.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
