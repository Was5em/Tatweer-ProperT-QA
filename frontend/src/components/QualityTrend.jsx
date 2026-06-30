import React from "react";
import { TrendingUp } from "lucide-react";

function QualityTrend({ stats, timeframe, setTimeframe }) {
  const renderTrendChart = () => {
    const data = stats.trends || [];
    if (data.length === 0) {
      return (
        <div style={{ display: "flex", height: "100%", alignItems: "center", justifyContent: "center", color: "#64748b" }}>
          No quality trend data available.
        </div>
      );
    }

    const width = 500;
    const height = 220;
    const paddingLeft = 40;
    const paddingRight = 20;
    const paddingTop = 20;
    const paddingBottom = 30;

    const chartWidth = width - paddingLeft - paddingRight;
    const chartHeight = height - paddingTop - paddingBottom;

    const points = data.map((item, index) => {
      const x = paddingLeft + (index / (data.length - 1)) * chartWidth;
      const y = paddingTop + chartHeight - (item.score / 100) * chartHeight;
      return { x, y, score: item.score, name: item.name };
    });

    const linePath = points.reduce((path, p, i) => {
      return i === 0 ? `M ${p.x} ${p.y}` : `${path} L ${p.x} ${p.y}`;
    }, "");

    const areaPath = points.length > 0 
      ? `${linePath} L ${points[points.length - 1].x} ${paddingTop + chartHeight} L ${points[0].x} ${paddingTop + chartHeight} Z`
      : "";

    return (
      <svg viewBox={`0 0 ${width} ${height}`} width="100%" height="100%" style={{ overflow: "visible" }}>
        <defs>
          <linearGradient id="trendGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-primary)" stopOpacity="0.2" />
            <stop offset="100%" stopColor="var(--color-primary)" stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {/* Gridlines */}
        {[0, 50, 100].map((val) => {
          const y = paddingTop + chartHeight - (val / 100) * chartHeight;
          return (
            <g key={val}>
              <line 
                x1={paddingLeft} 
                y1={y} 
                x2={width - paddingRight} 
                y2={y} 
                stroke="var(--border)" 
                strokeDasharray="3 3" 
              />
              <text x={paddingLeft - 10} y={y + 4} fill="var(--text2)" fontSize="9" textAnchor="end">{val}%</text>
            </g>
          );
        })}

        {areaPath && <path d={areaPath} fill="url(#trendGradient)" />}
        {linePath && <path d={linePath} fill="none" stroke="var(--color-primary)" strokeWidth="2.5" />}

        {points.map((p, i) => (
          <circle 
            key={i}
            cx={p.x} 
            cy={p.y} 
            r="4.5" 
            fill="var(--bg2)" 
            stroke="var(--color-primary)" 
            strokeWidth="2" 
          />
        ))}
      </svg>
    );
  };

  return (
    <div className="widget-panel">
      <div className="widget-header">
        <h3 className="widget-title">
          <TrendingUp size={18} style={{ color: "var(--color-primary)" }} />
          Audit Quality Trend
        </h3>
        <div className="timeframe-tabs">
          {["Day", "Week", "Month"].map((tab) => (
            <button 
              key={tab} 
              className={`timeframe-tab ${timeframe === tab ? "active" : ""}`}
              onClick={() => setTimeframe(tab)}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>
      <div className="chart-container">
        {renderTrendChart()}
      </div>
    </div>
  );
}

export default QualityTrend;
