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
        setProgress({
          stage: "Complete!",
          progress: 100,
          message: "Using cached results",
          error: null,
        });

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
            setProgress((prev) => ({
              ...prev,
              message: "Connected to analysis session",
            }));
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
            setIsAnalyzing(false);
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
              setIsAnalyzing(false);
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

  const handleReset = () => {
    setUrl("");
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
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900">
            Analyze Website Performance
          </h2>
          {url && (
            <button
              onClick={handleReset}
              className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
              disabled={isAnalyzing}
            >
              Reset Form
            </button>
          )}
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label
              htmlFor="url"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Website URL *
            </label>
            <div className="relative">
              <input
                type="text"
                id="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="Enter website URL (e.g., example.com or https://example.com)"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                disabled={isAnalyzing}
                required
              />
              <div className="absolute inset-y-0 right-0 flex items-center pr-3">
                <svg
                  className="h-5 w-5 text-gray-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9v-9m0-9v9"
                  />
                </svg>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="text-sm font-medium text-gray-700">
              Analysis Options
            </h3>
            <div className="flex items-center">
              <input
                type="checkbox"
                id="screenshots"
                checked={includeScreenshots}
                onChange={(e) => setIncludeScreenshots(e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded transition-colors"
                disabled={isAnalyzing}
              />
              <label
                htmlFor="screenshots"
                className="ml-3 block text-sm text-gray-700"
              >
                Include screenshots (desktop, tablet & mobile views)
                <span className="text-xs text-gray-500 block">
                  This may increase analysis time by 10-15 seconds
                </span>
              </label>
            </div>
          </div>

          <button
            type="submit"
            disabled={isAnalyzing || !url.trim()}
            className={`w-full py-3 px-6 rounded-lg font-medium transition-all duration-200 ${
              isAnalyzing || !url.trim()
                ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                : "bg-blue-600 hover:bg-blue-700 text-white shadow-md hover:shadow-lg transform hover:scale-[1.02]"
            }`}
          >
            {isAnalyzing ? (
              <div className="flex items-center justify-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>Analyzing...</span>
              </div>
            ) : (
              "Start Analysis"
            )}
          </button>
        </form>

        {/* Analysis Information */}
        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
          <h3 className="text-sm font-medium text-blue-900 mb-3">
            What we analyze:
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="flex items-start space-x-2">
              <div className="flex-shrink-0 w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center mt-0.5">
                <svg
                  className="w-3 h-3 text-white"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div>
                <p className="text-sm font-medium text-blue-900">Performance</p>
                <p className="text-xs text-blue-700">
                  Page load speed, Core Web Vitals, resource optimization
                </p>
              </div>
            </div>

            <div className="flex items-start space-x-2">
              <div className="flex-shrink-0 w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center mt-0.5">
                <svg
                  className="w-3 h-3 text-white"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div>
                <p className="text-sm font-medium text-blue-900">SEO</p>
                <p className="text-xs text-blue-700">
                  Meta tags, structured data, content optimization
                </p>
              </div>
            </div>

            <div className="flex items-start space-x-2">
              <div className="flex-shrink-0 w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center mt-0.5">
                <svg
                  className="w-3 h-3 text-white"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div>
                <p className="text-sm font-medium text-blue-900">Security</p>
                <p className="text-xs text-blue-700">
                  SSL certificates, security headers, vulnerabilities
                </p>
              </div>
            </div>

            <div className="flex items-start space-x-2">
              <div className="flex-shrink-0 w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center mt-0.5">
                <svg
                  className="w-3 h-3 text-white"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div>
                <p className="text-sm font-medium text-blue-900">Mobile</p>
                <p className="text-xs text-blue-700">
                  Responsiveness, device compatibility, touch usability
                </p>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-blue-200">
            <p className="text-xs text-blue-600">
              ⏱️ Typical analysis takes 20-30 seconds • 📊 Results are cached
              for faster future access
            </p>
          </div>
        </div>

        {/* Show last progress message if there was an error */}
        {progress.error && !isAnalyzing && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-start space-x-2">
              <svg
                className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
              <div>
                <h4 className="text-sm font-medium text-red-800">
                  Analysis Failed
                </h4>
                <p className="text-sm text-red-700 mt-1">{progress.message}</p>
                <button
                  onClick={handleReset}
                  className="text-sm text-red-600 hover:text-red-800 font-medium mt-2"
                >
                  Try Again
                </button>
              </div>
            </div>
          </div>
        )}
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
