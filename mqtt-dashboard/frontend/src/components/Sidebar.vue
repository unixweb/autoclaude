<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";

const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["close"]);

const route = useRoute();

// Navigation items
const navItems = [
  {
    name: "Overview",
    path: "/",
    icon: "📊",
    description: "Broker statistics and health",
  },
  {
    name: "Clients",
    path: "/clients",
    icon: "👥",
    description: "Connected MQTT clients",
  },
  {
    name: "Topics",
    path: "/topics",
    icon: "🏷️",
    description: "Active topics and messages",
  },
  {
    name: "Publish",
    path: "/publish",
    icon: "📤",
    description: "Send messages to topics",
  },
  {
    name: "Monitor",
    path: "/monitor",
    icon: "📡",
    description: "Real-time message feed",
  },
  {
    name: "Settings",
    path: "/settings",
    icon: "⚙️",
    description: "Broker configuration",
  },
];

// Check if a nav item is active
const isActive = (path) => {
  if (path === "/") {
    return route.path === "/";
  }
  return route.path.startsWith(path);
};

// Handle navigation link click
const handleNavClick = () => {
  emit("close");
};
</script>

<template>
  <!-- Mobile overlay -->
  <div
    v-if="open"
    class="fixed inset-0 bg-gray-900 bg-opacity-50 z-20 lg:hidden"
    @click="emit('close')"
  ></div>

  <!-- Sidebar -->
  <aside
    :class="[
      'fixed lg:static inset-y-0 left-0 z-30 w-64 bg-white border-r border-gray-200',
      'transform transition-transform duration-300 ease-in-out lg:translate-x-0',
      open ? 'translate-x-0' : '-translate-x-full',
    ]"
  >
    <!-- Logo/Brand -->
    <div class="h-16 flex items-center px-6 border-b border-gray-200">
      <div class="flex items-center space-x-2">
        <span class="text-2xl">🦟</span>
        <div>
          <h1 class="text-lg font-bold text-gray-900">MQTT Dashboard</h1>
          <p class="text-xs text-gray-500">Mosquitto Admin</p>
        </div>
      </div>
    </div>

    <!-- Navigation -->
    <nav class="p-4 space-y-1 overflow-y-auto h-[calc(100vh-4rem)] scrollbar-thin">
      <RouterLink
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        @click="handleNavClick"
        :class="[
          'flex items-center px-3 py-2.5 rounded-lg transition-colors duration-150',
          'group hover:bg-gray-100',
          isActive(item.path)
            ? 'bg-primary-50 text-primary-700 font-medium'
            : 'text-gray-700 hover:text-gray-900',
        ]"
      >
        <span class="text-xl mr-3">{{ item.icon }}</span>
        <div class="flex-1 min-w-0">
          <div class="font-medium">{{ item.name }}</div>
          <div
            :class="[
              'text-xs truncate',
              isActive(item.path) ? 'text-primary-600' : 'text-gray-500',
            ]"
          >
            {{ item.description }}
          </div>
        </div>
      </RouterLink>
    </nav>

    <!-- Footer info -->
    <div class="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 bg-white">
      <div class="text-xs text-gray-500 text-center">
        <div class="mb-1">Version 1.0.0</div>
        <div>© 2026 MQTT Dashboard</div>
      </div>
    </div>
  </aside>
</template>
