<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import { getSocket, connectSocket } from "../api/client.js";
import MessagePublisher from "../components/MessagePublisher.vue";
import StatCard from "../components/StatCard.vue";

// State
const wsConnected = ref(false);
const publishCount = ref(0);
const lastPublishedTopic = ref("");

// Initialize WebSocket connection for broker status
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

// Handle successful publish
const handlePublishSuccess = (topic) => {
  publishCount.value++;
  lastPublishedTopic.value = topic;
};

// Lifecycle hooks
onMounted(() => {
  initWebSocket();
});

onUnmounted(() => {
  // Cleanup if needed
});
</script>

<template>
  <div class="space-y-6">
    <!-- Page header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Publish Message</h1>
        <p class="text-sm text-gray-600 mt-1">
          Send messages to MQTT topics
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
          {{ wsConnected ? "Connected" : "Disconnected" }}
        </span>
      </div>
    </div>

    <!-- Statistics Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <StatCard
        title="Messages Published"
        :value="publishCount"
        icon="📤"
        status="online"
      />
      <StatCard
        title="Last Topic"
        :value="lastPublishedTopic || 'None'"
        icon="📍"
      />
    </div>

    <!-- Message Publisher -->
    <MessagePublisher @publish-success="handlePublishSuccess" />

    <!-- Info Note -->
    <div class="card bg-blue-50 border border-blue-200">
      <div class="flex items-start space-x-3">
        <span class="text-2xl">ℹ️</span>
        <div class="flex-1">
          <h3 class="text-sm font-semibold text-blue-900 mb-1">
            Publishing Messages
          </h3>
          <p class="text-sm text-blue-800 mb-2">
            Use this form to publish messages to any MQTT topic. Messages will be sent to the broker
            and distributed to all subscribers.
          </p>
          <ul class="text-sm text-blue-800 space-y-1">
            <li><strong>QoS 0:</strong> At most once delivery (fire and forget)</li>
            <li><strong>QoS 1:</strong> At least once delivery (acknowledged)</li>
            <li><strong>QoS 2:</strong> Exactly once delivery (assured)</li>
            <li><strong>Retain:</strong> The broker stores the message and delivers it to new subscribers</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>
