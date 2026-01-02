import { ref, computed } from "vue";

/**
 * Composable for managing time-series chart data
 * @param {Object} options - Configuration options
 * @param {number} options.maxDataPoints - Maximum number of data points to keep (default: 60)
 * @param {number} options.timeWindow - Time window in seconds (default: 60)
 */
export function useChartData(options = {}) {
  const maxDataPoints = options.maxDataPoints || 60;
  const timeWindow = options.timeWindow || 60; // in seconds

  const dataPoints = ref([]);
  const labels = ref([]);

  /**
   * Add a new data point to the chart
   * @param {Object} point - Data point to add
   * @param {number|Object} point.value - Value or object with multiple values
   * @param {Date|string} point.timestamp - Timestamp (optional, defaults to now)
   */
  const addDataPoint = (point) => {
    const timestamp = point.timestamp ? new Date(point.timestamp) : new Date();
    const timeLabel = timestamp.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });

    labels.value.push(timeLabel);
    dataPoints.value.push({
      timestamp,
      value: point.value,
    });

    // Remove old data points that exceed the time window
    const cutoffTime = new Date(Date.now() - timeWindow * 1000);
    let removeCount = 0;

    for (let i = 0; i < dataPoints.value.length; i++) {
      if (dataPoints.value[i].timestamp < cutoffTime) {
        removeCount++;
      } else {
        break;
      }
    }

    if (removeCount > 0) {
      dataPoints.value.splice(0, removeCount);
      labels.value.splice(0, removeCount);
    }

    // Also enforce max data points limit
    if (dataPoints.value.length > maxDataPoints) {
      const excess = dataPoints.value.length - maxDataPoints;
      dataPoints.value.splice(0, excess);
      labels.value.splice(0, excess);
    }
  };

  /**
   * Clear all data points
   */
  const clearData = () => {
    dataPoints.value = [];
    labels.value = [];
  };

  /**
   * Get values array for a specific field
   * @param {string} field - Field name (optional, for multi-value data points)
   */
  const getValues = (field = null) => {
    if (field) {
      return dataPoints.value.map((point) => point.value[field] || 0);
    }
    return dataPoints.value.map((point) => point.value);
  };

  /**
   * Set time window and adjust data accordingly
   * @param {number} seconds - Time window in seconds
   */
  const setTimeWindow = (seconds) => {
    options.timeWindow = seconds;

    // Remove data points outside new time window
    const cutoffTime = new Date(Date.now() - seconds * 1000);
    let removeCount = 0;

    for (let i = 0; i < dataPoints.value.length; i++) {
      if (dataPoints.value[i].timestamp < cutoffTime) {
        removeCount++;
      } else {
        break;
      }
    }

    if (removeCount > 0) {
      dataPoints.value.splice(0, removeCount);
      labels.value.splice(0, removeCount);
    }
  };

  const isEmpty = computed(() => dataPoints.value.length === 0);
  const latestValue = computed(() => {
    if (dataPoints.value.length === 0) return null;
    return dataPoints.value[dataPoints.value.length - 1].value;
  });

  return {
    dataPoints,
    labels,
    addDataPoint,
    clearData,
    getValues,
    setTimeWindow,
    isEmpty,
    latestValue,
  };
}
