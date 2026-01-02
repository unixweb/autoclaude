<script setup>
import { ref, computed, watch } from "vue";

const props = defineProps({
  modelValue: {
    type: String,
    default: "",
  },
  error: {
    type: String,
    default: "",
  },
  placeholder: {
    type: String,
    default: "Enter message payload...",
  },
});

const emit = defineEmits(["update:modelValue"]);

// Editor mode: 'text' or 'json'
const editorMode = ref("text");
const localValue = ref(props.modelValue);
const jsonError = ref("");
const showFormatOptions = ref(false);

// Update local value when prop changes
watch(() => props.modelValue, (newValue) => {
  localValue.value = newValue;

  // Auto-detect JSON
  if (isValidJson(newValue)) {
    editorMode.value = "json";
  }
});

// Check if string is valid JSON
const isValidJson = (str) => {
  if (!str || !str.trim()) return false;
  try {
    JSON.parse(str);
    return true;
  } catch {
    return false;
  }
};

// Format JSON
const formatJson = () => {
  jsonError.value = "";

  if (!localValue.value || !localValue.value.trim()) {
    jsonError.value = "Payload is empty";
    return;
  }

  try {
    const parsed = JSON.parse(localValue.value);
    localValue.value = JSON.stringify(parsed, null, 2);
    editorMode.value = "json";
    emit("update:modelValue", localValue.value);
    showFormatOptions.value = false;
  } catch (error) {
    jsonError.value = "Invalid JSON: " + error.message;
  }
};

// Minify JSON
const minifyJson = () => {
  jsonError.value = "";

  if (!localValue.value || !localValue.value.trim()) {
    jsonError.value = "Payload is empty";
    return;
  }

  try {
    const parsed = JSON.parse(localValue.value);
    localValue.value = JSON.stringify(parsed);
    editorMode.value = "text";
    emit("update:modelValue", localValue.value);
    showFormatOptions.value = false;
  } catch (error) {
    jsonError.value = "Invalid JSON: " + error.message;
  }
};

// Switch to text mode
const switchToText = () => {
  editorMode.value = "text";
  jsonError.value = "";
  showFormatOptions.value = false;
};

// Handle input
const handleInput = (event) => {
  localValue.value = event.target.value;
  emit("update:modelValue", localValue.value);
  jsonError.value = "";
};

// Clear payload
const clearPayload = () => {
  localValue.value = "";
  emit("update:modelValue", "");
  jsonError.value = "";
};

// Insert JSON template
const insertTemplate = (template) => {
  localValue.value = JSON.stringify(template, null, 2);
  editorMode.value = "json";
  emit("update:modelValue", localValue.value);
  showFormatOptions.value = false;
};

// Common JSON templates
const jsonTemplates = [
  { name: "Object", value: { key: "value" } },
  { name: "Array", value: [1, 2, 3] },
  { name: "Sensor Data", value: { temperature: 22.5, humidity: 60, timestamp: new Date().toISOString() } },
];

// Character count
const characterCount = computed(() => {
  return localValue.value.length;
});

// Is JSON mode
const isJsonMode = computed(() => {
  return editorMode.value === "json";
});

// Computed class for textarea
const textareaClass = computed(() => {
  return [
    'w-full px-4 py-3 border rounded-md focus:outline-none focus:ring-2 focus:ring-mqtt-blue focus:border-transparent resize-none',
    props.error || jsonError.value ? 'border-red-300 bg-red-50' : 'border-gray-300',
    isJsonMode.value ? 'font-mono text-sm' : '',
  ].join(' ');
});
</script>

<template>
  <div class="space-y-2">
    <!-- Editor Toolbar -->
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-2">
        <!-- Mode Indicator -->
        <span
          v-if="isJsonMode"
          class="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800"
        >
          JSON
        </span>

        <!-- Character Count -->
        <span class="text-xs text-gray-500">
          {{ characterCount }} characters
        </span>
      </div>

      <div class="flex items-center space-x-2">
        <!-- Format Options Dropdown -->
        <div class="relative">
          <button
            type="button"
            @click="showFormatOptions = !showFormatOptions"
            class="text-xs text-mqtt-blue hover:text-mqtt-dark focus:outline-none"
          >
            ⚙️ Format
          </button>

          <!-- Dropdown Menu -->
          <div
            v-if="showFormatOptions"
            class="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg border border-gray-200 z-10"
          >
            <div class="py-1">
              <button
                type="button"
                @click="formatJson"
                class="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
              >
                Format JSON
              </button>
              <button
                type="button"
                @click="minifyJson"
                class="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
              >
                Minify JSON
              </button>
              <button
                type="button"
                @click="switchToText"
                class="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
              >
                Text Mode
              </button>
              <div class="border-t border-gray-200 my-1"></div>
              <div class="px-4 py-2 text-xs text-gray-500 font-medium">
                Insert Template
              </div>
              <button
                type="button"
                v-for="template in jsonTemplates"
                :key="template.name"
                @click="insertTemplate(template.value)"
                class="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
              >
                {{ template.name }}
              </button>
            </div>
          </div>
        </div>

        <!-- Clear Button -->
        <button
          type="button"
          @click="clearPayload"
          class="text-xs text-gray-500 hover:text-gray-700 focus:outline-none"
          :disabled="!localValue"
        >
          Clear
        </button>
      </div>
    </div>

    <!-- JSON Error -->
    <div
      v-if="jsonError"
      class="p-2 bg-red-50 border border-red-200 rounded text-xs text-red-600"
    >
      {{ jsonError }}
    </div>

    <!-- Textarea -->
    <textarea
      :value="localValue"
      @input="handleInput"
      :placeholder="placeholder"
      :class="textareaClass"
      rows="8"
    ></textarea>
  </div>
</template>

<style scoped>
/* Close dropdown when clicking outside */
</style>
