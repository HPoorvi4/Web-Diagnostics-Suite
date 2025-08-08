// src/components/AnalyzeForm.jsx
import React, { useState, useRef } from "react";
import APIService from "../services/api";
import AnalysisProgress from "./AnalysisProgress";

const AnalyzeForm = ({ onAnalysisComplete }) => {
  const [url, setUrl] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progress, setProgress] = useState({
    stage: "",
    progress: 0,
    message: "",
    error: null,
  });
  const [includeScreenshots, setIncludeScreenshots] = useState(true);

  const wsRef = useRef(null);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!url.trim()) {
      alert("Please enter a URL");
      return;
    }

    // Add https:// if no protocol specified
    let formattedUrl = url.trim();
    if (!/^https?:\/\//i.test(formattedUrl)) {
      formattedUrl = `https://${formattedUrl}`;
    }

    setIsAnalyzing(true);
    setProgress({
      stage: "Initializing...",
      progress: 0,
      message: "Starting analysis request",
      error: null,
    });

    try {
      // Start the analysis
      const response = await APIService.analyzeWebsite(
        formattedUrl,
        includeScreenshots
      );

      if (response.type === "cached") {
        // Cached result - show immediately
        setIsAnalyzing(false);
        if (onAnalysisComplete) {
          onAnalysisComplete(response.data);
        }
        return;
      }

      if (response.type === "session") {
        // New analysis - connect to WebSocket for progress
        const { session_id } = response.data;

        wsRef.current = APIService.connectWebSocket(session_id, {
          onOpen: () => {
            console.log("Connected to analysis session");
          },

          onProgress: (data) => {
            setProgress({
              stage: data.stage || "Processing...",
              progress: data.progress || 0,
              message: data.message || "",
              error: data.error ? data.message : null,
            });
          },

          onComplete: (results, analysisId) => {
            console.log("Analysis completed:", results);
            setIsAnalyzing(false);
            setProgress({
              stage: "Complete!",
              progress: 100,
              message: "Analysis finished successfully",
              error: null,
            });

            // Call completion handler with results
            if (onAnalysisComplete) {
              onAnalysisComplete({
                ...results,
                analysis_id: analysisId,
              });
            }

            // Close WebSocket
            if (wsRef.current) {
              wsRef.current.close();
              wsRef.current = null;
            }
          },

          onError: (error) => {
            console.error("Analysis error:", error);
            setProgress({
              stage: "Error",
              progress: 0,
              message: error,
              error: true,
            });
          },

          onClose: (code, reason) => {
            console.log("WebSocket closed:", code, reason);
            if (isAnalyzing && code !== 1000) {
              // Unexpected close
              setProgress({
                stage: "Error",
                progress: 0,
                message: "Connection lost during analysis",
                error: true,
              });
            }
          },
        });
      }
    } catch (error) {
      console.error("Analysis failed:", error);
      setIsAnalyzing(false);
      setProgress({
        stage: "Error",
        progress: 0,
        message: error.message || "Analysis request failed",
        error: true,
      });
    }
  };

  const handleCancel = () => {
    setIsAnalyzing(false);

    // Close WebSocket connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    // Reset progress
    setProgress({
      stage: "",
      progress: 0,
      message: "",
      error: null,
    });
  };

  return (
    <>
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">
          Analyze Website Performance
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="url"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Website URL
            </label>
            <input
              type="text"
              id="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="Enter website URL (e.g., example.com)"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              disabled={isAnalyzing}
            />
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              id="screenshots"
              checked={includeScreenshots}
              onChange={(e) => setIncludeScreenshots(e.target.checked)}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              disabled={isAnalyzing}
            />
            <label
              htmlFor="screenshots"
              className="ml-2 block text-sm text-gray-700"
            >
              Include screenshots (desktop & mobile)
            </label>
          </div>

          <button
            type="submit"
            disabled={isAnalyzing || !url.trim()}
            className={`w-full py-3 px-4 rounded-lg font-medium transition-colors ${
              isAnalyzing || !url.trim()
                ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                : "bg-blue-500 hover:bg-blue-600 text-white"
            }`}
          >
            {isAnalyzing ? "Analyzing..." : "Analyze Website"}
          </button>
        </form>

        {/* Analysis Instructions */}
        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
          <h3 className="text-sm font-medium text-blue-900 mb-2">
            What we analyze:
          </h3>
          <ul className="text-sm text-blue-700 space-y-1">
            <li>• Page load speed and Core Web Vitals</li>
            <li>• SEO optimization and meta tags</li>
            <li>• Security headers and SSL configuration</li>
            <li>• Mobile responsiveness and usability</li>
          </ul>
        </div>
      </div>

      {/* Progress Modal */}
      <AnalysisProgress
        isVisible={isAnalyzing}
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
