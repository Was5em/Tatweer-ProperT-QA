import React, { useState, useEffect } from "react";
import axios from "axios";
import { 
  Activity, 
  BarChart2, 
  CheckCircle, 
  AlertCircle, 
  UploadCloud, 
  FileText, 
  List, 
  TrendingUp, 
  Award,
  Search,
  ExternalLink,
  Clock,
  User,
  Hash,
  RefreshCw,
  FolderOpen,
  Settings,
  ShieldCheck,
  Calendar,
  Filter,
  Check,
  AlertTriangle
} from "lucide-react";

// API Base URL
const API_URL = "http://localhost:5000/api";

function App() {
  const [history, setHistory] = useState([]);
  const [stats, setStats] = useState({
    totalAudits: 0,
    passRate: "0%",
    avgScore: 0,
    avgCC: 0,
    avgBC: 0,
    avgEC: 0,
    avgNC: 0,
    trends: [],
    agentRankings: []
  });
  
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [connectionError, setConnectionError] = useState("");
  const [timeframe, setTimeframe] = useState("Week"); // "Day", "Week", "Month"
  
  // Upload Call form state
  const [agentName, setAgentName] = useState("");
  const [callId, setCallId] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  
  // Auditing progress state
  const [auditing, setAuditing] = useState(false);
  const [currentStep, setCurrentStep] = useState(0); // 0: Idle, 1: Uploading, 2: AI Analysis, 5: Complete
  const [auditError, setAuditError] = useState("");
  const [latestResult, setLatestResult] = useState(null);
  
  // Table filters
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [agentFilter, setAgentFilter] = useState("All");

  // Selected audit for scorecard view
  const [selectedAudit, setSelectedAudit] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    setConnectionError("");
    try {
      const [historyRes, statsRes] = await Promise.all([
        axios.get(`${API_URL}/history`),
        axios.get(`${API_URL}/stats`)
      ]);
      if (historyRes.data.success) setHistory(historyRes.data.data);
      if (statsRes.data.success) setStats(statsRes.data.data);
    } catch (err) {
      console.error("Error loading dashboard data:", err);
      setConnectionError("Unable to connect to the backend server on port 5000. Please ensure the API server is running ('npm run dev').");
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    setConnectionError("");
    try {
      const [historyRes, statsRes] = await Promise.all([
        axios.get(`${API_URL}/history`),
        axios.get(`${API_URL}/stats`)
      ]);
      if (historyRes.data.success) setHistory(historyRes.data.data);
      if (statsRes.data.success) setStats(statsRes.data.data);
    } catch (err) {
      console.error("Error refreshing data:", err);
      setConnectionError("Failed to refresh dashboard. Backend API is unreachable.");
    } finally {
      setRefreshing(false);
    }
  };

  // Drag-and-Drop file handlers
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleStartAudit = async (e) => {
    e.preventDefault();
    if (!selectedFile) return;

    setAuditing(true);
    setAuditError("");
    setLatestResult(null);
    setCurrentStep(1); // Uploading

    const formData = new FormData();
    formData.append("audio", selectedFile);
    formData.append("agent_name", agentName || "Unknown Agent");
    if (callId) formData.append("call_id", callId);

    try {
      // Simulate progress step transition
      setTimeout(() => {
        setCurrentStep(2); // AI Analysis
      }, 1500);

      const response = await axios.post(`${API_URL}/audit`, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });

      if (response.data.success) {
        setCurrentStep(5); // Complete
        setLatestResult(response.data.data);
        setSelectedFile(null);
        setAgentName("");
        setCallId("");
        fetchData();
      } else {
        throw new Error(response.data.error || "Failed to process audio.");
      }
    } catch (err) {
      console.error("Audit processing error:", err);
      setAuditError(err.response?.data?.error || err.message || "An unexpected error occurred.");
      setCurrentStep(0);
    }
  };

  // Unique agents list helper for filter dropdown
  const getUniqueAgents = () => {
    const agents = history.map(item => item.Agent_Name);
    return [...new Set(agents)].filter(Boolean);
  };

  // Filtered History
  const filteredHistory = history.filter(item => {
    const matchesSearch = 
      item.Agent_Name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.Call_ID.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesStatus = statusFilter === "All" || item.Pass_Fail === statusFilter;
    const matchesAgent = agentFilter === "All" || item.Agent_Name === agentFilter;
    
    return matchesSearch && matchesStatus && matchesAgent;
  });

  // Calculate stats parameters
  const numericPassRate = parseInt(stats.passRate) || 0;
  const avgScoreVal = stats.avgScore || 0;

  // Visual SVG Renderers
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
    <div className="app-container">
      {/* Top Header */}
      <div className="dashboard-header">
        <div>
          <h1 className="brand-title">OS Precision Audit</h1>
          <p className="brand-subtitle">Automated Call Quality Monitoring & Generative AI Scorecards</p>
        </div>
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          <div className="status-indicator" style={{ marginRight: "0.5rem" }}>
            <div className={`indicator-dot ${connectionError ? "offline" : ""}`}></div>
            <span style={{ fontSize: "0.85rem", color: "#64748b", fontWeight: "600" }}>
              {connectionError ? "API Offline" : "System Connected"}
            </span>
          </div>
          <button className="btn btn-outline" onClick={handleRefresh} disabled={refreshing}>
            <RefreshCw className={refreshing ? "spin-fast" : ""} size={15} style={{ marginRight: "0.5rem" }} />
            Refresh
          </button>
        </div>
      </div>

      {connectionError && (
        <div className="error-banner">
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <AlertCircle size={20} style={{ color: "var(--color-danger)" }} />
            <div>
              <p style={{ fontWeight: "700" }}>Connection Failure</p>
              <p style={{ fontSize: "0.8rem", opacity: 0.8 }}>{connectionError}</p>
            </div>
          </div>
          <button className="btn btn-outline" style={{ padding: "0.4rem 0.8rem", fontSize: "0.75rem" }} onClick={fetchData}>
            Retry
          </button>
        </div>
      )}

      {loading ? (
        <div className="widget-panel" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "6rem 0", gap: "1.5rem" }}>
          <RefreshCw className="spin-fast" size={40} style={{ color: "var(--color-primary)" }} />
          <p style={{ color: "#64748b", fontSize: "0.9rem" }}>Loading system analytics and metrics...</p>
        </div>
      ) : (
        <>
          {/* Top KPI Cards Row */}
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

            {/* Overall Pass Rate with Progress Ring */}
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

            {/* Average Score with Arc Gauge */}
            <div className="kpi-card">
              <div className="kpi-details">
                <span className="kpi-title">Average Score</span>
                <div className="kpi-value">{stats.avgScore}%</div>
                <span className="kpi-subtext">Quality benchmark</span>
              </div>
              <div className="kpi-chart-side">
                <svg width="70" height="50">
                  {/* Track Arc (180deg) */}
                  <path d="M 10,40 A 25,25 0 0,1 60,40" fill="none" stroke="var(--border)" strokeWidth="6" strokeLinecap="round" />
                  {/* Fill Arc */}
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

          {/* Main Content Grid: Trend and Upload Form */}
          <div className="dashboard-columns">
            {/* Left: Quality Trend Chart */}
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

            {/* Right: Embedded Upload Call Form */}
            <div className="widget-panel">
              <div className="widget-header">
                <h3 className="widget-title">
                  <UploadCloud size={18} style={{ color: "var(--color-primary)" }} />
                  Upload Call Audio
                </h3>
              </div>
              <form onSubmit={handleStartAudit} className="upload-form-card">
                <div className="floating-group">
                  <input 
                    type="text" 
                    placeholder=" " 
                    value={agentName}
                    onChange={(e) => setAgentName(e.target.value)}
                    className="floating-input"
                    required
                  />
                  <label className="floating-label">Agent Name</label>
                </div>

                <div className="floating-group">
                  <input 
                    type="text" 
                    placeholder=" " 
                    value={callId}
                    onChange={(e) => setCallId(e.target.value)}
                    className="floating-input"
                  />
                  <label className="floating-label">Call ID (Optional)</label>
                </div>

                <div 
                  className={`drag-drop-area ${dragActive ? "dragover" : ""}`}
                  onDragEnter={handleDrag}
                  onDragOver={handleDrag}
                  onDragLeave={handleDrag}
                  onDrop={handleDrop}
                  onClick={() => document.getElementById("audio-uploader-input").click()}
                >
                  <input 
                    type="file" 
                    id="audio-uploader-input" 
                    accept="audio/*" 
                    onChange={handleFileChange} 
                    style={{ display: "none" }}
                  />
                  <UploadCloud className="drag-drop-icon" />
                  {selectedFile ? (
                    <div>
                      <p style={{ fontWeight: "700", fontSize: "0.9rem" }}>{selectedFile.name}</p>
                      <p style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "0.15rem" }}>
                        ({(selectedFile.size / (1024 * 1024)).toFixed(2)} MB)
                      </p>
                    </div>
                  ) : (
                    <div>
                      <p style={{ fontWeight: "700", fontSize: "0.9rem" }}>Drag & Drop Call Audio</p>
                      <p style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "0.15rem" }}>
                        Supports MP3, WAV, M4A
                      </p>
                    </div>
                  )}
                </div>

                <button 
                  type="submit" 
                  className="btn btn-primary" 
                  disabled={!selectedFile || auditing}
                  style={{ width: "100%", padding: "0.9rem" }}
                >
                  Start AI Audit
                </button>
              </form>
            </div>
          </div>

          {/* Lower Grid: Call Logs (Left) & Top Performers (Right) */}
          <div className="dashboard-columns">
            {/* Left: Call Log Table */}
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
                          <td style={{ fontWeight: "800", color: "var(--color-primary)" }}>{item.Total_Score}</td>
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

            {/* Right: Leaderboard */}
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
                    const initials = agent.name.split(" ").map(n => n[0]).join("").toUpperCase().substring(0, 2);
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
          </div>
        </>
      )}

      {/* PROCESS PROGRESS MODAL */}
      {auditing && (
        <div className="modal-backdrop">
          <div className="modal-content-panel" style={{ textAlign: "center" }}>
            <h3 style={{ fontSize: "1.35rem", fontWeight: "800", marginBottom: "1rem" }}>OS Audit Processing</h3>
            <p style={{ color: "#64748b", fontSize: "0.9rem" }}>
              Audio upload and Generative AI transcription scorecard analysis in progress...
            </p>

            <div className="audit-progress-ring-container">
              <svg width="100" height="100">
                <circle cx="50" cy="50" r="45" fill="none" stroke="var(--border)" strokeWidth="6" />
                <circle className="audit-pulse-circle" cx="50" cy="50" r="45" />
              </svg>
            </div>

            <div style={{ marginTop: "2rem" }}>
              <div className={`step-row ${currentStep >= 1 ? "active" : ""} ${currentStep > 1 || currentStep === 5 ? "completed" : ""}`}>
                <div className="step-indicator-dot"></div>
                <span>Uploading call recording files...</span>
              </div>
              <div className={`step-row ${currentStep >= 2 ? "active" : ""} ${currentStep > 2 || currentStep === 5 ? "completed" : ""}`}>
                <div className="step-indicator-dot"></div>
                <span>Auditing audio transcription via Gemini 2.5 Flash...</span>
              </div>
              <div className={`step-row ${currentStep === 5 ? "completed" : ""}`}>
                <div className="step-indicator-dot"></div>
                <span>Logging Sheet logs, rendering Docs scorecard, and dispatching report...</span>
              </div>
            </div>

            {auditError && (
              <div className="widget-panel" style={{ background: "rgba(244, 63, 94, 0.03)", border: "1px solid rgba(244, 63, 94, 0.15)", padding: "1.25rem", marginTop: "1.5rem", textAlign: "left" }}>
                <div style={{ display: "flex", gap: "0.5rem", color: "var(--color-danger)", marginBottom: "0.5rem" }}>
                  <AlertCircle size={18} />
                  <span style={{ fontWeight: "700" }}>Audit Failed</span>
                </div>
                <p style={{ fontSize: "0.85rem", color: "#fda4af" }}>{auditError}</p>
                <button className="btn btn-outline" style={{ marginTop: "1rem", width: "100%" }} onClick={() => setAuditing(false)}>
                  Dismiss
                </button>
              </div>
            )}

            {latestResult && (
              <div className="widget-panel" style={{ border: "1px solid rgba(16, 185, 129, 0.2)", padding: "1.5rem", marginTop: "1.5rem", textAlign: "left" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--color-success)" }}>
                    <CheckCircle size={20} />
                    <h4 style={{ fontWeight: "700" }}>Audit Completed</h4>
                  </div>
                  <span className={`status-badge ${latestResult.Pass_Fail === "Pass" ? "pass" : "fail"}`}>
                    {latestResult.Pass_Fail}
                  </span>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", marginBottom: "1rem" }}>
                  <div className="modal-info-box">
                    <div className="modal-info-label">Agent</div>
                    <div className="modal-info-value">{latestResult.Agent_Name}</div>
                  </div>
                  <div className="modal-info-box">
                    <div className="modal-info-label">Score</div>
                    <div className="modal-info-value" style={{ color: "var(--color-success)" }}>{latestResult.Total_Score}</div>
                  </div>
                  <div className="modal-info-box">
                    <div className="modal-info-label">Call ID</div>
                    <div className="modal-info-value">{latestResult.Call_ID}</div>
                  </div>
                  <div className="modal-info-box">
                    <div className="modal-info-label">Audited At</div>
                    <div className="modal-info-value" style={{ fontSize: "0.8rem" }}>{latestResult.Call_Timestamp}</div>
                  </div>
                </div>

                <p style={{ fontWeight: "bold", margin: "1rem 0 0.4rem 0", fontSize: "0.85rem", color: "#64748b" }}>AI Evaluation Feedback:</p>
                <div style={{ background: "rgba(255,255,255,0.015)", padding: "1rem", borderRadius: "8px", fontSize: "0.85rem", maxHeight: "100px", overflowY: "auto", border: "1px solid rgba(255,255,255,0.02)" }}>
                  {latestResult.AI_Feedback}
                </div>

                <div style={{ display: "flex", gap: "0.75rem", marginTop: "1.5rem" }}>
                  {latestResult.doc_url && latestResult.doc_url !== "#" && (
                    <a href={latestResult.doc_url} target="_blank" rel="noreferrer" className="btn btn-primary" style={{ flex: 1, textDecoration: "none", fontSize: "0.85rem" }}>
                      <FolderOpen size={16} style={{ marginRight: "0.5rem" }} />
                      View Google Doc
                    </a>
                  )}
                  <button className="btn btn-outline" style={{ flex: 1, fontSize: "0.85rem" }} onClick={() => setAuditing(false)}>
                    Close
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* SCORECARD DETAIL VIEW MODAL */}
      {selectedAudit && (
        <div className="modal-backdrop" onClick={() => setSelectedAudit(null)}>
          <div className="modal-content-panel" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close-btn" onClick={() => setSelectedAudit(null)}>×</button>
            
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem", borderBottom: "1px solid var(--border-color)", paddingBottom: "1rem" }}>
              <div>
                <h3 style={{ fontSize: "1.35rem", fontWeight: "800" }}>Quality Scorecard</h3>
                <p style={{ color: "#64748b", fontSize: "0.85rem", marginTop: "0.15rem" }}>
                  Detailed call evaluation & compliance findings
                </p>
              </div>
              <span className={`status-badge ${selectedAudit.Pass_Fail === "Pass" ? "pass" : "fail"}`}>
                {selectedAudit.Pass_Fail}
              </span>
            </div>

            {/* General Info */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
              <div className="modal-info-box">
                <div className="modal-info-label">Agent Name</div>
                <div className="modal-info-value">{selectedAudit.Agent_Name}</div>
              </div>
              <div className="modal-info-box">
                <div className="modal-info-label">Call ID</div>
                <div className="modal-info-value">{selectedAudit.Call_ID}</div>
              </div>
              <div className="modal-info-box">
                <div className="modal-info-label">Evaluation Date</div>
                <div className="modal-info-value">{selectedAudit.Call_Timestamp}</div>
              </div>
              <div className="modal-info-box">
                <div className="modal-info-label">Total Score</div>
                <div className="modal-info-value" style={{ color: "var(--color-success)" }}>{selectedAudit.Total_Score}</div>
              </div>
            </div>

            {/* Criteria Scores */}
            <h4 style={{ fontSize: "0.95rem", fontWeight: "700", marginBottom: "0.75rem", color: "#64748b" }}>Criteria Performance:</h4>
            <div className="criteria-scores" style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.75rem", marginBottom: "1.5rem" }}>
              <div className="criterion-card" style={{ padding: "0.75rem", textAlign: "center" }}>
                <div style={{ fontSize: "0.75rem", color: "#64748b" }}>Connection</div>
                <div style={{ fontSize: "1.25rem", fontWeight: "bold" }}>{selectedAudit.CC}</div>
              </div>
              <div className="criterion-card" style={{ padding: "0.75rem", textAlign: "center" }}>
                <div style={{ fontSize: "0.75rem", color: "#64748b" }}>Compliance</div>
                <div style={{ fontSize: "1.25rem", fontWeight: "bold" }}>{selectedAudit.BC}</div>
              </div>
              <div className="criterion-card" style={{ padding: "0.75rem", textAlign: "center" }}>
                <div style={{ fontSize: "0.75rem", color: "#64748b" }}>Solution</div>
                <div style={{ fontSize: "1.25rem", fontWeight: "bold" }}>{selectedAudit.EC}</div>
              </div>
              <div className="criterion-card" style={{ padding: "0.75rem", textAlign: "center" }}>
                <div style={{ fontSize: "0.75rem", color: "#64748b" }}>Next Steps</div>
                <div style={{ fontSize: "1.25rem", fontWeight: "bold" }}>{selectedAudit.NC}</div>
              </div>
            </div>

            {/* Errors */}
            <h4 style={{ fontSize: "0.95rem", fontWeight: "700", marginBottom: "0.5rem", color: "#64748b" }}>Compliance Errors:</h4>
            <div style={{ background: "rgba(244, 63, 94, 0.02)", border: "1px solid rgba(244, 63, 94, 0.15)", padding: "1rem", borderRadius: "8px", marginBottom: "1.5rem", fontSize: "0.85rem", color: "#fda4af", lineHeight: "1.4" }}>
              {selectedAudit.Errors || "No compliance errors detected."}
            </div>

            {/* AI Feedback */}
            <h4 style={{ fontSize: "0.95rem", fontWeight: "700", marginBottom: "0.5rem", color: "#64748b" }}>AI Coach Feedback:</h4>
            <div style={{ background: "rgba(14, 165, 233, 0.02)", border: "1px solid rgba(14, 165, 233, 0.15)", padding: "1.25rem", borderRadius: "8px", fontSize: "0.85rem", color: "#cbd5e1", lineHeight: "1.5", whiteSpace: "pre-line", maxHeight: "180px", overflowY: "auto" }}>
              {selectedAudit.AI_Feedback || "No additional feedback."}
            </div>

            <div style={{ display: "flex", gap: "0.75rem", marginTop: "1.75rem" }}>
              <button className="btn btn-outline" style={{ width: "100%" }} onClick={() => setSelectedAudit(null)}>
                Close Scorecard
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
