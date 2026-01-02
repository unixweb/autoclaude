<script setup>
import { ref, computed } from "vue";

const props = defineProps({
  subscriptions: {
    type: Array,
    required: true,
    default: () => [],
  },
  wsConnected: {
    type: Boolean,
    default: false,
  },
  messageCounts: {
    type: Object,
    default: () => ({}),
  },
});

const emit = defineEmits(["add-subscription", "remove-subscription", "clear-all"]);

// Form state
const newTopic = ref("");
const topicError = ref("");

// Preset topics for quick subscription
const presetTopics = [
  { topic: "#", label: "All Topics", description: "Subscribe to all messages" },
  { topic: "$SYS/#", label: "System Topics", description: "Broker system messages" },
  { topic: "sensor/#", label: "All Sensors", description: "All sensor data" },
  { topic: "home/+/temperature", label: "Room Temperatures", description: "Temperature readings" },
];

// Validate topic
const validateTopic = () => {
  topicError.value = "";

  if (!newTopic.value) {
    topicError.value = "Topic is required";
    return false;
  }

  if (props.subscriptions.includes(newTopic.value)) {
    topicError.value = "Already subscribed to this topic";
    return false;
  }

  return true;
};

// Add subscription
const addSubscription = () => {
  if (!validateTopic()) return;

  emit("add-subscription", newTopic.value);
  newTopic.value = "";
  topicError.value = "";
};

// Add preset subscription
const addPresetSubscription = (topic) => {
  if (props.subscriptions.includes(topic)) {
    topicError.value = "Already subscribed to this topic";
    setTimeout(() => {
      topicError.value = "";
    }, 3000);
    return;
  }

  emit("add-subscription", topic);
};

// Remove subscription
const removeSubscription = (topic) => {
  emit("remove-subscription", topic);
};

// Clear all subscriptions
const clearAll = () => {
  emit("clear-all");
};

// Check if topic is a wildcard
const isWildcard = (topic) => {
  return topic.includes("#") || topic.includes("+");
};

// Subscription count
const subscriptionCount = computed(() => props.subscriptions.length);
</script>

<template>
  <div class="card">
    <h2 class="card-header mb-4">Subscription Manager</h2>

    <!-- Add Subscription Form -->
    <div class="mb-4">
      <label class="block text-sm font-medium text-gray-700 mb-2">
        Add Topic Subscription
      </label>
      <div class="flex gap-2">
        <input
          v-model="newTopic"
          type="text"
          placeholder="e.g., sensor/# or home/+/temperature"
          :class="[
            'flex-1 px-3 py-2 text-sm border rounded-md focus:outline-none focus:ring-2 focus:ring-mqtt-blue focus:border-transparent',
            topicError ? 'border-red-300 bg-red-50' : 'border-gray-300',
          ]"
          @keyup.enter="addSubscription"
          @input="topicError = ''"
          :disabled="!wsConnected"
        />
        <button
          @click="addSubscription"
          class="btn-primary px-4 py-2 text-sm"
          :disabled="!wsConnected || !newTopic"
        >
          ➕ Subscribe
        </button>
      </div>
      <p v-if="topicError" class="mt-1 text-sm text-red-600">
        {{ topicError }}
      </p>
      <p v-else-if="!wsConnected" class="mt-1 text-xs text-orange-600">
        ⚠️ WebSocket not connected - please wait
      </p>
      <p v-else class="mt-1 text-xs text-gray-500">
        Use # for multi-level wildcard, + for single-level wildcard
      </p>
    </div>

    <!-- Preset Topics -->
    <div class="mb-4">
      <label class="block text-sm font-medium text-gray-700 mb-2">
        Quick Subscribe
      </label>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
        <button
          v-for="preset in presetTopics"
          :key="preset.topic"
          @click="addPresetSubscription(preset.topic)"
          :disabled="!wsConnected || subscriptions.includes(preset.topic)"
          :class="[
            'text-left px-3 py-2 text-sm border rounded-md transition-colors',
            subscriptions.includes(preset.topic)
              ? 'border-gray-200 bg-gray-50 text-gray-400 cursor-not-allowed'
              : 'border-gray-300 hover:border-mqtt-blue hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-mqtt-blue',
          ]"
        >
          <div class="font-medium text-gray-900">{{ preset.label }}</div>
          <div class="text-xs text-gray-600 font-mono">{{ preset.topic }}</div>
          <div class="text-xs text-gray-500">{{ preset.description }}</div>
        </button>
      </div>
    </div>

    <!-- Active Subscriptions -->
    <div>
      <div class="flex items-center justify-between mb-2">
        <label class="block text-sm font-medium text-gray-700">
          Active Subscriptions ({{ subscriptionCount }})
        </label>
        <button
          v-if="subscriptionCount > 0"
          @click="clearAll"
          class="text-xs text-red-600 hover:text-red-800 focus:outline-none"
        >
          🗑️ Clear All
        </button>
      </div>

      <!-- Subscriptions List -->
      <div
        v-if="subscriptionCount === 0"
        class="text-center py-8 bg-gray-50 rounded-md border border-gray-200"
      >
        <span class="text-4xl mb-2 block">📭</span>
        <p class="text-sm text-gray-500">No active subscriptions</p>
        <p class="text-xs text-gray-400 mt-1">Add a topic above to start monitoring</p>
      </div>

      <div v-else class="space-y-2">
        <div
          v-for="topic in subscriptions"
          :key="topic"
          class="flex items-center justify-between px-3 py-2 bg-gray-50 border border-gray-200 rounded-md hover:border-mqtt-blue transition-colors group"
        >
          <div class="flex items-center space-x-2 flex-1 min-w-0">
            <span
              v-if="isWildcard(topic)"
              class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800 flex-shrink-0"
            >
              🔀 Wildcard
            </span>
            <span
              v-else
              class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 flex-shrink-0"
            >
              📍 Topic
            </span>
            <span class="text-sm font-mono text-gray-900 truncate flex-1" :title="topic">
              {{ topic }}
            </span>
            <span
              v-if="messageCounts[topic] !== undefined"
              class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 flex-shrink-0"
            >
              {{ messageCounts[topic] }} msg
            </span>
          </div>
          <button
            @click="removeSubscription(topic)"
            class="ml-2 text-gray-400 hover:text-red-600 focus:outline-none flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
            title="Unsubscribe"
          >
            <span class="text-lg">×</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
