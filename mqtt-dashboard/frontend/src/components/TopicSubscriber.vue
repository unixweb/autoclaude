<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { getSocket, connectSocket } from "../api/client.js";

const props = defineProps({
  topic: {
    type: String,
    required: true,
  },
});

const emit = defineEmits(["close"]);

// State
const wsConnected = ref(false);
const subscribed = ref(false);
const messages = ref([]);
const isPaused = ref(false);
const maxMessages = ref(100);
const subscribedTopic = ref("");

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
const truncatePayload = (payload, maxLength = 200) => {
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

// Subscribe to topic
const subscribe = async () => {
  try {
    await connectSocket();
    const socket = getSocket();

    if (!socket.connected) {
      console.error("WebSocket not connected");
      return;
    }

    // Subscribe to the topic
    socket.emit("subscribe_topic", { topic: props.topic });

    // Listen for messages on this topic
    socket.on("topic_message", handleTopicMessage);

    subscribed.value = true;
    subscribedTopic.value = props.topic;
  } catch (error) {
    console.error("Failed to subscribe to topic:", error);
  }
};

// Unsubscribe from topic
const unsubscribe = () => {
  const socket = getSocket();
  if (socket && socket.connected && subscribedTopic.value) {
    socket.emit("unsubscribe_topic", { topic: subscribedTopic.value });
    socket.off("topic_message", handleTopicMessage);
  }
  subscribed.value = false;
  subscribedTopic.value = "";
};

// Handle incoming topic message
const handleTopicMessage = (data) => {
  if (!data || !data.topic) return;

  // Only add message if not paused
  if (!isPaused.value) {
    const message = {
      id: Date.now() + Math.random(),
      topic: data.topic,
      payload: data.payload,
      timestamp: data.timestamp || new Date().toISOString(),
      subscription: data.subscription,
    };

    messages.value.unshift(message);

    // Limit message history
    if (messages.value.length > maxMessages.value) {
      messages.value = messages.value.slice(0, maxMessages.value);
    }
  }
};

// Clear messages
const clearMessages = () => {
  messages.value = [];
};

// Toggle pause
const togglePause = () => {
  isPaused.value = !isPaused.value;
};

// Close modal
const close = () => {
  unsubscribe();
  emit("close");
};

// Message count
const messageCount = computed(() => messages.value.length);

// Initialize WebSocket connection
const initWebSocket = async () => {
  try {
    await connectSocket();
    const socket = getSocket();

    socket.on("connect", () => {
      wsConnected.value = true;
      // Re-subscribe if we were subscribed before disconnect
      if (subscribed.value) {
        subscribe();
      }
    });

    socket.on("disconnect", () => {
      wsConnected.value = false;
      subscribed.value = false;
    });

    wsConnected.value = socket.connected;
  } catch (error) {
    console.error("WebSocket connection failed:", error);
  }
};

// Watch for topic changes
watch(() => props.topic, (newTopic, oldTopic) => {
  if (newTopic !== oldTopic) {
    // Unsubscribe from old topic and subscribe to new one
    if (subscribed.value) {
      unsubscribe();
    }
    clearMessages();
    subscribe();
  }
});

// Lifecycle hooks
onMounted(() => {
  initWebSocket();
  subscribe();
});

onUnmounted(() => {
  unsubscribe();
});
</script>

<template>
  <!-- Modal Overlay -->
  <div
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
    @click.self="close"
  >
    <!-- Modal Container -->
    <div class="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col">
      <!-- Modal Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200">
        <div class="flex-1 min-w-0 mr-4">
          <h2 class="text-xl font-bold text-gray-900 mb-1">Topic Subscriber</h2>
          <p class="text-sm font-mono text-gray-600 truncate" :title="topic">
            {{ topic }}
          </p>
        </div>
        <div class="flex items-center space-x-3">
          <!-- Connection Status -->
          <span
            :class="[
              'inline-flex items-center px-3 py-1 rounded-full text-xs font-medium',
              subscribed && wsConnected
                ? 'bg-green-100 text-green-800'
                : 'bg-gray-100 text-gray-800',
            ]"
          >
            <span
              :class="[
                'w-2 h-2 rounded-full mr-2',
                subscribed && wsConnected ? 'bg-mqtt-green animate-pulse-slow' : 'bg-gray-400',
              ]"
            ></span>
            {{ subscribed && wsConnected ? "Subscribed" : "Not Subscribed" }}
          </span>
          <!-- Close Button -->
          <button
            @click="close"
            class="text-gray-400 hover:text-gray-600 focus:outline-none"
          >
            <span class="text-2xl">&times;</span>
          </button>
        </div>
      </div>

      <!-- Modal Content -->
      <div class="flex-1 overflow-hidden flex flex-col">
        <!-- Controls -->
        <div class="px-6 py-3 bg-gray-50 border-b border-gray-200">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-3">
              <!-- Message Count -->
              <span class="text-sm text-gray-600">
                <strong>{{ messageCount }}</strong> messages
              </span>
              <!-- Pause Indicator -->
              <span
                v-if="isPaused"
                class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-yellow-100 text-yellow-800"
              >
                ⏸️ Paused
              </span>
            </div>
            <div class="flex items-center space-x-2">
              <!-- Pause/Resume Button -->
              <button
                @click="togglePause"
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
                @click="clearMessages"
                class="btn-secondary px-3 py-1 text-sm"
                :disabled="messageCount === 0"
              >
                🗑️ Clear
              </button>
            </div>
          </div>
        </div>

        <!-- Messages List -->
        <div class="flex-1 overflow-y-auto px-6 py-4">
          <!-- Empty State -->
          <div
            v-if="messageCount === 0"
            class="flex flex-col items-center justify-center h-full text-center py-12"
          >
            <span class="text-6xl mb-4">📡</span>
            <p class="text-gray-500 text-sm mb-1">
              {{ subscribed ? "Waiting for messages..." : "Not subscribed" }}
            </p>
            <p class="text-gray-400 text-xs">
              Messages published to this topic will appear here
            </p>
          </div>

          <!-- Messages -->
          <div v-else class="space-y-3">
            <div
              v-for="message in messages"
              :key="message.id"
              class="border border-gray-200 rounded-lg p-4 hover:border-mqtt-blue transition-colors"
            >
              <!-- Message Header -->
              <div class="flex items-start justify-between mb-2">
                <div class="flex items-center space-x-2 min-w-0 flex-1">
                  <span class="text-sm font-medium text-gray-700">Topic:</span>
                  <span class="text-sm font-mono text-gray-900 truncate" :title="message.topic">
                    {{ message.topic }}
                  </span>
                </div>
                <div class="flex items-center space-x-2 flex-shrink-0 ml-2">
                  <span class="text-xs text-gray-500">
                    {{ formatTimestamp(message.timestamp) }}
                  </span>
                  <span
                    v-if="isJsonPayload(message.payload)"
                    class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800"
                  >
                    JSON
                  </span>
                </div>
              </div>

              <!-- Message Payload -->
              <div class="mt-2">
                <div class="text-xs text-gray-500 mb-1">Payload:</div>
                <div
                  v-if="isJsonPayload(message.payload)"
                  class="bg-gray-50 rounded p-3 overflow-x-auto"
                >
                  <pre class="text-xs font-mono text-gray-800">{{ formatJsonPayload(message.payload) }}</pre>
                </div>
                <div
                  v-else
                  class="bg-gray-50 rounded p-3 break-all"
                >
                  <code class="text-xs font-mono text-gray-800">{{ message.payload }}</code>
                </div>
              </div>

              <!-- Full Timestamp -->
              <div class="mt-2 text-xs text-gray-400" :title="message.timestamp">
                Received: {{ formatFullTimestamp(message.timestamp) }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Modal Footer -->
      <div class="px-6 py-4 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
        <div class="text-sm text-gray-600">
          <span class="font-medium">Tip:</span> Use the pause button to stop receiving new messages while inspecting the current ones.
        </div>
        <button
          @click="close"
          class="btn-primary px-4 py-2 text-sm"
        >
          Close
        </button>
      </div>
    </div>
  </div>
</template>
