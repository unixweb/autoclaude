import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { resolve } from "path";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],

  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
    },
  },

  server: {
    port: 3000,
    host: true,
    proxy: {
      // Proxy API requests to Flask backend during development
      "/api": {
        target: "http://localhost:5000",
        changeOrigin: true,
      },
      // Proxy WebSocket connections
      "/socket.io": {
        target: "http://localhost:5000",
        changeOrigin: true,
        ws: true,
      },
    },
  },

  build: {
    outDir: "dist",
    assetsDir: "assets",
    // Generate source maps for debugging
    sourcemap: false,
    // Optimize chunk splitting
    rollupOptions: {
      output: {
        manualChunks: {
          vue: ["vue", "vue-router"],
          socketio: ["socket.io-client"],
        },
      },
    },
  },
});
