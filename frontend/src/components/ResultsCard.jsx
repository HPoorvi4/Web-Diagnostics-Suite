import "./Styles/ResultsCard.css";

const ResultsCard = ({ title, url, date, score }) => {
  return (
    <div className="results-card">
      {/* Header */}
      <div className="results-header">
        <div className="header-content">
          <div className="header-info">
            <h2 className="results-title">{title}</h2>
            <span className="results-url">{url}</span>
            <div className="results-date">{date}</div>
          </div>
          <div className="header-score">{score}</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs-nav">
        <div className="tabs-list">
          <button className="tab-button active">Overview</button>
          <button className="tab-button inactive">Performance</button>
          <button className="tab-button inactive">Security</button>
        </div>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {/* Example Overview */}
        <div className="overview-grid">
          <div className="score-item">SEO Score</div>
          <div className="score-item">Speed</div>
          <div className="score-item">Accessibility</div>
        </div>
      </div>
    </div>
  );
};

export default ResultsCard;
