// src/components/ResultsCard.jsx
import React, { useState } from "react";
import ScoreCircle from "./ScoreCircle";

const ResultsCard = ({ results }) => {
  const [activeTab, setActiveTab] = useState("overview");
  const [selectedDevice, setSelectedDevice] = useState("desktop");

  if (!results) {
    return null;
  }

  const {
    url,
    overall_score,
    speed_analysis,
    seo_analysis,
    security_analysis,
    mobile_analysis,
    screenshots,
    analysis_id,
    created_at,
  } = results;

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const getSpeedMetrics = () => {
    if (!speed_analysis?.metrics) return [];

    return [
      {
        name: "First Contentful Paint",
        value: speed_analysis.metrics.first_contentful_paint,
        unit: "s",
      },
      {
        name: "Largest Contentful Paint",
        value: speed_analysis.metrics.largest_contentful_paint,
        unit: "s",
      },
      {
        name: "Cumulative Layout Shift",
        value: speed_analysis.metrics.cumulative_layout_shift,
        unit: "",
      },
      {
        name: "Total Blocking Time",
        value: speed_analysis.metrics.total_blocking_time,
        unit: "ms",
      },
    ];
  };

  const tabs = [
    { id: "overview", name: "Overview" },
    { id: "speed", name: "Performance" },
    { id: "seo", name: "SEO" },
    { id: "security", name: "Security" },
    { id: "mobile", name: "Mobile" },
    { id: "screenshots", name: "Screenshots" },
  ];

  return (
    <div className="bg-white rounded-lg shadow-lg">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex justify-between items-start">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              Analysis Results
            </h2>
            <p className="text-sm text-gray-500 mt-1">{url}</p>
            {created_at && (
              <p className="text-xs text-gray-400 mt-1">
                Analyzed on {formatDate(created_at)}
              </p>
            )}
          </div>
          <div className="flex items-center space-x-4">
            <ScoreCircle
              score={overall_score}
              size={80}
              title="Overall Score"
            />
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="px-6 flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              {tab.name}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="p-6">
        {activeTab === "overview" && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="text-center">
              <ScoreCircle
                score={speed_analysis?.score || 0}
                size={100}
                title="Performance"
              />
            </div>
            <div className="text-center">
              <ScoreCircle
                score={seo_analysis?.score || 0}
                size={100}
                title="SEO"
              />
            </div>
            <div className="text-center">
              <ScoreCircle
                score={security_analysis?.score || 0}
                size={100}
                title="Security"
              />
            </div>
            <div className="text-center">
              <ScoreCircle
                score={mobile_analysis?.score || 0}
                size={100}
                title="Mobile"
              />
            </div>
          </div>
        )}

        {activeTab === "speed" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <ScoreCircle
                score={speed_analysis?.score || 0}
                title="Performance Score"
              />
              <div className="text-right">
                <p className="text-2xl font-bold text-gray-900">
                  {speed_analysis?.load_time || 0}s
                </p>
                <p className="text-sm text-gray-500">Load Time</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {getSpeedMetrics().map((metric, index) => (
                <div key={index} className="bg-gray-50 p-4 rounded-lg">
                  <h4 className="font-medium text-gray-900">{metric.name}</h4>
                  <p className="text-2xl font-bold text-blue-600 mt-1">
                    {metric.value}
                    {metric.unit}
                  </p>
                </div>
              ))}
            </div>

            {speed_analysis?.issues && speed_analysis.issues.length > 0 && (
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-3">
                  Performance Issues
                </h3>
                <ul className="space-y-2">
                  {speed_analysis.issues.map((issue, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <span className="text-red-500 mt-1">⚠</span>
                      <span className="text-gray-700">{issue}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {activeTab === "seo" && (
          <div className="space-y-6">
            <ScoreCircle score={seo_analysis?.score || 0} title="SEO Score" />

            {seo_analysis?.meta_tags && (
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-3">
                  Meta Tags
                </h3>
                <div className="grid grid-cols-1 gap-4">
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <h4 className="font-medium text-gray-900">Title</h4>
                    <p className="text-gray-700 mt-1">
                      {seo_analysis.meta_tags.title || "Not found"}
                    </p>
                  </div>
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <h4 className="font-medium text-gray-900">Description</h4>
                    <p className="text-gray-700 mt-1">
                      {seo_analysis.meta_tags.description || "Not found"}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {seo_analysis?.issues && seo_analysis.issues.length > 0 && (
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-3">
                  SEO Issues
                </h3>
                <ul className="space-y-2">
                  {seo_analysis.issues.map((issue, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <span className="text-orange-500 mt-1">⚠</span>
                      <span className="text-gray-700">{issue}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {activeTab === "security" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <ScoreCircle
                score={security_analysis?.score || 0}
                title="Security Score"
              />
              <div className="text-right">
                <p className="text-lg font-medium text-gray-900">
                  {security_analysis?.security_level || "Unknown"}
                </p>
                <p className="text-sm text-gray-500">Security Level</p>
              </div>
            </div>

            {security_analysis?.ssl_info && (
              <div className="bg-gray-50 p-4 rounded-lg">
                <h3 className="text-lg font-medium text-gray-900 mb-3">
                  SSL Certificate
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm font-medium text-gray-700">Status</p>
                    <p
                      className={`text-sm ${
                        security_analysis.ssl_info.valid
                          ? "text-green-600"
                          : "text-red-600"
                      }`}
                    >
                      {security_analysis.ssl_info.valid ? "Valid" : "Invalid"}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-700">Issuer</p>
                    <p className="text-sm text-gray-900">
                      {security_analysis.ssl_info.issuer || "Unknown"}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {security_analysis?.issues &&
              security_analysis.issues.length > 0 && (
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-3">
                    Security Issues
                  </h3>
                  <ul className="space-y-2">
                    {security_analysis.issues.map((issue, index) => (
                      <li key={index} className="flex items-start space-x-2">
                        <span className="text-red-500 mt-1">🔒</span>
                        <span className="text-gray-700">{issue}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
          </div>
        )}

        {activeTab === "mobile" && (
          <div className="space-y-6">
            <ScoreCircle
              score={mobile_analysis?.score || 0}
              title="Mobile Score"
            />

            {mobile_analysis?.device_compatibility && (
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-3">
                  Device Compatibility
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {Object.entries(mobile_analysis.device_compatibility).map(
                    ([device, compatible]) => (
                      <div key={device} className="bg-gray-50 p-4 rounded-lg">
                        <h4 className="font-medium text-gray-900 capitalize">
                          {device}
                        </h4>
                        <p
                          className={`text-sm font-medium mt-1 ${
                            compatible ? "text-green-600" : "text-red-600"
                          }`}
                        >
                          {compatible ? "Compatible" : "Issues Found"}
                        </p>
                      </div>
                    )
                  )}
                </div>
              </div>
            )}

            {mobile_analysis?.issues && mobile_analysis.issues.length > 0 && (
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-3">
                  Mobile Issues
                </h3>
                <ul className="space-y-2">
                  {mobile_analysis.issues.map((issue, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <span className="text-orange-500 mt-1">📱</span>
                      <span className="text-gray-700">{issue}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {activeTab === "screenshots" && (
          <div className="space-y-6">
            {screenshots && Object.keys(screenshots).length > 0 && (
              <>
                <div className="flex space-x-4 border-b">
                  {Object.keys(screenshots).map((device) => (
                    <button
                      key={device}
                      onClick={() => setSelectedDevice(device)}
                      className={`py-2 px-4 font-medium text-sm capitalize transition-colors ${
                        selectedDevice === device
                          ? "text-blue-600 border-b-2 border-blue-500"
                          : "text-gray-500 hover:text-gray-700"
                      }`}
                    >
                      {device}
                    </button>
                  ))}
                </div>

                <div className="text-center">
                  <h3 className="text-lg font-medium text-gray-900 mb-4 capitalize">
                    {selectedDevice} View
                  </h3>
                  <div className="inline-block border border-gray-200 rounded-lg overflow-hidden shadow-sm">
                    <img
                      src={screenshots[selectedDevice]}
                      alt={`${selectedDevice} screenshot`}
                      className="max-w-full h-auto"
                      style={{ maxHeight: "600px" }}
                    />
                  </div>
                </div>
              </>
            )}

            {(!screenshots || Object.keys(screenshots).length === 0) && (
              <div className="text-center py-8">
                <p className="text-gray-500">No screenshots available</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ResultsCard;
