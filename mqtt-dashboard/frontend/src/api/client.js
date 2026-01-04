import axios from "axios";
import { io } from "socket.io-client";

/**
 * Base API URL - proxied in development, direct in production
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || "";

/**
 * Axios instance configured for the MQTT Dashboard API
 */
export const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.error || error.message || "An error occurred";
    return Promise.reject(new Error(message));
  }
);

/**
 * Socket.IO client singleton
 */
let socketInstance = null;

/**
 * Get or create the Socket.IO client instance
 * @returns {import('socket.io-client').Socket}
 */
export function getSocket() {
  if (!socketInstance) {
    const socketUrl = import.meta.env.VITE_WS_URL || window.location.origin;
    socketInstance = io(socketUrl, {
      autoConnect: false,
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      transports: ["polling", "websocket"],
    });
  }
  return socketInstance;
}

/**
 * Connect to WebSocket server
 * @returns {Promise<void>}
 */
export function connectSocket() {
  return new Promise((resolve, reject) => {
    const socket = getSocket();

    if (socket.connected) {
      resolve();
      return;
    }

    const onConnect = () => {
      socket.off("connect_error", onError);
      resolve();
    };

    const onError = (error) => {
      socket.off("connect", onConnect);
      reject(error);
    };

    socket.once("connect", onConnect);
    socket.once("connect_error", onError);

    socket.connect();
  });
}

/**
 * Disconnect from WebSocket server
 */
export function disconnectSocket() {
  if (socketInstance) {
    socketInstance.disconnect();
  }
}

/**
 * API methods for broker endpoints
 */
export const brokerApi = {
  /**
   * Get broker health/connection status
   */
  async getStatus() {
    const response = await apiClient.get("/broker/status");
    return response.data;
  },

  /**
   * Get broker statistics
   */
  async getStats() {
    const response = await apiClient.get("/broker/stats");
    return response.data;
  },

  /**
   * Get Mosquitto version info
   */
  async getVersion() {
    const response = await apiClient.get("/broker/version");
    return response.data;
  },
};

/**
 * API methods for client endpoints
 */
export const clientsApi = {
  /**
   * Get list of connected clients
   */
  async getClients() {
    const response = await apiClient.get("/clients");
    return response.data;
  },

  /**
   * Get client count statistics
   */
  async getCount() {
    const response = await apiClient.get("/clients/count");
    return response.data;
  },
};

/**
 * API methods for topic endpoints
 */
export const topicsApi = {
  /**
   * Get list of active topics
   * @param {Object} params - Query parameters
   * @param {string} [params.filter] - Filter pattern
   */
  async getTopics(params = {}) {
    const response = await apiClient.get("/topics", { params });
    return response.data;
  },

  /**
   * Get recent messages for a topic
   * @param {string} topic - Topic name (URL encoded)
   */
  async getMessages(topic) {
    const encodedTopic = encodeURIComponent(topic);
    const response = await apiClient.get(`/topics/${encodedTopic}/messages`);
    return response.data;
  },
};

/**
 * API methods for message publishing
 */
export const messagesApi = {
  /**
   * Publish a message to an MQTT topic
   * @param {Object} message - Message to publish
   * @param {string} message.topic - Target topic
   * @param {string} message.payload - Message payload
   * @param {number} [message.qos=0] - QoS level (0, 1, or 2)
   * @param {boolean} [message.retain=false] - Retain flag
   */
  async publish(message) {
    const response = await apiClient.post("/messages/publish", message);
    return response.data;
  },
};

export default {
  apiClient,
  getSocket,
  connectSocket,
  disconnectSocket,
  brokerApi,
  clientsApi,
  topicsApi,
  messagesApi,
};
