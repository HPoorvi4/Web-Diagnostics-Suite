import React, { useState, useEffect } from "react";
import axios from "axios";
import { useParams } from "react-router-dom";

export default function Results() {
  const { analysisId } = useParams();
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    const fetchResults = async () => {
      try {
        const response = await axios.get(
          `http://localhost:5001/api/analysis/${analysisId}`
        );
        setResults(response.data);
      } catch (err) {
        setError("Failed to fetch analysis results.");
      } finally {
        setLoading(false);
      }
    };

    fetchResults();
  }, [analysisId]);

  if (loading) {
    return <p className="results__loading">Loading analysis results...</p>;
  }

  if (error) {
    return <p className="results__error">{error}</p>;
  }

  if (!results) {
    return <p className="results__empty">No results available.</p>;
  }

  const { performance, seo, security, mobile, screenshots } = results;

  return (
    <div className="results">
      <header className="results__header">
        <h1 className="results__title">Analysis Results</h1>
      </header>

      <div className="results__card">
        <h2 className="results__subtitle">Website Overview</h2>
        <p className="results__url">URL: {results.url}</p>
        <p className="results__timestamp">
          Analyzed on: {new Date(results.timestamp).toLocaleString()}
        </p>
      </div>

      <nav className="results__tabs">
        {[
          "overview",
          "performance",
          "seo",
          "security",
          "mobile",
          "screenshots",
        ].map((tab) => (
          <button
            key={tab}
            className={`results__tab ${
              activeTab === tab ? "results__tab--active" : ""
            }`}
            onClick={() => setActiveTab(tab)}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </nav>

      <section className="results__content">
        {activeTab === "overview" && (
          <div className="results__section results__section--overview">
            <p>
              <strong>Overall Score:</strong> {results.overallScore}
            </p>
            <p>
              <strong>Issues Found:</strong> {results.issues.length}
            </p>
            <ul className="results__issues">
              {results.issues.map((issue, index) => (
                <li key={index} className="results__issue">
                  {issue}
                </li>
              ))}
            </ul>
          </div>
        )}

        {activeTab === "performance" && (
          <div className="results__section results__section--performance">
            <h3>Performance Metrics</h3>
            <ul>
              {performance &&
                Object.entries(performance).map(([key, value]) => (
                  <li key={key}>
                    {key}: {value}
                  </li>
                ))}
            </ul>
          </div>
        )}

        {activeTab === "seo" && (
          <div className="results__section results__section--seo">
            <h3>SEO Analysis</h3>
            <ul>
              {seo &&
                Object.entries(seo).map(([key, value]) => (
                  <li key={key}>
                    {key}: {value}
                  </li>
                ))}
            </ul>
          </div>
        )}

        {activeTab === "security" && (
          <div className="results__section results__section--security">
            <h3>Security Analysis</h3>
            <ul>
              {security &&
                Object.entries(security).map(([key, value]) => (
                  <li key={key}>
                    {key}: {value ? "Yes" : "No"}
                  </li>
                ))}
            </ul>
          </div>
        )}

        {activeTab === "mobile" && (
          <div className="results__section results__section--mobile">
            <h3>Mobile-Friendliness</h3>
            <ul>
              {mobile &&
                Object.entries(mobile).map(([key, value]) => (
                  <li key={key}>
                    {key}: {value ? "Yes" : "No"}
                  </li>
                ))}
            </ul>
          </div>
        )}

        {activeTab === "screenshots" && (
          <div className="results__section results__section--screenshots">
            <h3>Screenshots</h3>
            <div className="results__screenshots">
              {screenshots && screenshots.length > 0 ? (
                screenshots.map((src, index) => (
                  <img
                    key={index}
                    src={src}
                    alt={`Screenshot ${index + 1}`}
                    className="results__screenshot"
                  />
                ))
              ) : (
                <p>No screenshots available.</p>
              )}
            </div>
          </div>
        )}
      </section>

      <footer className="results__footer">
        <p>© 2025 Web Diagnostics Suite</p>
      </footer>
    </div>
  );
}
