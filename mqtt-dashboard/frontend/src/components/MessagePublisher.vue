<script setup>
import { ref, computed } from "vue";
import { messagesApi } from "../api/client.js";
import PayloadEditor from "./PayloadEditor.vue";

const emit = defineEmits(["publish-success"]);

// Form state
const topic = ref("");
const payload = ref("");
const qos = ref(0);
const retain = ref(false);

// UI state
const publishing = ref(false);
const publishSuccess = ref(false);
const publishError = ref("");
const successMessage = ref("");

// Validation state
const topicError = ref("");
const payloadError = ref("");

// QoS options
const qosOptions = [
  { value: 0, label: "QoS 0", description: "At most once" },
  { value: 1, label: "QoS 1", description: "At least once" },
  { value: 2, label: "QoS 2", description: "Exactly once" },
];

// Validate topic
const validateTopic = () => {
  topicError.value = "";

  if (!topic.value) {
    topicError.value = "Topic is required";
    return false;
  }

  if (topic.value.includes("#") || topic.value.includes("+")) {
    topicError.value = "Topic cannot contain wildcards (# or +)";
    return false;
  }

  if (topic.value.startsWith("$")) {
    topicError.value = "Cannot publish to $SYS topics";
    return false;
  }

  return true;
};

// Validate payload
const validatePayload = () => {
  payloadError.value = "";

  // Payload can be empty, so no validation needed for now
  // Could add max length validation if needed

  return true;
};

// Validate form
const validateForm = () => {
  const topicValid = validateTopic();
  const payloadValid = validatePayload();

  return topicValid && payloadValid;
};

// Handle payload update from editor
const handlePayloadUpdate = (newPayload) => {
  payload.value = newPayload;
  payloadError.value = "";
};

// Publish message
const publishMessage = async () => {
  // Reset feedback
  publishSuccess.value = false;
  publishError.value = "";
  successMessage.value = "";

  // Validate form
  if (!validateForm()) {
    return;
  }

  try {
    publishing.value = true;

    const message = {
      topic: topic.value,
      payload: payload.value,
      qos: qos.value,
      retain: retain.value,
    };

    const result = await messagesApi.publish(message);

    // Success feedback
    publishSuccess.value = true;
    successMessage.value = `Message published to ${topic.value}`;

    // Emit success event
    emit("publish-success", topic.value);

    // Clear success message after 5 seconds
    setTimeout(() => {
      publishSuccess.value = false;
      successMessage.value = "";
    }, 5000);

  } catch (error) {
    publishError.value = error.message || "Failed to publish message";

    // Clear error message after 10 seconds
    setTimeout(() => {
      publishError.value = "";
    }, 10000);
  } finally {
    publishing.value = false;
  }
};

// Clear form
const clearForm = () => {
  topic.value = "";
  payload.value = "";
  qos.value = 0;
  retain.value = false;
  topicError.value = "";
  payloadError.value = "";
  publishSuccess.value = false;
  publishError.value = "";
  successMessage.value = "";
};

// Form is valid
const isFormValid = computed(() => {
  return topic.value && !topicError.value && !payloadError.value;
});
</script>

<template>
  <div class="card">
    <h2 class="card-header mb-6">Publish Message</h2>

    <!-- Success Message -->
    <div
      v-if="publishSuccess"
      class="mb-6 p-4 bg-green-50 border border-green-200 rounded-md flex items-start space-x-3"
    >
      <span class="text-green-600 text-xl">✓</span>
      <div class="flex-1">
        <p class="text-sm font-medium text-green-800">{{ successMessage }}</p>
      </div>
      <button
        @click="publishSuccess = false"
        class="text-green-600 hover:text-green-800 focus:outline-none"
      >
        <span class="text-xl">&times;</span>
      </button>
    </div>

    <!-- Error Message -->
    <div
      v-if="publishError"
      class="mb-6 p-4 bg-red-50 border border-red-200 rounded-md flex items-start space-x-3"
    >
      <span class="text-red-600 text-xl">⚠</span>
      <div class="flex-1">
        <p class="text-sm font-medium text-red-800">{{ publishError }}</p>
      </div>
      <button
        @click="publishError = ''"
        class="text-red-600 hover:text-red-800 focus:outline-none"
      >
        <span class="text-xl">&times;</span>
      </button>
    </div>

    <!-- Form -->
    <form @submit.prevent="publishMessage" class="space-y-6">
      <!-- Topic Input -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Topic <span class="text-red-500">*</span>
        </label>
        <input
          v-model="topic"
          type="text"
          placeholder="e.g., home/livingroom/temperature"
          :class="[
            'w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-mqtt-blue focus:border-transparent',
            topicError ? 'border-red-300 bg-red-50' : 'border-gray-300',
          ]"
          @blur="validateTopic"
          @input="topicError = ''"
        />
        <p v-if="topicError" class="mt-1 text-sm text-red-600">
          {{ topicError }}
        </p>
        <p v-else class="mt-1 text-xs text-gray-500">
          Enter the MQTT topic to publish to (no wildcards allowed)
        </p>
      </div>

      <!-- Payload Editor -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Payload
        </label>
        <PayloadEditor
          :modelValue="payload"
          @update:modelValue="handlePayloadUpdate"
          :error="payloadError"
        />
        <p v-if="payloadError" class="mt-1 text-sm text-red-600">
          {{ payloadError }}
        </p>
        <p v-else class="mt-1 text-xs text-gray-500">
          Enter the message payload (text or JSON)
        </p>
      </div>

      <!-- QoS Selector -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          Quality of Service (QoS)
        </label>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div
            v-for="option in qosOptions"
            :key="option.value"
            :class="[
              'border rounded-md p-3 cursor-pointer transition-colors',
              qos === option.value
                ? 'border-mqtt-blue bg-blue-50 ring-2 ring-mqtt-blue'
                : 'border-gray-300 hover:border-mqtt-blue',
            ]"
            @click="qos = option.value"
          >
            <div class="flex items-center space-x-2">
              <input
                type="radio"
                :id="`qos-${option.value}`"
                :value="option.value"
                v-model="qos"
                class="text-mqtt-blue focus:ring-mqtt-blue"
              />
              <label
                :for="`qos-${option.value}`"
                class="flex-1 cursor-pointer"
              >
                <div class="font-medium text-gray-900">{{ option.label }}</div>
                <div class="text-xs text-gray-600">{{ option.description }}</div>
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- Retain Flag -->
      <div>
        <label class="flex items-start space-x-3 cursor-pointer group">
          <div class="flex items-center h-5">
            <input
              type="checkbox"
              v-model="retain"
              class="w-4 h-4 text-mqtt-blue border-gray-300 rounded focus:ring-mqtt-blue"
            />
          </div>
          <div class="flex-1">
            <div class="text-sm font-medium text-gray-700 group-hover:text-gray-900">
              Retain Message
            </div>
            <div class="text-xs text-gray-600">
              The broker will store this message and deliver it to new subscribers
            </div>
          </div>
        </label>
      </div>

      <!-- Action Buttons -->
      <div class="flex items-center justify-end space-x-3 pt-4 border-t border-gray-200">
        <button
          type="button"
          @click="clearForm"
          class="btn-secondary px-6 py-2"
          :disabled="publishing"
        >
          Clear
        </button>
        <button
          type="submit"
          class="btn-primary px-6 py-2"
          :disabled="publishing || !isFormValid"
        >
          <span v-if="publishing" class="flex items-center space-x-2">
            <svg class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>Publishing...</span>
          </span>
          <span v-else>Publish Message</span>
        </button>
      </div>
    </form>
  </div>
</template>
