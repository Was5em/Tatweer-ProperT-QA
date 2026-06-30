import React from "react";
import { Award } from "lucide-react";

function Leaderboard({ stats }) {
  return (
    <div className="widget-panel">
      <div className="widget-header">
        <h3 className="widget-title">
          <Award size={18} style={{ color: "var(--color-warning)" }} />
          Top Performers
        </h3>
      </div>
      <div className="leaderboard-list">
        {stats.agentRankings && stats.agentRankings.length > 0 ? (
          stats.agentRankings.map((agent, index) => {
            const initials = (agent.name || "")
              .split(" ")
              .map(n => n[0])
              .join("")
              .toUpperCase()
              .substring(0, 2);
            return (
              <div key={index} className="leaderboard-item">
                <div className="leaderboard-agent">
                  <div className="agent-avatar">{initials || "A"}</div>
                  <div className="agent-info">
                    <span className="agent-name">{agent.name}</span>
                    <span className="agent-rank">Rank #{index + 1}</span>
                  </div>
                </div>
                <div className="leaderboard-score-side">
                  <span className="leaderboard-score-value">{agent.avgScore}%</span>
                  <div className="score-progress-container">
                    <div className="score-progress-bar" style={{ width: `${agent.avgScore}%` }}></div>
                  </div>
                </div>
              </div>
            );
          })
        ) : (
          <div style={{ textAlign: "center", color: "#64748b", padding: "3rem 0" }}>
            No leaderboard rankings computed.
          </div>
        )}
      </div>
    </div>
  );
}

export default Leaderboard;
