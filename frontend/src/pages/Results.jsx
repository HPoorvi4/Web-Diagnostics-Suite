import React, { useState } from "react";

const ResultsCard = ({ analysis }) => {
  const [activeTab, setActiveTab] = useState("overview");
  const [expandedSection, setExpandedSection] = useState(null);

  if (!analysis) {
    return null;
  }

  // Helper functions
  const getGradeColor = (grade) => {
    switch (grade?.toUpperCase()) {
      case "A":
        return "text-green-600 bg-green-100 border-green-200";
      case "B":
        return "text-blue-600 bg-blue-100 border-blue-200";
      case "C":
        return "text-yellow-600 bg-yellow-100 border-yellow-200";
      case "D":
        return "text-orange-600 bg-orange-100 border-orange-200";
      case "F":
        return "text-red-600 bg-red-100 border-red-200";
      default:
        return "text-gray-600 bg-gray-100 border-gray-200";
    }
  };

  const getScoreColor = (score) => {
    if (score >= 90) return "text-green-600";
    if (score >= 80) return "text-blue-600";
    if (score >= 70) return "text-yellow-600";
    if (score >= 60) return "text-orange-600";
    return "text-red-600";
  };

  const getProgressColor = (score) => {
    if (score >= 90) return "bg-green-500";
    if (score >= 80) return "bg-blue-500";
    if (score >= 70) return "bg-yellow-500";
    if (score >= 60) return "bg-orange-500";
    return "bg-red-500";
  };

  const formatBytes = (bytes) => {
    if (!bytes) return "N/A";
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round((bytes / Math.pow(1024, i)) * 100) / 100 + " " + sizes[i];
  };

  const formatTime = (seconds) => {
    if (!seconds) return "N/A";
    return `${seconds.toFixed(2)}s`;
  };

  const ScoreCircle = ({ score, label, size = "large" }) => {
    const radius = size === "large" ? 45 : 35;
    const circumference = 2 * Math.PI * radius;
    const strokeDasharray = circumference;
    const strokeDashoffset = circumference - (score / 100) * circumference;

    return (
      <div
        className={`flex flex-col items-center ${
          size === "large" ? "space-y-2" : "space-y-1"
        }`}
      >
        <div className="relative">
          <svg
            className={size === "large" ? "w-24 h-24" : "w-20 h-20"}
            viewBox="0 0 100 100"
          >
            <circle
              cx="50"
              cy="50"
              r={radius}
              stroke="currentColor"
              strokeWidth="8"
              fill="transparent"
              className="text-gray-200"
            />
            <circle
              cx="50"
              cy="50"
              r={radius}
              stroke="currentColor"
              strokeWidth="8"
              fill="transparent"
              strokeDasharray={strokeDasharray}
              strokeDashoffset={strokeDashoffset}
              className={`${getScoreColor(
                score
              )} transition-all duration-1000 ease-out`}
              style={{
                transformOrigin: "50% 50%",
                transform: "rotate(-90deg)",
              }}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span
              className={`${
                size === "large" ? "text-2xl" : "text-xl"
              } font-bold ${getScoreColor(score)}`}
            >
              {score}
            </span>
          </div>
        </div>
        <div
          className={`${
            size === "large" ? "text-sm" : "text-xs"
          } font-medium text-gray-600 text-center`}
        >
          {label}
        </div>
      </div>
    );
  };

  const MetricCard = ({ title, value, description, icon, color = "blue" }) => (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-2">
        <div className={`p-2 rounded-lg bg-${color}-100`}>{icon}</div>
        <div className="text-right">
          <div className="text-2xl font-bold text-gray-900">{value}</div>
          <div className="text-xs text-gray-500">{description}</div>
        </div>
      </div>
      <h3 className="text-sm font-medium text-gray-700">{title}</h3>
    </div>
  );

  const RecommendationsList = ({ recommendations, title }) => {
    if (!recommendations || recommendations.length === 0) return null;

    return (
      <div className="mb-6">
        <h4 className="text-lg font-semibold text-gray-900 mb-3">{title}</h4>
        <div className="space-y-2">
          {recommendations.map((rec, index) => (
            <div
              key={index}
              className="flex items-start space-x-3 p-3 bg-blue-50 rounded-lg"
            >
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
              <p className="text-sm text-gray-700">{rec}</p>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const tabs = [
    { id: "overview", label: "Overview", icon: "📊" },
    { id: "performance", label: "Performance", icon: "⚡" },
    { id: "seo", label: "SEO", icon: "🔍" },
    { id: "security", label: "Security", icon: "🔒" },
    { id: "mobile", label: "Mobile", icon: "📱" },
    { id: "screenshots", label: "Screenshots", icon: "📸" },
  ];

  return (
    <div className="bg-white rounded-lg shadow-lg overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold mb-2">Analysis Results</h1>
            <p className="text-blue-100 text-lg">{analysis.url}</p>
          </div>
          <div className="text-right">
            <div
              className={`inline-flex items-center px-4 py-2 rounded-full text-lg font-bold border-2 ${getGradeColor(
                analysis.overall_grade
              )}`}
            >
              Grade {analysis.overall_grade}
            </div>
            <div className="text-blue-100 text-sm mt-2">
              Analyzed: {new Date(analysis.analyzed_at).toLocaleString()}
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8 px-6" aria-label="Tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 ${
                activeTab === tab.id
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="p-6">
        {activeTab === "overview" && (
          <div className="space-y-8">
            {/* Overall Score */}
            <div className="text-center">
              <ScoreCircle
                score={analysis.overall_score}
                label="Overall Score"
              />
            </div>

            {/* Category Scores */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <ScoreCircle
                score={analysis.speed?.score || 0}
                label="Performance"
                size="small"
              />
              <ScoreCircle
                score={analysis.seo?.score || 0}
                label="SEO"
                size="small"
              />
              <ScoreCircle
                score={analysis.security?.score || 0}
                label="Security"
                size="small"
              />
              <ScoreCircle
                score={analysis.mobile?.score || 0}
                label="Mobile"
                size="small"
              />
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <MetricCard
                title="Page Load Time"
                value={formatTime(analysis.speed?.load_time)}
                description="Time to fully load"
                color="blue"
                icon={
                  <svg
                    className="w-5 h-5 text-blue-600"
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
                }
              />
              <MetricCard
                title="Page Size"
                value={formatBytes(analysis.speed?.page_size)}
                description="Total resource size"
                color="green"
                icon={
                  <svg
                    className="w-5 h-5 text-green-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                    />
                  </svg>
                }
              />
              <MetricCard
                title="HTTP Requests"
                value={analysis.speed?.requests_count || "N/A"}
                description="Total requests made"
                color="purple"
                icon={
                  <svg
                    className="w-5 h-5 text-purple-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z"
                    />
                  </svg>
                }
              />
            </div>

            {/* Critical Issues */}
            {analysis.critical_issues &&
              analysis.critical_issues.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <h3 className="text-lg font-semibold text-red-800 mb-3 flex items-center">
                    <svg
                      className="w-5 h-5 mr-2"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                        clipRule="evenodd"
                      />
                    </svg>
                    Critical Issues
                  </h3>
                  <div className="space-y-2">
                    {analysis.critical_issues.map((issue, index) => (
                      <div key={index} className="flex items-start space-x-2">
                        <div className="flex-shrink-0 w-2 h-2 bg-red-500 rounded-full mt-2"></div>
                        <p className="text-sm text-red-700">{issue}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            {/* Top Recommendations */}
            {analysis.top_recommendations && (
              <RecommendationsList
                recommendations={analysis.top_recommendations}
                title="Top Recommendations"
              />
            )}
          </div>
        )}

        {activeTab === "performance" && analysis.speed && (
          <div className="space-y-6">
            <div className="flex items-center space-x-4">
              <ScoreCircle
                score={analysis.speed.score}
                label="Performance Score"
              />
              <div className="flex-1">
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  Performance Analysis
                </h3>
                <p className="text-gray-600">
                  This section analyzes your website's loading speed, Core Web
                  Vitals, and performance optimization opportunities.
                </p>
              </div>
            </div>

            {/* Performance Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {analysis.speed.load_time && (
                <MetricCard
                  title="Load Time"
                  value={formatTime(analysis.speed.load_time)}
                  description="Time to fully load"
                  color="blue"
                  icon={
                    <svg
                      className="w-5 h-5 text-blue-600"
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
                  }
                />
              )}
              {analysis.speed.page_size && (
                <MetricCard
                  title="Page Size"
                  value={formatBytes(analysis.speed.page_size)}
                  description="Total resource size"
                  color="green"
                  icon={
                    <svg
                      className="w-5 h-5 text-green-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                      />
                    </svg>
                  }
                />
              )}
              {analysis.speed.requests_count && (
                <MetricCard
                  title="HTTP Requests"
                  value={analysis.speed.requests_count}
                  description="Total requests made"
                  color="purple"
                  icon={
                    <svg
                      className="w-5 h-5 text-purple-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z"
                      />
                    </svg>
                  }
                />
              )}
            </div>

            {/* Recommendations */}
            {analysis.speed.recommendations && (
              <RecommendationsList
                recommendations={analysis.speed.recommendations}
                title="Performance Improvements"
              />
            )}

            {/* Detailed Issues */}
            {analysis.speed.issues && analysis.speed.issues.length > 0 && (
              <div>
                <h4 className="text-lg font-semibold text-gray-900 mb-3">
                  Performance Issues
                </h4>
                <div className="space-y-2">
                  {analysis.speed.issues.map((issue, index) => (
                    <div
                      key={index}
                      className="flex items-start space-x-3 p-3 bg-yellow-50 rounded-lg"
                    >
                      <div className="flex-shrink-0 w-5 h-5 bg-yellow-500 rounded-full flex items-center justify-center mt-0.5">
                        <span className="text-white text-xs">!</span>
                      </div>
                      <p className="text-sm text-gray-700">{issue}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === "seo" && analysis.seo && (
          <div className="space-y-6">
            <div className="flex items-center space-x-4">
              <ScoreCircle score={analysis.seo.score} label="SEO Score" />
              <div className="flex-1">
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  SEO Analysis
                </h3>
                <p className="text-gray-600">
                  Search engine optimization analysis covering meta tags,
                  structured data, and content optimization.
                </p>
              </div>
            </div>

            {/* SEO Recommendations */}
            {analysis.seo.recommendations && (
              <RecommendationsList
                recommendations={analysis.seo.recommendations}
                title="SEO Improvements"
              />
            )}

            {/* SEO Issues */}
            {analysis.seo.issues && analysis.seo.issues.length > 0 && (
              <div>
                <h4 className="text-lg font-semibold text-gray-900 mb-3">
                  SEO Issues
                </h4>
                <div className="space-y-2">
                  {analysis.seo.issues.map((issue, index) => (
                    <div
                      key={index}
                      className="flex items-start space-x-3 p-3 bg-yellow-50 rounded-lg"
                    >
                      <div className="flex-shrink-0 w-5 h-5 bg-yellow-500 rounded-full flex items-center justify-center mt-0.5">
                        <span className="text-white text-xs">!</span>
                      </div>
                      <p className="text-sm text-gray-700">{issue}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === "security" && analysis.security && (
          <div className="space-y-6">
            <div className="flex items-center space-x-4">
              <ScoreCircle
                score={analysis.security.score}
                label="Security Score"
              />
              <div className="flex-1">
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  Security Analysis
                </h3>
                <p className="text-gray-600">
                  Security assessment including SSL certificates, security
                  headers, and vulnerability checks.
                </p>
              </div>
            </div>

            {/* Security Recommendations */}
            {analysis.security.recommendations && (
              <RecommendationsList
                recommendations={analysis.security.recommendations}
                title="Security Improvements"
              />
            )}

            {/* Security Issues */}
            {analysis.security.issues &&
              analysis.security.issues.length > 0 && (
                <div>
                  <h4 className="text-lg font-semibold text-gray-900 mb-3">
                    Security Issues
                  </h4>
                  <div className="space-y-2">
                    {analysis.security.issues.map((issue, index) => (
                      <div
                        key={index}
                        className="flex items-start space-x-3 p-3 bg-red-50 rounded-lg"
                      >
                        <div className="flex-shrink-0 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center mt-0.5">
                          <span className="text-white text-xs">!</span>
                        </div>
                        <p className="text-sm text-gray-700">{issue}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
          </div>
        )}

        {activeTab === "mobile" && analysis.mobile && (
          <div className="space-y-6">
            <div className="flex items-center space-x-4">
              <ScoreCircle score={analysis.mobile.score} label="Mobile Score" />
              <div className="flex-1">
                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  Mobile Analysis
                </h3>
                <p className="text-gray-600">
                  Mobile experience evaluation including responsiveness, device
                  compatibility, and touch usability.
                </p>
              </div>
            </div>

            {/* Mobile Recommendations */}
            {analysis.mobile.recommendations && (
              <RecommendationsList
                recommendations={analysis.mobile.recommendations}
                title="Mobile Improvements"
              />
            )}

            {/* Mobile Issues */}
            {analysis.mobile.issues && analysis.mobile.issues.length > 0 && (
              <div>
                <h4 className="text-lg font-semibold text-gray-900 mb-3">
                  Mobile Issues
                </h4>
                <div className="space-y-2">
                  {analysis.mobile.issues.map((issue, index) => (
                    <div
                      key={index}
                      className="flex items-start space-x-3 p-3 bg-yellow-50 rounded-lg"
                    >
                      <div className="flex-shrink-0 w-5 h-5 bg-yellow-500 rounded-full flex items-center justify-center mt-0.5">
                        <span className="text-white text-xs">!</span>
                      </div>
                      <p className="text-sm text-gray-700">{issue}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === "screenshots" && analysis.screenshots && (
          <div className="space-y-6">
            <h3 className="text-xl font-semibold text-gray-900">Screenshots</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {analysis.screenshots.desktop && (
                <div className="space-y-3">
                  <h4 className="text-lg font-medium text-gray-700">
                    Desktop View
                  </h4>
                  <div className="border border-gray-200 rounded-lg overflow-hidden">
                    <img
                      src={analysis.screenshots.desktop}
                      alt="Desktop screenshot"
                      className="w-full h-auto"
                      onError={(e) => {
                        e.target.style.display = "none";
                        e.target.nextSibling.style.display = "block";
                      }}
                    />
                    <div className="hidden p-8 text-center text-gray-500">
                      Desktop screenshot not available
                    </div>
                  </div>
                </div>
              )}
              {analysis.screenshots.mobile && (
                <div className="space-y-3">
                  <h4 className="text-lg font-medium text-gray-700">
                    Mobile View
                  </h4>
                  <div className="border border-gray-200 rounded-lg overflow-hidden max-w-xs mx-auto">
                    <img
                      src={analysis.screenshots.mobile}
                      alt="Mobile screenshot"
                      className="w-full h-auto"
                      onError={(e) => {
                        e.target.style.display = "none";
                        e.target.nextSibling.style.display = "block";
                      }}
                    />
                    <div className="hidden p-8 text-center text-gray-500">
                      Mobile screenshot not available
                    </div>
                  </div>
                </div>
              )}
            </div>
            {!analysis.screenshots.desktop && !analysis.screenshots.mobile && (
              <div className="text-center py-8 text-gray-500">
                No screenshots available for this analysis
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="bg-gray-50 px-6 py-4 border-t border-gray-200">
        <div className="flex items-center justify-between text-sm text-gray-600">
          <div>
            Analysis completed in{" "}
            {analysis.analysis_duration
              ? `${analysis.analysis_duration.toFixed(1)}s`
              : "N/A"}
          </div>
          <div className="flex items-center space-x-4">
            {analysis.cached && (
              <span className="inline-flex items-center">
                <svg
                  className="w-4 h-4 mr-1"
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
                Cached result
              </span>
            )}
            <button
              onClick={() => window.print()}
              className="inline-flex items-center text-blue-600 hover:text-blue-800"
            >
              <svg
                className="w-4 h-4 mr-1"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"
                />
              </svg>
              Print Report
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ResultsCard;
