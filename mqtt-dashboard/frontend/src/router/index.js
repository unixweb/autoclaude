import { createRouter, createWebHistory } from "vue-router";
import DashboardLayout from "../layouts/DashboardLayout.vue";
import Overview from "../views/Overview.vue";
import Clients from "../views/Clients.vue";
import Topics from "../views/Topics.vue";

// Placeholder component for routes that will be implemented later
const PlaceholderView = {
  template: `
    <div class="flex items-center justify-center min-h-[60vh]">
      <div class="text-center">
        <h1 class="text-2xl font-semibold text-gray-900 mb-2">{{ $route.meta.title || 'Coming Soon' }}</h1>
        <p class="text-gray-600">This view will be implemented in a future phase.</p>
      </div>
    </div>
  `,
};

const routes = [
  {
    path: "/",
    component: DashboardLayout,
    children: [
      {
        path: "",
        name: "overview",
        component: Overview,
        meta: {
          title: "Broker Overview",
        },
      },
      {
        path: "clients",
        name: "clients",
        component: Clients,
        meta: {
          title: "Connected Clients",
        },
      },
      {
        path: "topics",
        name: "topics",
        component: Topics,
        meta: {
          title: "Topics Explorer",
        },
      },
      {
        path: "publish",
        name: "publish",
        component: PlaceholderView,
        meta: {
          title: "Publish Message",
        },
      },
      {
        path: "monitor",
        name: "monitor",
        component: PlaceholderView,
        meta: {
          title: "Live Monitor",
        },
      },
      {
        path: "settings",
        name: "settings",
        component: PlaceholderView,
        meta: {
          title: "Settings",
        },
      },
    ],
  },
  {
    path: "/:pathMatch(.*)*",
    name: "not-found",
    component: {
      template: `
        <div class="flex items-center justify-center min-h-screen bg-gray-50">
          <div class="text-center">
            <h1 class="text-4xl font-bold text-gray-900 mb-2">404</h1>
            <p class="text-gray-600 mb-4">Page not found</p>
            <router-link to="/" class="btn-primary">Go to Dashboard</router-link>
          </div>
        </div>
      `,
    },
  },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition;
    }
    return { top: 0 };
  },
});

// Update document title on navigation
router.afterEach((to) => {
  const baseTitle = "MQTT Dashboard";
  document.title = to.meta.title ? `${to.meta.title} | ${baseTitle}` : baseTitle;
});

export default router;
