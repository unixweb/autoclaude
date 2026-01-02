<script setup>
import { computed } from "vue";

const props = defineProps({
  topics: {
    type: Array,
    required: true,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["select-topic"]);

// Format timestamp to relative time
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

// Format timestamp to human-readable date
const formatDate = (timestamp) => {
  if (!timestamp) return "N/A";
  return new Date(timestamp).toLocaleString();
};

// Truncate long payloads
const truncatePayload = (payload, maxLength = 100) => {
  if (!payload) return "N/A";
  if (payload.length <= maxLength) return payload;
  return payload.substring(0, maxLength) + "...";
};

// Get QoS badge styling
const getQosBadgeClass = (qos) => {
  switch (qos) {
    case 0:
      return "bg-gray-100 text-gray-800";
    case 1:
      return "bg-blue-100 text-blue-800";
    case 2:
      return "bg-purple-100 text-purple-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
};

// Check if there are no results
const hasNoResults = computed(() => {
  return !props.loading && props.topics.length === 0;
});

// Handle topic selection
const selectTopic = (topic) => {
  emit("select-topic", topic.topic);
};
</script>

<template>
  <div>
    <!-- Loading state -->
    <div v-if="loading" class="space-y-3">
      <div
        v-for="i in 5"
        :key="i"
        class="animate-pulse flex items-center space-x-4 p-4 border border-gray-200 rounded-lg"
      >
        <div class="flex-1 space-y-2">
          <div class="h-4 bg-gray-200 rounded w-3/4"></div>
          <div class="h-3 bg-gray-200 rounded w-1/2"></div>
        </div>
        <div class="h-4 bg-gray-200 rounded w-16"></div>
      </div>
    </div>

    <!-- Empty state -->
    <div
      v-else-if="hasNoResults"
      class="text-center py-12"
    >
      <span class="text-5xl mb-4 block">📭</span>
      <p class="text-gray-500 text-sm mb-1">No topics found</p>
      <p class="text-gray-400 text-xs">
        Topics will appear here once messages are published
      </p>
    </div>

    <!-- Data Display -->
    <div v-else>
      <!-- Desktop Table -->
      <div class="hidden md:block overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th
              scope="col"
              class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Topic
            </th>
            <th
              scope="col"
              class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Last Payload
            </th>
            <th
              scope="col"
              class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Messages
            </th>
            <th
              scope="col"
              class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              QoS
            </th>
            <th
              scope="col"
              class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Last Seen
            </th>
            <th
              scope="col"
              class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Actions
            </th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr
            v-for="topic in topics"
            :key="topic.topic"
            class="hover:bg-gray-50 transition-colors"
          >
            <td class="px-6 py-4">
              <div class="flex items-center">
                <span class="text-lg mr-2">📋</span>
                <div>
                  <div class="text-sm font-mono font-medium text-gray-900 break-all">
                    {{ topic.topic }}
                  </div>
                  <div
                    v-if="topic.last_retained"
                    class="flex items-center mt-1"
                  >
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                      💾 Retained
                    </span>
                  </div>
                </div>
              </div>
            </td>
            <td class="px-6 py-4">
              <div class="text-sm text-gray-600 font-mono max-w-xs truncate" :title="topic.last_payload">
                {{ truncatePayload(topic.last_payload, 50) }}
              </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="text-sm font-bold text-gray-900">
                {{ topic.message_count || 0 }}
              </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <span
                v-if="topic.last_qos !== null && topic.last_qos !== undefined"
                :class="[
                  'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                  getQosBadgeClass(topic.last_qos),
                ]"
              >
                QoS {{ topic.last_qos }}
              </span>
              <span v-else class="text-xs text-gray-400">N/A</span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="text-sm text-gray-600">
                {{ formatTimeAgo(topic.last_seen) }}
              </div>
              <div class="text-xs text-gray-400" :title="formatDate(topic.last_seen)">
                {{ formatDate(topic.last_seen) }}
              </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <button
                @click="selectTopic(topic)"
                class="text-mqtt-blue hover:text-mqtt-blue-dark text-sm font-medium focus:outline-none focus:underline"
              >
                Subscribe 📡
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      </div>

      <!-- Mobile Cards -->
      <div class="md:hidden space-y-3">
      <div
        v-for="topic in topics"
        :key="topic.topic"
        class="border border-gray-200 rounded-lg p-4 hover:border-mqtt-blue transition-colors"
      >
        <!-- Header -->
        <div class="flex items-start justify-between mb-3">
          <div class="flex items-start space-x-2 flex-1 min-w-0">
            <span class="text-lg flex-shrink-0">📋</span>
            <div class="min-w-0 flex-1">
              <h3 class="text-sm font-mono font-medium text-gray-900 break-all">
                {{ topic.topic }}
              </h3>
              <div class="flex items-center gap-2 mt-1">
                <span
                  v-if="topic.last_qos !== null && topic.last_qos !== undefined"
                  :class="[
                    'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                    getQosBadgeClass(topic.last_qos),
                  ]"
                >
                  QoS {{ topic.last_qos }}
                </span>
                <span
                  v-if="topic.last_retained"
                  class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800"
                >
                  💾 Retained
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Last Payload -->
        <div class="mb-3 pb-3 border-b border-gray-200">
          <div class="text-xs text-gray-500 mb-1">Last Payload:</div>
          <div class="text-sm text-gray-700 font-mono break-all">
            {{ truncatePayload(topic.last_payload, 80) }}
          </div>
        </div>

        <!-- Stats -->
        <div class="grid grid-cols-2 gap-3 mb-3">
          <div>
            <div class="text-xs text-gray-500">Messages</div>
            <div class="text-lg font-bold text-gray-900">
              {{ topic.message_count || 0 }}
            </div>
          </div>
          <div>
            <div class="text-xs text-gray-500">Last Seen</div>
            <div class="text-sm text-gray-900">
              {{ formatTimeAgo(topic.last_seen) }}
            </div>
          </div>
        </div>

        <!-- Action Button -->
        <button
          @click="selectTopic(topic)"
          class="w-full btn-primary py-2 text-sm"
        >
          📡 Subscribe to Topic
        </button>
      </div>
      </div>
    </div>
  </div>
</template>
