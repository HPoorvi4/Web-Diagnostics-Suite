// src/services/api.js
const API_BASE_URL = "http://localhost:8000";
const WS_BASE_URL = "ws://localhost:8000";

class APIService {
  constructor() {
    this.baseURL = API_BASE_URL;
    this.wsBaseURL = WS_BASE_URL;
  }

  // Regular HTTP API calls
  async analyzeWebsite(url, includeScreenshots = true) {
    try {
      const response = await fetch(`${this.baseURL}/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url: url,
          include_screenshots: includeScreenshots,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Analysis failed");
      }

      const data = await response.json();

      // If it's a cached result (status 200), return immediately
      if (response.status === 200) {
        return { type: "cached", data };
      }

      // If it's a new analysis (status 202), return session info
      return { type: "session", data };
    } catch (error) {
      console.error("Analysis request failed:", error);
      throw error;
    }
  }

  // WebSocket connection for real-time progress
  connectWebSocket(sessionId, callbacks = {}) {
    const wsUrl = `${this.wsBaseURL}/ws/${sessionId}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("WebSocket connected for session:", sessionId);
      if (callbacks.onOpen) callbacks.onOpen();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("WebSocket message:", data);

        if (callbacks.onProgress) {
          callbacks.onProgress(data);
        }

        // Handle completion
        if (data.progress === 100 && data.results) {
          if (callbacks.onComplete) {
            callbacks.onComplete(data.results, data.analysis_id);
          }
        }

        // Handle errors
        if (data.error) {
          if (callbacks.onError) {
            callbacks.onError(data.message || "Analysis failed");
          }
        }
      } catch (error) {
        console.error("Error parsing WebSocket message:", error);
        if (callbacks.onError) {
          callbacks.onError("Invalid response format");
        }
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      if (callbacks.onError) {
        callbacks.onError("Connection error");
      }
    };

    ws.onclose = (event) => {
      console.log("WebSocket closed:", event.code, event.reason);
      if (callbacks.onClose) {
        callbacks.onClose(event.code, event.reason);
      }
    };

    // Return WebSocket instance for manual control if needed
    return ws;
  }

  // Get analysis by ID
  async getAnalysis(analysisId) {
    try {
      const response = await fetch(`${this.baseURL}/analysis/${analysisId}`);
      if (!response.ok) {
        throw new Error("Failed to fetch analysis");
      }
      return await response.json();
    } catch (error) {
      console.error("Get analysis failed:", error);
      throw error;
    }
  }

  // Get analysis history
  async getHistory(limit = 10) {
    try {
      const response = await fetch(`${this.baseURL}/history?limit=${limit}`);
      if (!response.ok) {
        throw new Error("Failed to fetch history");
      }
      return await response.json();
    } catch (error) {
      console.error("Get history failed:", error);
      throw error;
    }
  }

  // Get statistics
  async getStats() {
    try {
      const response = await fetch(`${this.baseURL}/stats`);
      if (!response.ok) {
        throw new Error("Failed to fetch stats");
      }
      return await response.json();
    } catch (error) {
      console.error("Get stats failed:", error);
      throw error;
    }
  }

  // Health check
  async healthCheck() {
    try {
      const response = await fetch(`${this.baseURL}/health`);
      return await response.json();
    } catch (error) {
      console.error("Health check failed:", error);
      throw error;
    }
  }
}

export default new APIService();
