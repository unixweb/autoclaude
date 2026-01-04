<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { getSocket, connectSocket } from "../api/client.js";
import MessageFeed from "../components/MessageFeed.vue";
import SubscriptionManager from "../components/SubscriptionManager.vue";
import StatCard from "../components/StatCard.vue";

// State
const wsConnected = ref(false);
const subscriptions = ref([]);
const messages = ref([]);
const isPaused = ref(false);
const maxMessages = ref(500);

// Message count by topic
const messageCountByTopic = computed(() => {
  const counts = {};
  subscriptions.value.forEach(sub => {
    counts[sub] = messages.value.filter(msg => msg.topic === sub || matchesTopic(msg.topic, sub)).length;
  });
  return counts;
});

// Total message count
const totalMessageCount = computed(() => messages.value.length);

// Active subscription count
const activeSubscriptionCount = computed(() => subscriptions.value.length);

// Match topic against subscription pattern
const matchesTopic = (topic, pattern) => {
  // Convert MQTT wildcards to regex
  const regexPattern = pattern
    .replace(/\+/g, '[^/]+')
    .replace(/#/g, '.*');
  const regex = new RegExp(`^${regexPattern}$`);
  return regex.test(topic);
};

// Initialize WebSocket connection
const initWebSocket = async () => {
  try {
    await connectSocket();
    const socket = getSocket();

    socket.on("connect", () => {
      console.log('Socket connected!');
      wsConnected.value = true;
      // Re-subscribe to all topics after reconnection
      subscriptions.value.forEach(topic => {
        socket.emit("subscribe_topic", { topic });
      });
    });

    socket.on("disconnect", () => {
      console.log('Socket disconnected!');
      wsConnected.value = false;
    });

    // Listen for topic messages
    socket.on("topic_message", handleTopicMessage);

    // Set initial state
    if (socket.connected) {
      console.log('Socket already connected');
      wsConnected.value = true;
    } else {
      console.log('Waiting for socket to connect...');
    }
  } catch (error) {
    console.error("WebSocket connection failed:", error);
  }
};

// Handle incoming topic message
const handleTopicMessage = (data) => {
  if (!data || !data.topic) return;

  // Check if message matches any subscription
  const matchesAnySubscription = subscriptions.value.some(sub =>
    data.topic === sub || matchesTopic(data.topic, sub)
  );

  if (!matchesAnySubscription) return;

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

// Add subscription
const addSubscription = (topic) => {
  if (!topic || subscriptions.value.includes(topic)) return;

  const socket = getSocket();
  console.log('addSubscription called:', { topic, connected: socket?.connected, wsConnected: wsConnected.value });

  // Always try to emit if we think we're connected
  if (socket) {
    socket.emit("subscribe_topic", { topic });
    subscriptions.value.push(topic);
    console.log('Emitted subscribe_topic for:', topic);
  } else {
    console.error('Socket not available!');
  }
};

// Remove subscription
const removeSubscription = (topic) => {
  const socket = getSocket();
  if (socket && socket.connected) {
    socket.emit("unsubscribe_topic", { topic });
  }

  subscriptions.value = subscriptions.value.filter(sub => sub !== topic);

  // Optionally remove messages from this topic
  // messages.value = messages.value.filter(msg => !matchesTopic(msg.topic, topic));
};

// Clear all subscriptions
const clearAllSubscriptions = () => {
  const socket = getSocket();
  if (socket && socket.connected) {
    subscriptions.value.forEach(topic => {
      socket.emit("unsubscribe_topic", { topic });
    });
  }
  subscriptions.value = [];
  messages.value = [];
};

// Clear messages
const clearMessages = () => {
  messages.value = [];
};

// Toggle pause
const togglePause = () => {
  isPaused.value = !isPaused.value;
};

// Cleanup
const cleanup = () => {
  const socket = getSocket();
  if (socket) {
    socket.off("topic_message", handleTopicMessage);

    // Unsubscribe from all topics
    subscriptions.value.forEach(topic => {
      socket.emit("unsubscribe_topic", { topic });
    });
  }
};

// Lifecycle hooks
onMounted(() => {
  initWebSocket();
});

onUnmounted(() => {
  cleanup();
});
</script>

<template>
  <div class="space-y-6">
    <!-- Page header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Live Monitor</h1>
        <p class="text-sm text-gray-600 mt-1">
          Subscribe to topics and monitor messages in real-time
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
        title="Active Subscriptions"
        :value="activeSubscriptionCount"
        icon="📡"
        status="online"
      />
      <StatCard
        title="Total Messages"
        :value="totalMessageCount"
        icon="📨"
      />
      <StatCard
        title="Feed Status"
        :value="isPaused ? 'Paused' : 'Live'"
        icon="⏯️"
        :status="isPaused ? 'warning' : 'online'"
      />
    </div>

    <!-- Subscription Manager -->
    <SubscriptionManager
      :subscriptions="subscriptions"
      :ws-connected="wsConnected"
      :message-counts="messageCountByTopic"
      @add-subscription="addSubscription"
      @remove-subscription="removeSubscription"
      @clear-all="clearAllSubscriptions"
    />

    <!-- Message Feed -->
    <MessageFeed
      :messages="messages"
      :is-paused="isPaused"
      :message-count="totalMessageCount"
      @toggle-pause="togglePause"
      @clear-messages="clearMessages"
    />

    <!-- Info Note -->
    <div class="card bg-blue-50 border border-blue-200">
      <div class="flex items-start space-x-3">
        <span class="text-2xl">ℹ️</span>
        <div class="flex-1">
          <h3 class="text-sm font-semibold text-blue-900 mb-1">
            About Live Monitoring
          </h3>
          <p class="text-sm text-blue-800 mb-2">
            Add topic subscriptions above to start monitoring messages in real-time.
            You can subscribe to multiple topics simultaneously, including wildcards.
          </p>
          <ul class="text-sm text-blue-800 space-y-1">
            <li><strong>Wildcards:</strong> Use <code class="bg-blue-100 px-1 rounded">#</code> for multi-level wildcard (e.g., sensor/#)</li>
            <li><strong>Single-level:</strong> Use <code class="bg-blue-100 px-1 rounded">+</code> for single-level wildcard (e.g., sensor/+/temperature)</li>
            <li><strong>Pause:</strong> Pause the feed to inspect messages without new ones being added</li>
            <li><strong>Limit:</strong> Message feed is limited to {{ maxMessages }} most recent messages</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>
