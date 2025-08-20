// src/components/AnalysisProgress.jsx
import React from "react";
import "./Styles/AnalysisProgress.css";

const AnalysisProgress = ({
  isVisible,
  stage,
  progress,
  message,
  error,
  onCancel,
}) => {
  if (!isVisible) return null;

  return (
    <div className="ap-overlay">
      <div className="ap-modal">
        <div className="ap-header">
          {error ? (
            <div className="ap-error-icon">
              <svg
                className="ap-icon"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
                />
              </svg>
            </div>
          ) : (
            <div className="ap-loader">
              <div className="ap-spinner"></div>
            </div>
          )}

          <h3
            className={`ap-title ${error ? "ap-error-text" : "ap-normal-text"}`}
          >
            {error ? "Analysis Failed" : "Analyzing Website"}
          </h3>
        </div>

        {!error && (
          <div className="ap-progress-section">
            <div className="ap-progress-bar-wrapper">
              <div className="ap-progress-labels">
                <span>{stage || "Processing..."}</span>
                <span>{Math.round(progress || 0)}%</span>
              </div>
              <div className="ap-progress-bg">
                <div
                  className="ap-progress-fill"
                  style={{ width: `${Math.min(progress || 0, 100)}%` }}
                >
                  <div className="ap-progress-glow"></div>
                </div>
              </div>
            </div>

            <div className="ap-current-stage">
              <div className="ap-stage-indicator">
                <div className="ap-stage-dot"></div>
                <p className="ap-stage-text">{stage || "Initializing..."}</p>
              </div>

              {message && <p className="ap-stage-message">{message}</p>}
            </div>

            <div className="ap-stage-steps">
              {[25, 50, 75, 100].map((val, idx) => (
                <div
                  key={idx}
                  className={`ap-step ${
                    progress >= val ? "ap-step-active" : ""
                  }`}
                ></div>
              ))}
            </div>
          </div>
        )}

        {error && (
          <div className="ap-error-section">
            <h4 className="ap-error-title">Analysis Error</h4>
            <p className="ap-error-message">
              {message || "An unexpected error occurred during analysis."}
            </p>
          </div>
        )}

        <div className="ap-actions">
          <button
            onClick={onCancel}
            className={`ap-button ${
              error ? "ap-button-error" : "ap-button-cancel"
            }`}
          >
            {error ? "Close" : "Cancel Analysis"}
          </button>

          {!error && (
            <div className="ap-info-text">
              <svg
                className="ap-info-icon"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              Usually takes 20-30 seconds
            </div>
          )}
        </div>

        {!error && (
          <div className="ap-additional-info">
            <div className="ap-info-grid">
              <div className="ap-info-item performance"></div>
              <span>Performance</span>
              <div className="ap-info-item seo"></div>
              <span>SEO</span>
              <div className="ap-info-item security"></div>
              <span>Security</span>
              <div className="ap-info-item mobile"></div>
              <span>Mobile</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AnalysisProgress;
