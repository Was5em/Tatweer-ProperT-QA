import React, { useState, useEffect } from "react";
import axios from "axios";
import { RefreshCw, AlertCircle, LogOut } from "lucide-react";

// Import modular components
import KPICards from "./components/KPICards";
import QualityTrend from "./components/QualityTrend";
import UploadForm from "./components/UploadForm";
import CallLogTable from "./components/CallLogTable";
import Leaderboard from "./components/Leaderboard";
import AuditProgressModal from "./components/AuditProgressModal";
import ScorecardModal from "./components/ScorecardModal";
import LoginView from "./components/LoginView";

// API Base URL
const API_URL = "http://localhost:5000/api";

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem("admin_token"));
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
  
  // Auditing progress state
  const [auditing, setAuditing] = useState(false);
  const [currentStep, setCurrentStep] = useState(0); // 0: Idle, 1: Uploading, 2: AI Analysis, 5: Complete
  const [auditError, setAuditError] = useState("");
  const [latestResult, setLatestResult] = useState(null);
  
  // Selected audit for scorecard view
  const [selectedAudit, setSelectedAudit] = useState(null);

  useEffect(() => {
    if (isAuthenticated) {
      fetchData();
    }
  }, [isAuthenticated]);

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

  const handleLogout = () => {
    localStorage.removeItem("admin_token");
    localStorage.removeItem("admin_user");
    setIsAuthenticated(false);
  };

  if (!isAuthenticated) {
    return <LoginView API_URL={API_URL} onLoginSuccess={() => setIsAuthenticated(true)} />;
  }

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
          <button className="btn btn-outline" onClick={handleLogout} style={{ borderColor: "rgba(244, 63, 94, 0.2)", color: "#fda4af" }}>
            <LogOut size={15} style={{ marginRight: "0.5rem" }} />
            Logout
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
          <KPICards stats={stats} />

          {/* Main Content Grid: Trend and Upload Form */}
          <div className="dashboard-columns">
            {/* Left: Quality Trend Chart */}
            <QualityTrend stats={stats} timeframe={timeframe} setTimeframe={setTimeframe} />

            {/* Right: Embedded Upload Call Form */}
            <UploadForm 
              API_URL={API_URL} 
              fetchData={fetchData} 
              setAuditing={setAuditing} 
              setCurrentStep={setCurrentStep} 
              setLatestResult={setLatestResult} 
              setAuditError={setAuditError} 
            />
          </div>

          {/* Lower Grid: Call Logs (Left) & Top Performers (Right) */}
          <div className="dashboard-columns">
            {/* Left: Call Log Table */}
            <CallLogTable history={history} setSelectedAudit={setSelectedAudit} />

            {/* Right: Leaderboard */}
            <Leaderboard stats={stats} />
          </div>
        </>
      )}

      {/* PROCESS PROGRESS MODAL */}
      <AuditProgressModal 
        auditing={auditing} 
        setAuditing={setAuditing} 
        currentStep={currentStep} 
        auditError={auditError} 
        latestResult={latestResult} 
      />

      {/* SCORECARD DETAIL VIEW MODAL */}
      <ScorecardModal 
        selectedAudit={selectedAudit} 
        setSelectedAudit={setSelectedAudit} 
      />
    </div>
  );
}

export default App;
