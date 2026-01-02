<script setup>
import { ref, computed } from "vue";

const props = defineProps({
  messages: {
    type: Array,
    required: true,
    default: () => [],
  },
  isPaused: {
    type: Boolean,
    default: false,
  },
  messageCount: {
    type: Number,
    default: 0,
  },
});

const emit = defineEmits(["toggle-pause", "clear-messages"]);

// Expanded message state (for showing full payload)
const expandedMessages = ref(new Set());

// Toggle message expansion
const toggleExpand = (messageId) => {
  if (expandedMessages.value.has(messageId)) {
    expandedMessages.value.delete(messageId);
  } else {
    expandedMessages.value.add(messageId);
  }
  // Trigger reactivity
  expandedMessages.value = new Set(expandedMessages.value);
};

// Check if message is expanded
const isExpanded = (messageId) => {
  return expandedMessages.value.has(messageId);
};

// Format timestamp
const formatTimestamp = (timestamp) => {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  return date.toLocaleTimeString() + "." + String(date.getMilliseconds()).padStart(3, "0");
};

// Format full timestamp
const formatFullTimestamp = (timestamp) => {
  if (!timestamp) return "";
  return new Date(timestamp).toLocaleString();
};

// Truncate long payloads
const truncatePayload = (payload, maxLength = 100) => {
  if (!payload) return "";
  if (payload.length <= maxLength) return payload;
  return payload.substring(0, maxLength) + "...";
};

// Check if payload is JSON
const isJsonPayload = (payload) => {
  try {
    JSON.parse(payload);
    return true;
  } catch {
    return false;
  }
};

// Format JSON payload
const formatJsonPayload = (payload) => {
  try {
    const parsed = JSON.parse(payload);
    return JSON.stringify(parsed, null, 2);
  } catch {
    return payload;
  }
};

// Get badge color for topic
const getTopicBadgeColor = (topic) => {
  if (topic.startsWith("$SYS")) return "bg-purple-100 text-purple-800";
  if (topic.includes("/status")) return "bg-blue-100 text-blue-800";
  if (topic.includes("/sensor")) return "bg-green-100 text-green-800";
  if (topic.includes("/command")) return "bg-orange-100 text-orange-800";
  return "bg-gray-100 text-gray-800";
};

// Handle pause toggle
const handleTogglePause = () => {
  emit("toggle-pause");
};

// Handle clear messages
const handleClearMessages = () => {
  expandedMessages.value.clear();
  emit("clear-messages");
};
</script>

<template>
  <div class="card">
    <!-- Feed Header -->
    <div class="flex items-center justify-between mb-4">
      <h2 class="card-header mb-0">Message Feed</h2>
      <div class="flex items-center space-x-2">
        <!-- Pause/Resume Button -->
        <button
          @click="handleTogglePause"
          :class="[
            'px-3 py-1 text-sm rounded-md focus:outline-none focus:ring-2 focus:ring-mqtt-blue',
            isPaused
              ? 'bg-green-100 text-green-800 hover:bg-green-200'
              : 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200',
          ]"
        >
          {{ isPaused ? "▶️ Resume" : "⏸️ Pause" }}
        </button>
        <!-- Clear Button -->
        <button
          @click="handleClearMessages"
          class="btn-secondary px-3 py-1 text-sm"
          :disabled="messageCount === 0"
        >
          🗑️ Clear
        </button>
      </div>
    </div>

    <!-- Feed Status Bar -->
    <div class="mb-4 px-4 py-2 bg-gray-50 rounded-md flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <span class="text-sm text-gray-600">
          <strong>{{ messageCount }}</strong> messages
        </span>
        <span
          v-if="isPaused"
          class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-yellow-100 text-yellow-800"
        >
          ⏸️ Paused
        </span>
      </div>
      <div class="text-xs text-gray-500">
        Click on a message to expand payload
      </div>
    </div>

    <!-- Messages List -->
    <div class="overflow-y-auto max-h-[600px]">
      <!-- Empty State -->
      <div
        v-if="messageCount === 0"
        class="flex flex-col items-center justify-center py-16 text-center"
      >
        <span class="text-6xl mb-4">📡</span>
        <p class="text-gray-500 text-sm mb-1">
          No messages yet
        </p>
        <p class="text-gray-400 text-xs">
          Subscribe to topics to start receiving messages
        </p>
      </div>

      <!-- Messages -->
      <div v-else class="space-y-2">
        <div
          v-for="message in messages"
          :key="message.id"
          :class="[
            'border rounded-lg p-3 transition-colors cursor-pointer',
            isExpanded(message.id)
              ? 'border-mqtt-blue bg-blue-50'
              : 'border-gray-200 hover:border-mqtt-blue hover:bg-gray-50',
          ]"
          @click="toggleExpand(message.id)"
        >
          <!-- Message Header -->
          <div class="flex items-center justify-between mb-1">
            <div class="flex items-center space-x-2 min-w-0 flex-1">
              <span
                :class="[
                  'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium flex-shrink-0',
                  getTopicBadgeColor(message.topic),
                ]"
              >
                {{ message.topic }}
              </span>
              <span
                v-if="isJsonPayload(message.payload)"
                class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 flex-shrink-0"
              >
                JSON
              </span>
            </div>
            <div class="flex items-center space-x-2 flex-shrink-0">
              <span class="text-xs text-gray-500">
                {{ formatTimestamp(message.timestamp) }}
              </span>
              <span class="text-gray-400 text-xs">
                {{ isExpanded(message.id) ? "▼" : "▶" }}
              </span>
            </div>
          </div>

          <!-- Message Payload Preview/Full -->
          <div class="mt-2">
            <div v-if="!isExpanded(message.id)" class="text-xs text-gray-600">
              {{ truncatePayload(message.payload, 100) }}
            </div>
            <div v-else>
              <div class="text-xs text-gray-500 mb-1 font-medium">Payload:</div>
              <div
                v-if="isJsonPayload(message.payload)"
                class="bg-white rounded p-3 overflow-x-auto border border-gray-200"
              >
                <pre class="text-xs font-mono text-gray-800">{{ formatJsonPayload(message.payload) }}</pre>
              </div>
              <div
                v-else
                class="bg-white rounded p-3 break-all border border-gray-200"
              >
                <code class="text-xs font-mono text-gray-800">{{ message.payload }}</code>
              </div>
              <div class="mt-2 text-xs text-gray-400">
                Received: {{ formatFullTimestamp(message.timestamp) }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
