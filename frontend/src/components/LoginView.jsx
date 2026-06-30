import React, { useState } from "react";
import axios from "axios";
import { User, Lock, AlertCircle, ShieldCheck } from "lucide-react";

function LoginView({ API_URL, onLoginSuccess }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await axios.post(`${API_URL}/auth/login`, {
        username,
        password
      });

      if (response.data.success) {
        localStorage.setItem("admin_token", response.data.token);
        localStorage.setItem("admin_user", username);
        onLoginSuccess();
      } else {
        setError(response.data.error || "Invalid username or password.");
      }
    } catch (err) {
      console.error("Login request error:", err);
      setError(err.response?.data?.detail || "Connection to auth server failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container" style={{ display: "flex", minHeight: "100vh", alignItems: "center", justifyContent: "center", background: "radial-gradient(circle at top, #0f172a 0%, #020617 100%)" }}>
      <div className="widget-panel" style={{ width: "100%", maxWidth: "420px", padding: "2.5rem", borderRadius: "16px", border: "1px solid rgba(255, 255, 255, 0.05)", background: "rgba(15, 23, 42, 0.6)", backdropFilter: "blur(20px)" }}>
        
        {/* Title / Logo */}
        <div style={{ textAlign: "center", marginBottom: "2rem" }}>
          <div style={{ display: "inline-flex", padding: "1rem", borderRadius: "50%", background: "rgba(237, 66, 36, 0.1)", color: "var(--color-primary)", marginBottom: "1rem" }}>
            <ShieldCheck size={40} />
          </div>
          <h2 style={{ fontSize: "1.75rem", fontWeight: "900", color: "#ffffff", letterSpacing: "-0.5px" }}>OS Precision Audit</h2>
          <p style={{ fontSize: "0.85rem", color: "#64748b", marginTop: "0.25rem" }}>Call Quality QA Portal - Admin Login</p>
        </div>

        {/* Error Banner */}
        {error && (
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", background: "rgba(244, 63, 94, 0.08)", border: "1px solid rgba(244, 63, 94, 0.2)", padding: "0.75rem 1rem", borderRadius: "8px", color: "#fda4af", fontSize: "0.85rem", marginBottom: "1.5rem" }}>
            <AlertCircle size={16} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          
          {/* Username Input */}
          <div className="floating-group" style={{ marginBottom: 0 }}>
            <input 
              type="text" 
              placeholder=" " 
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="floating-input"
              style={{ paddingLeft: "2.75rem" }}
              required
            />
            <User size={18} style={{ position: "absolute", left: "1rem", top: "1rem", color: "#475569" }} />
            <label className="floating-label" style={{ left: "2.75rem" }}>Username</label>
          </div>

          {/* Password Input */}
          <div className="floating-group" style={{ marginBottom: 0 }}>
            <input 
              type="password" 
              placeholder=" " 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="floating-input"
              style={{ paddingLeft: "2.75rem" }}
              required
            />
            <Lock size={18} style={{ position: "absolute", left: "1rem", top: "1rem", color: "#475569" }} />
            <label className="floating-label" style={{ left: "2.75rem" }}>Password</label>
          </div>

          {/* Submit Button */}
          <button 
            type="submit" 
            className="btn btn-primary" 
            disabled={loading}
            style={{ width: "100%", padding: "0.9rem", marginTop: "1rem", fontSize: "0.95rem", fontWeight: "700" }}
          >
            {loading ? "Authenticating..." : "Login to Portal"}
          </button>
        </form>

        <div style={{ textAlign: "center", marginTop: "2rem", fontSize: "0.75rem", color: "#475569" }}>
          OS Precision Audit System v2.0 • Secure Administration
        </div>

      </div>
    </div>
  );
}

export default LoginView;
