<script setup>
import { computed } from "vue";

const props = defineProps({
  categories: {
    type: Array,
    required: true,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
});

// Status badge styling
const getStatusClass = (status) => {
  switch (status) {
    case "online":
      return "bg-green-100 text-green-800";
    case "offline":
      return "bg-gray-100 text-gray-800";
    case "expired":
      return "bg-red-100 text-red-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
};

// Status icon
const getStatusIcon = (status) => {
  switch (status) {
    case "online":
      return "🟢";
    case "offline":
      return "🔴";
    case "expired":
      return "⚫";
    default:
      return "⚪";
  }
};

// Format status text
const formatStatus = (status) => {
  return status.charAt(0).toUpperCase() + status.slice(1);
};

// Check if there are no results
const hasNoResults = computed(() => {
  return !props.loading && props.categories.length === 0;
});
</script>

<template>
  <div>
    <!-- Loading state -->
    <div v-if="loading" class="space-y-3">
      <div
        v-for="i in 3"
        :key="i"
        class="animate-pulse flex items-center space-x-4 p-4 border border-gray-200 rounded-lg"
      >
        <div class="h-4 bg-gray-200 rounded w-1/4"></div>
        <div class="h-4 bg-gray-200 rounded w-1/2"></div>
        <div class="h-4 bg-gray-200 rounded w-1/6"></div>
      </div>
    </div>

    <!-- Empty state -->
    <div
      v-else-if="hasNoResults"
      class="text-center py-12"
    >
      <span class="text-5xl mb-4 block">🔍</span>
      <p class="text-gray-500 text-sm">No client categories found</p>
    </div>

    <!-- Desktop Table -->
    <div v-else class="hidden md:block overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th
              scope="col"
              class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Category
            </th>
            <th
              scope="col"
              class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Description
            </th>
            <th
              scope="col"
              class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Count
            </th>
            <th
              scope="col"
              class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
            >
              Status
            </th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr
            v-for="category in categories"
            :key="category.name"
            class="hover:bg-gray-50 transition-colors"
          >
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="flex items-center">
                <span class="text-lg mr-2">{{ getStatusIcon(category.status) }}</span>
                <span class="text-sm font-medium text-gray-900">
                  {{ category.name }}
                </span>
              </div>
            </td>
            <td class="px-6 py-4">
              <div class="text-sm text-gray-600">
                {{ category.description }}
              </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="text-sm font-bold text-gray-900">
                {{ category.count || 0 }}
              </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <span
                :class="[
                  'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                  getStatusClass(category.status),
                ]"
              >
                {{ formatStatus(category.status) }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Mobile Cards -->
    <div v-else class="md:hidden space-y-3">
      <div
        v-for="category in categories"
        :key="category.name"
        class="border border-gray-200 rounded-lg p-4 hover:border-mqtt-blue transition-colors"
      >
        <!-- Header -->
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center space-x-2">
            <span class="text-lg">{{ getStatusIcon(category.status) }}</span>
            <h3 class="text-sm font-medium text-gray-900">
              {{ category.name }}
            </h3>
          </div>
          <span
            :class="[
              'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
              getStatusClass(category.status),
            ]"
          >
            {{ formatStatus(category.status) }}
          </span>
        </div>

        <!-- Description -->
        <p class="text-sm text-gray-600 mb-3">
          {{ category.description }}
        </p>

        <!-- Count -->
        <div class="flex items-center justify-between pt-3 border-t border-gray-200">
          <span class="text-xs text-gray-500">Client Count</span>
          <span class="text-lg font-bold text-gray-900">
            {{ category.count || 0 }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
