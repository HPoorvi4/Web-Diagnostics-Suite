// src/components/AnalyzeForm.jsx
import React, { useState, useRef, useEffect, useCallback } from "react";
import { RefreshCw, Link, AlertCircle, Check, CheckCircle } from "lucide-react";
import AnalysisProgress from "./AnalysisProgress";
import "./Styles/AnalyzeForm.css";

const AnalyzeForm = ({ onAnalysisComplete }) => {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [includeScreenshots, setIncludeScreenshots] = useState(true);

  // Progress tracking
  const [progress, setProgress] = useState({
    stage: "",
    progress: 0,
    message: "",
    error: false,
  });

  const wsRef = useRef(null);
  const sessionIdRef = useRef(null);
  const abortControllerRef = useRef(null);

  // Cleanup WebSocket and abort controllers on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const connectWebSocket = useCallback(
    (sessionId) => {
      return new Promise((resolve, reject) => {
        // Close existing WebSocket if any
        if (wsRef.current) {
          wsRef.current.close();
        }

        const wsUrl = `ws://localhost:8000/ws/${sessionId}`;
        console.log("Connecting to WebSocket:", wsUrl);

        let ws;
        try {
          ws = new WebSocket(wsUrl);
        } catch (error) {
          console.error("Failed to create WebSocket:", error);
          reject(error);
          return;
        }

        // Set timeout for connection
        const connectionTimeout = setTimeout(() => {
          console.warn("WebSocket connection timeout");
          ws.close();
          reject(new Error("WebSocket connection timeout"));
        }, 10000); // 10 second timeout

        ws.onopen = () => {
          console.log("WebSocket connected for session:", sessionId);
          clearTimeout(connectionTimeout);
          wsRef.current = ws;
          resolve(ws);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log("WebSocket message:", data);

            setProgress({
              stage: data.stage || "",
              progress: data.progress || 0,
              message: data.message || "",
              error: data.error || false,
            });

            // Check if analysis is complete
            if (data.results) {
              setSuccess(true);
              setLoading(false);
              if (onAnalysisComplete) {
                onAnalysisComplete(data.results);
              }
              ws.close();
            } else if (data.error) {
              setError(data.message || "Analysis failed");
              setLoading(false);
              ws.close();
            }
          } catch (e) {
            console.error("Error parsing WebSocket message:", e);
          }
        };

        ws.onerror = (error) => {
          console.error("WebSocket error:", error);
          clearTimeout(connectionTimeout);
          setError("Connection error during analysis");
          setLoading(false);
          reject(error);
        };

        ws.onclose = (event) => {
          console.log("WebSocket closed:", event.code, event.reason);
          clearTimeout(connectionTimeout);
          wsRef.current = null;
        };
      });
    },
    [onAnalysisComplete]
  );

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Prevent multiple simultaneous submissions
    if (loading) return;

    setLoading(true);
    setError(null);
    setSuccess(false);
    setProgress({
      stage: "Starting...",
      progress: 0,
      message: "",
      error: false,
    });

    // Create abort controller for this request
    abortControllerRef.current = new AbortController();

    try {
      // Validate URL format
      let urlToTest;
      try {
        urlToTest = url.startsWith("http") ? url : `https://${url}`;
        new URL(urlToTest); // This will throw if invalid
      } catch (urlError) {
        throw new Error(
          "Please enter a valid URL (e.g., example.com or https://example.com)"
        );
      }

      console.log("Starting analysis for:", urlToTest);

      // Start analysis
      const response = await fetch("http://localhost:8000/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url: urlToTest,
          include_screenshots: includeScreenshots,
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        let errorData;
        try {
          errorData = await response.json();
        } catch {
          errorData = {
            detail: `HTTP ${response.status}: ${response.statusText}`,
          };
        }

        if (response.status === 503) {
          throw new Error(
            "Analysis service is currently unavailable. Please ensure the backend is properly configured and running."
          );
        }

        throw new Error(
          errorData.detail || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      const data = await response.json();

      if (response.status === 202) {
        // Analysis started - connect to WebSocket
        sessionIdRef.current = data.session_id;
        setProgress({
          stage: "Connecting...",
          progress: 5,
          message: "Establishing real-time connection",
          error: false,
        });

        try {
          await connectWebSocket(data.session_id);
        } catch (wsError) {
          console.error("WebSocket connection failed:", wsError);
          console.log("Falling back to polling method");
          // Fallback to polling
          pollForResults(data.session_id, urlToTest);
        }
      } else {
        // Immediate result (cached)
        console.log("Received immediate result (cached)");
        setSuccess(true);
        setLoading(false);
        if (onAnalysisComplete) {
          onAnalysisComplete(data);
        }
      }
    } catch (err) {
      console.error("Analysis error:", err);

      if (err.name === "AbortError") {
        console.log("Analysis was cancelled");
        return;
      }

      setError(err.message || "Failed to start analysis");
      setLoading(false);
      setProgress({
        stage: "Error",
        progress: 0,
        message: err.message,
        error: true,
      });
    }
  };

  // Fallback polling method if WebSocket fails
  const pollForResults = useCallback(
    async (sessionId, originalUrl) => {
      let attempts = 0;
      const maxAttempts = 60; // 60 attempts = 5 minutes max

      const poll = async () => {
        attempts++;

        if (abortControllerRef.current?.signal.aborted) {
          console.log("Polling cancelled");
          return;
        }

        try {
          // Try to get results by checking recent analyses
          const response = await fetch(
            "http://localhost:8000/history?limit=1",
            {
              signal: abortControllerRef.current?.signal,
            }
          );

          if (response.ok) {
            const data = await response.json();
            if (data.recent_analyses && data.recent_analyses.length > 0) {
              const recent = data.recent_analyses[0];

              // Check if this is our analysis (by URL and recency)
              const recentTime = new Date(recent.analyzed_at);
              const timeDiff = Date.now() - recentTime.getTime();

              if (recent.url === originalUrl && timeDiff < 300000) {
                // Within 5 minutes
                // Found our analysis
                console.log("Found analysis result via polling:", recent.id);
                const analysisResponse = await fetch(
                  `http://localhost:8000/analysis/${recent.id}`,
                  {
                    signal: abortControllerRef.current?.signal,
                  }
                );

                if (analysisResponse.ok) {
                  const analysisData = await analysisResponse.json();
                  setSuccess(true);
                  setLoading(false);
                  if (onAnalysisComplete) {
                    onAnalysisComplete(analysisData);
                  }
                  return;
                }
              }
            }
          }
        } catch (e) {
          if (e.name === "AbortError") {
            console.log("Polling aborted");
            return;
          }
          console.error("Polling error:", e);
        }

        if (
          attempts < maxAttempts &&
          !abortControllerRef.current?.signal.aborted
        ) {
          setProgress({
            stage: "Processing...",
            progress: Math.min(10 + attempts * 1.5, 95),
            message: `Analysis in progress (${attempts * 5}s)`,
            error: false,
          });
          setTimeout(poll, 5000); // Poll every 5 seconds
        } else if (!abortControllerRef.current?.signal.aborted) {
          setError("Analysis timeout - please try again");
          setLoading(false);
        }
      };

      setTimeout(poll, 2000); // Start polling after 2 seconds
    },
    [onAnalysisComplete]
  );

  const handleReset = useCallback(() => {
    setUrl("");
    setError(null);
    setSuccess(false);
    setLoading(false);
    setProgress({ stage: "", progress: 0, message: "", error: false });

    if (wsRef.current) {
      wsRef.current.close();
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  }, []);

  const handleCancel = useCallback(() => {
    setLoading(false);
    setError(null);
    setProgress({ stage: "", progress: 0, message: "", error: false });

    if (wsRef.current) {
      wsRef.current.close();
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  }, []);

  return (
    <>
      <form className="analyze-form" onSubmit={handleSubmit}>
        {/* Header */}
        <div className="form-header">
          <h2 className="form-title">Website Analyzer</h2>
          <button
            type="button"
            className="reset-button"
            onClick={handleReset}
            disabled={loading}
          >
            Reset
          </button>
        </div>

        {/* URL Input */}
        <div className="url-input-section">
          <label htmlFor="url" className="input-label">
            Enter Website URL
          </label>
          <div className="url-input-container">
            <input
              id="url"
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="example.com or https://example.com"
              className="url-input"
              disabled={loading}
              required
            />
            <Link className="url-input-icon" />
          </div>
        </div>

        {/* Options */}
        <div className="options-section">
          <p className="options-title">Analysis Options</p>
          <label className="checkbox-container">
            <input
              type="checkbox"
              className="checkbox-input"
              checked={includeScreenshots}
              onChange={(e) => setIncludeScreenshots(e.target.checked)}
              disabled={loading}
            />
            <span className="checkbox-label">
              Include Screenshots
              <span className="checkbox-sublabel">
                Capture mobile and desktop screenshots (adds ~10s)
              </span>
            </span>
          </label>
        </div>

        {/* Submit */}
        <button
          type="submit"
          className="submit-button"
          disabled={loading || !url.trim()}
        >
          {loading ? (
            <span className="button-loading">
              <span className="loading-spinner" />
              Analyzing...
            </span>
          ) : (
            "Start Analysis"
          )}
        </button>

        {/* Success Message */}
        {success && !error && !loading && (
          <div className="success-section">
            <div className="success-content">
              <CheckCircle className="success-icon" />
              <div className="success-details">
                <p className="success-title">Analysis Complete!</p>
                <p className="success-message">Successfully analyzed {url}</p>
                <p className="success-score">Results are now available below</p>
              </div>
            </div>
          </div>
        )}

        {/* Analysis Info */}
        {!error && !loading && !success && url && (
          <div className="analysis-info">
            <p className="analysis-info-title">What we analyze:</p>
            <div className="analysis-features">
              <div className="feature-item">
                <div className="feature-icon">
                  <Check />
                </div>
                <div className="feature-content">
                  <p className="feature-title">Performance</p>
                  <p className="feature-description">
                    Load times, Core Web Vitals, and optimization opportunities
                  </p>
                </div>
              </div>

              <div className="feature-item">
                <div className="feature-icon">
                  <Check />
                </div>
                <div className="feature-content">
                  <p className="feature-title">SEO</p>
                  <p className="feature-description">
                    Meta tags, content structure, and search optimization
                  </p>
                </div>
              </div>

              <div className="feature-item">
                <div className="feature-icon">
                  <Check />
                </div>
                <div className="feature-content">
                  <p className="feature-title">Security</p>
                  <p className="feature-description">
                    SSL certificates, security headers, and vulnerabilities
                  </p>
                </div>
              </div>

              <div className="feature-item">
                <div className="feature-icon">
                  <Check />
                </div>
                <div className="feature-content">
                  <p className="feature-title">Mobile</p>
                  <p className="feature-description">
                    Responsive design, mobile usability, and compatibility
                  </p>
                </div>
              </div>
            </div>
            <div className="analysis-footer">
              <p className="analysis-footer-text">
                Comprehensive report with actionable recommendations
              </p>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="error-section">
            <div className="error-content">
              <AlertCircle className="error-icon" />
              <div className="error-details">
                <p className="error-title">Analysis Failed</p>
                <p className="error-message">{error}</p>
                <div className="error-actions">
                  <button onClick={handleSubmit} className="error-retry">
                    Try Again
                  </button>
                  <button onClick={handleReset} className="error-reset">
                    Reset
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </form>

      {/* Progress Modal */}
      <AnalysisProgress
        isVisible={loading}
        stage={progress.stage}
        progress={progress.progress}
        message={progress.message}
        error={progress.error}
        onCancel={handleCancel}
      />
    </>
  );
};

export default AnalyzeForm;
