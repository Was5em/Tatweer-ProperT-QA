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
    <div className="app-container" style={{ display: "flex", minHeight: "100vh", alignItems: "center", justifyContent: "center", background: "linear-gradient(135deg, #f4f7fe 0%, #e9edf7 100%)" }}>
      <div className="widget-panel" style={{ width: "100%", maxWidth: "420px", padding: "2.5rem", borderRadius: "16px", border: "1px solid #e9edf7", background: "#ffffff", boxShadow: "0 20px 25px -5px rgba(112, 144, 176, 0.15), 0 10px 10px -5px rgba(112, 144, 176, 0.1)" }}>
        
        {/* Title / Logo */}
        <div style={{ textAlign: "center", marginBottom: "2rem" }}>
          <div style={{ display: "inline-flex", padding: "1rem", borderRadius: "50%", background: "rgba(67, 24, 255, 0.08)", color: "var(--color-primary)", marginBottom: "1rem" }}>
            <ShieldCheck size={40} />
          </div>
          <h2 style={{ fontSize: "1.75rem", fontWeight: "900", color: "#1b254b", letterSpacing: "-0.5px" }}>OS Precision Audit</h2>
          <p style={{ fontSize: "0.85rem", color: "#a3b1cc", marginTop: "0.25rem", fontWeight: "600" }}>Call Quality QA Portal - Admin Login</p>
        </div>

        {/* Error Banner */}
        {error && (
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", background: "#fdeeed", border: "1px solid #fcdcdc", padding: "0.75rem 1rem", borderRadius: "8px", color: "#ee5d50", fontSize: "0.85rem", marginBottom: "1.5rem" }}>
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
              style={{ paddingLeft: "2.75rem", background: "#ffffff", color: "#1b254b", borderColor: "#e9edf7" }}
              required
            />
            <User size={18} style={{ position: "absolute", left: "1rem", top: "1rem", color: "#a3b1cc" }} />
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
              style={{ paddingLeft: "2.75rem", background: "#ffffff", color: "#1b254b", borderColor: "#e9edf7" }}
              required
            />
            <Lock size={18} style={{ position: "absolute", left: "1rem", top: "1rem", color: "#a3b1cc" }} />
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

        <div style={{ textAlign: "center", marginTop: "2rem", fontSize: "0.75rem", color: "#a3b1cc", fontWeight: "600" }}>
          OS Precision Audit System v2.0 • Secure Administration
        </div>

      </div>
    </div>
  );
}

export default LoginView;
