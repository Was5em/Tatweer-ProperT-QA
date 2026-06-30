import React, { useState } from "react";
import { List, Search } from "lucide-react";

function CallLogTable({ history, setSelectedAudit }) {
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [agentFilter, setAgentFilter] = useState("All");

  // Unique agents list helper for filter dropdown
  const getUniqueAgents = () => {
    const agents = history.map(item => item.Agent_Name);
    return [...new Set(agents)].filter(Boolean);
  };

  // Filtered History
  const filteredHistory = history.filter(item => {
    const matchesSearch = 
      (item.Agent_Name || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.Call_ID || "").toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesStatus = statusFilter === "All" || item.Pass_Fail === statusFilter;
    const matchesAgent = agentFilter === "All" || item.Agent_Name === agentFilter;
    
    return matchesSearch && matchesStatus && matchesAgent;
  });

  return (
    <div className="widget-panel table-panel">
      <div className="widget-header" style={{ marginBottom: "1.5rem" }}>
        <h3 className="widget-title">
          <List size={18} style={{ color: "var(--color-primary)" }} />
          Call Log Database
        </h3>
      </div>

      {/* Filter controls */}
      <div className="filter-bar">
        <div className="search-input-wrapper">
          <input 
            type="text" 
            placeholder="Search by ID or Agent..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="floating-input"
            style={{ padding: "0.75rem 1rem 0.75rem 2.5rem", fontSize: "0.85rem" }}
          />
          <Search size={15} className="search-icon" />
        </div>

        <div className="filter-dropdowns">
          {/* Agent Filter */}
          <select 
            value={agentFilter}
            onChange={(e) => setAgentFilter(e.target.value)}
            className="filter-select"
          >
            <option value="All">All Agents</option>
            {getUniqueAgents().map(agent => (
              <option key={agent} value={agent}>{agent}</option>
            ))}
          </select>

          {/* Status Filter */}
          <select 
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="filter-select"
          >
            <option value="All">All Statuses</option>
            <option value="Pass">Pass</option>
            <option value="Fail">Fail</option>
          </select>
        </div>
      </div>

      <div className="data-table-wrapper">
        <table className="saas-table">
          <thead>
            <tr>
              <th>Call ID</th>
              <th>Agent Name</th>
              <th>Timestamp</th>
              <th>Status</th>
              <th>Score</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredHistory.length > 0 ? (
              filteredHistory.map((item, index) => (
                <tr key={index}>
                  <td style={{ fontWeight: "700" }}>{item.Call_ID}</td>
                  <td style={{ fontWeight: "700" }}>{item.Agent_Name}</td>
                  <td style={{ color: "#64748b" }}>{item.Call_Timestamp}</td>
                  <td>
                    <span className={`status-badge ${item.Pass_Fail === "Pass" ? "pass" : "fail"}`}>
                      {item.Pass_Fail === "Pass" ? "Pass" : "Fail"}
                    </span>
                  </td>
                  <td style={{ fontWeight: "800", color: "var(--color-primary)" }}>
                    {typeof item.Total_Score === 'number' ? `${item.Total_Score}%` : item.Total_Score}
                  </td>
                  <td>
                    <button className="btn-action-view" onClick={() => setSelectedAudit(item)}>
                      View Scorecard
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="6" style={{ textAlign: "center", padding: "4rem", color: "#64748b" }}>
                  No call logs matched the filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default CallLogTable;
