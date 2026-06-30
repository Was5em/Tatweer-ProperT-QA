import React from "react";

function KPICards({ stats }) {
  const numericPassRate = parseInt(stats.passRate) || 0;
  const avgScoreVal = stats.avgScore || 0;

  const renderSparkline = (color) => {
    const data = stats.trends || [];
    if (data.length < 2) return null;
    const width = 120;
    const height = 40;
    const max = 100;
    
    const points = data.map((item, index) => {
      const x = (index / (data.length - 1)) * width;
      const y = height - (item.score / max) * height;
      return `${x},${y}`;
    }).join(" ");

    return (
      <svg width={width} height={height} style={{ overflow: "visible" }}>
        <polyline
          fill="none"
          stroke={color}
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          points={points}
        />
      </svg>
    );
  };

  return (
    <div className="kpi-grid">
      {/* Total Audited Calls */}
      <div className="kpi-card">
        <div className="kpi-details">
          <span className="kpi-title">Total Audits</span>
          <div className="kpi-value">{stats.totalAudits}</div>
          <span className="kpi-subtext">Calls evaluated</span>
        </div>
        <div className="kpi-chart-side">
          {renderSparkline("var(--color-primary)")}
        </div>
      </div>

      {/* Overall Pass Rate */}
      <div className="kpi-card">
        <div className="kpi-details">
          <span className="kpi-title">Overall Pass Rate</span>
          <div className="kpi-value">{stats.passRate}</div>
          <span className="kpi-subtext">Target: &gt;85% pass rate</span>
        </div>
        <div className="kpi-chart-side">
          <svg width="60" height="60">
            <circle cx="30" cy="30" r="24" fill="none" stroke="var(--border)" strokeWidth="5" />
            <circle 
              className="progress-ring-circle" 
              cx="30" 
              cy="30" 
              r="24" 
              fill="none" 
              stroke="var(--color-success)" 
              strokeWidth="5" 
              strokeDasharray="150.8"
              strokeDashoffset={150.8 - (numericPassRate / 100) * 150.8}
              strokeLinecap="round"
            />
          </svg>
        </div>
      </div>

      {/* Average Score */}
      <div className="kpi-card">
        <div className="kpi-details">
          <span className="kpi-title">Average Score</span>
          <div className="kpi-value">{stats.avgScore}%</div>
          <span className="kpi-subtext">Quality benchmark</span>
        </div>
        <div className="kpi-chart-side">
          <svg width="70" height="50">
            <path d="M 10,40 A 25,25 0 0,1 60,40" fill="none" stroke="var(--border)" strokeWidth="6" strokeLinecap="round" />
            <path 
              d="M 10,40 A 25,25 0 0,1 60,40" 
              fill="none" 
              stroke="var(--color-primary)" 
              strokeWidth="6" 
              strokeLinecap="round" 
              strokeDasharray="78.5"
              strokeDashoffset={78.5 - (avgScoreVal / 100) * 78.5}
            />
          </svg>
        </div>
      </div>
    </div>
  );
}

export default KPICards;
