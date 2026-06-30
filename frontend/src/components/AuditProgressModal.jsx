import React from "react";
import { AlertCircle, CheckCircle, FolderOpen } from "lucide-react";

function AuditProgressModal({ auditing, setAuditing, currentStep, auditError, latestResult }) {
  if (!auditing) return null;

  return (
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
                <div className="modal-info-value" style={{ color: "var(--color-success)" }}>
                  {typeof latestResult.Total_Score === 'number' ? `${latestResult.Total_Score}%` : latestResult.Total_Score}
                </div>
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
                  View Report PDF
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
  );
}

export default AuditProgressModal;
