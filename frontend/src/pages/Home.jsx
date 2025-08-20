import React, { useState, useEffect } from "react";
import AnalyzeForm from "../components/AnalyzeForm";
import ResultsCard from "../components/ResultsCard";
import Layout from "../components/Layout";
import "./Styles/Homes.css";

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
    analysis_available: false,
  });
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState(null);

  const API_BASE_URL = "http://localhost:8000";

  useEffect(() => {
    // Check if backend is available first
    checkBackendHealth();
    fetchRecentAnalyses();
    fetchStats();
  }, []);

  const checkBackendHealth = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      if (!response.ok) {
        throw new Error(`Backend health check failed: ${response.status}`);
      }
      const healthData = await response.json();
      console.log("Backend health:", healthData);
      setApiError(null);
    } catch (error) {
      console.error("Backend health check failed:", error);
      setApiError(
        "Backend server is not responding. Please make sure the backend is running on http://localhost:8000"
      );
    }
  };

  const fetchRecentAnalyses = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/history?limit=5`);
      if (response.ok) {
        const data = await response.json();
        setRecentAnalyses(data.recent_analyses || []);
        console.log("Recent analyses:", data.recent_analyses);
      } else {
        console.warn("Failed to fetch recent analyses:", response.status);
      }
    } catch (error) {
      console.error("Error fetching recent analyses:", error);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/stats`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
        console.log("Stats:", data);
      } else {
        console.warn("Failed to fetch stats:", response.status);
      }
    } catch (error) {
      console.error("Error fetching stats:", error);
    }
  };

  const handleAnalysisComplete = (results) => {
    console.log("Analysis completed:", results);
    setCurrentAnalysis(results);

    // Refresh recent analyses and stats after completion
    setTimeout(() => {
      fetchRecentAnalyses();
      fetchStats();
    }, 1000);
  };

  const handleViewPreviousAnalysis = async (analysisId) => {
    setLoading(true);
    try {
      console.log("Fetching analysis:", analysisId);
      const response = await fetch(`${API_BASE_URL}/analysis/${analysisId}`);
      if (response.ok) {
        const data = await response.json();
        console.log("Previous analysis loaded:", data);
        setCurrentAnalysis(data);
      } else {
        console.error("Failed to fetch analysis:", response.status);
        alert("Failed to load analysis. Please try again.");
      }
    } catch (error) {
      console.error("Error fetching analysis:", error);
      alert("Error loading analysis. Please check your connection.");
    } finally {
      setLoading(false);
    }
  };

  const handleNewAnalysis = () => {
    setCurrentAnalysis(null);
    // Scroll to top to show the form
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const getGradeClass = (grade) => {
    switch (grade) {
      case "A":
        return "grade-pill grade-a";
      case "B":
        return "grade-pill grade-b";
      case "C":
        return "grade-pill grade-c";
      case "D":
        return "grade-pill grade-d";
      case "F":
        return "grade-pill grade-f";
      default:
        return "grade-pill grade-default";
    }
  };

  const formatDate = (dateString) => {
    try {
      return new Date(dateString).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch (e) {
      return "Unknown date";
    }
  };

  const calculateOverallAverage = () => {
    const { speed, seo, security, mobile } = stats.average_scores;
    const average = (speed + seo + security + mobile) / 4;
    return Math.round(average) || 0;
  };

  return (
    <Layout>
      <div className="home-page">
        {/* API Error Banner */}
        {apiError && (
          <div className="api-error-banner">
            <div className="error-content">
              <strong>⚠️ Backend Connection Error:</strong>
              <p>{apiError}</p>
              <button onClick={checkBackendHealth} className="retry-connection">
                Retry Connection
              </button>
            </div>
          </div>
        )}

        {/* Hero Section */}
        <div className="hero-section">
          <div className="hero-content">
            <div className="hero-inner">
              <h1 className="hero-title">WebAudit Pro</h1>
              <p className="hero-subtitle">
                Professional web diagnostics and analysis suite. Get
                comprehensive insights into your website's performance, SEO,
                security, and mobile experience.
              </p>

              {/* Stats Cards */}
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-value">{stats.total_analyses}</div>
                  <div className="stat-label">Total Analyses</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{stats.today_analyses}</div>
                  <div className="stat-label">Today</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{calculateOverallAverage()}</div>
                  <div className="stat-label">Avg Score</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">
                    {stats.analysis_available ? "✓ Ready" : "⚠️ Limited"}
                  </div>
                  <div className="stat-label">Service Status</div>
                </div>
              </div>

              {/* Service Status Indicator */}
              {!stats.analysis_available && (
                <div className="service-warning">
                  <p>
                    ⚠️ Analysis service is running in limited mode. Some
                    features may not be available.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="main-content">
          {!currentAnalysis ? (
            <div className="content-sections">
              {/* Analysis Form */}
              <AnalyzeForm onAnalysisComplete={handleAnalysisComplete} />

              {/* Recent Analyses */}
              {recentAnalyses.length > 0 && (
                <div className="recent-analyses">
                  <div className="recent-analyses-header">
                    <h2 className="recent-analyses-title">Recent Analyses</h2>
                    <span className="recent-analyses-hint">
                      Click any analysis to view details
                    </span>
                  </div>

                  <div className="analyses-list">
                    {recentAnalyses.map((analysis) => (
                      <div
                        key={analysis.id}
                        onClick={() => handleViewPreviousAnalysis(analysis.id)}
                        className="analysis-item"
                        style={{ cursor: "pointer" }}
                      >
                        <div className="analysis-main">
                          <div className="analysis-details">
                            <div className="grade-badge">
                              <div
                                className={getGradeClass(
                                  analysis.overall_grade
                                )}
                              >
                                Grade {analysis.overall_grade}
                              </div>
                            </div>
                            <div className="analysis-info">
                              <p className="analysis-url" title={analysis.url}>
                                {analysis.url.length > 50
                                  ? analysis.url.substring(0, 50) + "..."
                                  : analysis.url}
                              </p>
                              <p className="analysis-meta">
                                Score: {analysis.overall_score}/100 •{" "}
                                {formatDate(analysis.analyzed_at)}
                              </p>
                            </div>
                          </div>
                        </div>

                        <div className="analysis-chevron">➔</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* No Recent Analyses Message */}
              {recentAnalyses.length === 0 && !apiError && (
                <div className="no-analyses">
                  <p>
                    No recent analyses found. Start your first analysis above!
                  </p>
                </div>
              )}

              {/* Features */}
              <div className="features-section">
                <h2 className="features-title">
                  Comprehensive Website Analysis
                </h2>
                <div className="features-grid">
                  <div className="feature-card">
                    <div className="feature-icon-wrapper feature-blue">⚡</div>
                    <h3 className="feature-name">Performance</h3>
                    <p className="feature-desc">
                      Core Web Vitals, load times, resource optimization, and
                      page speed insights
                    </p>
                  </div>

                  <div className="feature-card">
                    <div className="feature-icon-wrapper feature-green">🔍</div>
                    <h3 className="feature-name">SEO</h3>
                    <p className="feature-desc">
                      Meta tags, structured data, content optimization, and
                      search visibility
                    </p>
                  </div>

                  <div className="feature-card">
                    <div className="feature-icon-wrapper feature-red">🔒</div>
                    <h3 className="feature-name">Security</h3>
                    <p className="feature-desc">
                      SSL certificates, security headers, vulnerability scanning
                    </p>
                  </div>

                  <div className="feature-card">
                    <div className="feature-icon-wrapper feature-purple">
                      📱
                    </div>
                    <h3 className="feature-name">Mobile</h3>
                    <p className="feature-desc">
                      Responsiveness, device compatibility, touch usability
                      testing
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="results-section">
              <div className="results-header">
                <button onClick={handleNewAnalysis} className="back-button">
                  ← Analyze Another Website
                </button>
                <div className="results-status">
                  {currentAnalysis.cached && (
                    <span className="cached-result">✔ Cached result</span>
                  )}
                  <span className="analysis-id">
                    Analysis ID: {currentAnalysis.id}
                  </span>
                </div>
              </div>
              <ResultsCard analysis={currentAnalysis} />
            </div>
          )}

          {loading && (
            <div className="loading-overlay">
              <div className="loading-box">
                <div className="spinner"></div>
                <span>Loading analysis...</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
};

export default Home;
