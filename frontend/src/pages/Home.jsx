import React, { useState, useEffect } from "react";
import AnalyzeForm from "../components/AnalyzeForm";
import ResultsCard from "../components/ResultsCard";
import Layout from "../components/Layout";

const Home = () => {
  const [currentAnalysis, setCurrentAnalysis] = useState(null);
  const [recentAnalyses, setRecentAnalyses] = useState([]);
  const [stats, setStats] = useState({
    total_analyses: 0,
    today_analyses: 0,
    average_scores: {
      speed: 0,
      seo: 0,
      security: 0,
      mobile: 0,
    },
  });
  const [loading, setLoading] = useState(false);

  // Fetch recent analyses and stats on component mount
  useEffect(() => {
    fetchRecentAnalyses();
    fetchStats();
  }, []);

  const fetchRecentAnalyses = async () => {
    try {
      const response = await fetch("http://localhost:8000/history?limit=5");
      if (response.ok) {
        const data = await response.json();
        setRecentAnalyses(data.recent_analyses || []);
      }
    } catch (error) {
      console.error("Error fetching recent analyses:", error);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch("http://localhost:8000/stats");
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error("Error fetching stats:", error);
    }
  };

  const handleAnalysisComplete = (results) => {
    setCurrentAnalysis(results);
    // Refresh recent analyses and stats
    fetchRecentAnalyses();
    fetchStats();
  };

  const handleViewPreviousAnalysis = async (analysisId) => {
    setLoading(true);
    try {
      const response = await fetch(
        `http://localhost:8000/analysis/${analysisId}`
      );
      if (response.ok) {
        const data = await response.json();
        setCurrentAnalysis(data);
      }
    } catch (error) {
      console.error("Error fetching analysis:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleNewAnalysis = () => {
    setCurrentAnalysis(null);
  };

  const getGradeColor = (grade) => {
    switch (grade) {
      case "A":
        return "text-green-600 bg-green-100";
      case "B":
        return "text-blue-600 bg-blue-100";
      case "C":
        return "text-yellow-600 bg-yellow-100";
      case "D":
        return "text-orange-600 bg-orange-100";
      case "F":
        return "text-red-600 bg-red-100";
      default:
        return "text-gray-600 bg-gray-100";
    }
  };

  return (
    <Layout>
      <div className="min-h-screen bg-gray-50">
        {/* Header Section */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
            <div className="text-center">
              <h1 className="text-4xl font-bold mb-4">WebAudit Pro</h1>
              <p className="text-xl text-blue-100 mb-8 max-w-3xl mx-auto">
                Professional web diagnostics and analysis suite. Get
                comprehensive insights into your website's performance, SEO,
                security, and mobile experience.
              </p>

              {/* Stats Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 max-w-4xl mx-auto">
                <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4">
                  <div className="text-2xl font-bold">
                    {stats.total_analyses}
                  </div>
                  <div className="text-sm text-blue-100">Total Analyses</div>
                </div>
                <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4">
                  <div className="text-2xl font-bold">
                    {stats.today_analyses}
                  </div>
                  <div className="text-sm text-blue-100">Today</div>
                </div>
                <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4">
                  <div className="text-2xl font-bold">
                    {Math.round(
                      (stats.average_scores.speed +
                        stats.average_scores.seo +
                        stats.average_scores.security +
                        stats.average_scores.mobile) /
                        4
                    )}
                  </div>
                  <div className="text-sm text-blue-100">Avg Score</div>
                </div>
                <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4">
                  <div className="text-2xl font-bold">20-30s</div>
                  <div className="text-sm text-blue-100">Avg Time</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {!currentAnalysis ? (
            <div className="space-y-8">
              {/* Main Analysis Form */}
              <AnalyzeForm onAnalysisComplete={handleAnalysisComplete} />

              {/* Recent Analyses Section */}
              {recentAnalyses.length > 0 && (
                <div className="bg-white rounded-lg shadow-md p-6">
                  <div className="flex items-center justify-between mb-6">
                    <h2 className="text-2xl font-bold text-gray-900">
                      Recent Analyses
                    </h2>
                    <span className="text-sm text-gray-500">
                      Click any analysis to view details
                    </span>
                  </div>

                  <div className="space-y-4">
                    {recentAnalyses.map((analysis) => (
                      <div
                        key={analysis.id}
                        onClick={() => handleViewPreviousAnalysis(analysis.id)}
                        className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 cursor-pointer transition-all duration-200 group"
                      >
                        <div className="flex-1">
                          <div className="flex items-center space-x-3">
                            <div className="flex-shrink-0">
                              <div
                                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getGradeColor(
                                  analysis.overall_grade
                                )}`}
                              >
                                Grade {analysis.overall_grade}
                              </div>
                            </div>
                            <div>
                              <p className="text-sm font-medium text-gray-900 group-hover:text-blue-600">
                                {analysis.url}
                              </p>
                              <p className="text-sm text-gray-500">
                                Score: {analysis.overall_score}/100 •{" "}
                                {new Date(
                                  analysis.analyzed_at
                                ).toLocaleDateString()}
                              </p>
                            </div>
                          </div>
                        </div>

                        <div className="flex-shrink-0">
                          <svg
                            className="w-5 h-5 text-gray-400 group-hover:text-blue-500 transition-colors"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth="2"
                              d="M9 5l7 7-7 7"
                            />
                          </svg>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Features Section */}
              <div className="bg-white rounded-lg shadow-md p-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-6 text-center">
                  Comprehensive Website Analysis
                </h2>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  <div className="text-center">
                    <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                      <svg
                        className="w-6 h-6 text-blue-600"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="2"
                          d="M13 10V3L4 14h7v7l9-11h-7z"
                        />
                      </svg>
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      Performance
                    </h3>
                    <p className="text-sm text-gray-600">
                      Core Web Vitals, load times, resource optimization, and
                      page speed insights
                    </p>
                  </div>

                  <div className="text-center">
                    <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                      <svg
                        className="w-6 h-6 text-green-600"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="2"
                          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                        />
                      </svg>
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      SEO
                    </h3>
                    <p className="text-sm text-gray-600">
                      Meta tags, structured data, content optimization, and
                      search visibility
                    </p>
                  </div>

                  <div className="text-center">
                    <div className="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                      <svg
                        className="w-6 h-6 text-red-600"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="2"
                          d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                        />
                      </svg>
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      Security
                    </h3>
                    <p className="text-sm text-gray-600">
                      SSL certificates, security headers, vulnerability scanning
                    </p>
                  </div>

                  <div className="text-center">
                    <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                      <svg
                        className="w-6 h-6 text-purple-600"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="2"
                          d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z"
                        />
                      </svg>
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      Mobile
                    </h3>
                    <p className="text-sm text-gray-600">
                      Responsiveness, device compatibility, touch usability
                      testing
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            /* Results View */
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <button
                  onClick={handleNewAnalysis}
                  className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors"
                >
                  <svg
                    className="w-4 h-4 mr-2"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M10 19l-7-7m0 0l7-7m-7 7h18"
                    />
                  </svg>
                  Analyze Another Website
                </button>

                <div className="text-sm text-gray-500">
                  {currentAnalysis.cached && (
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
                </div>
              </div>

              <ResultsCard analysis={currentAnalysis} />
            </div>
          )}

          {loading && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
              <div className="bg-white rounded-lg p-6 flex items-center space-x-3">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                <span className="text-gray-700">Loading analysis...</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
};

export default Home;
