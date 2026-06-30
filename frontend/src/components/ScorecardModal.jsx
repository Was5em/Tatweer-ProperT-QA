import React from "react";
import { FolderOpen } from "lucide-react";

function ScorecardModal({ selectedAudit, setSelectedAudit }) {
  if (!selectedAudit) return null;

  return (
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
            <div className="modal-info-value" style={{ color: "var(--color-success)" }}>
              {typeof selectedAudit.Total_Score === 'number' ? `${selectedAudit.Total_Score}%` : selectedAudit.Total_Score}
            </div>
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
            <div style={{ fontSize: "0.75rem", color: "#64748b" }}>Execution</div>
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
          {selectedAudit.doc_url && selectedAudit.doc_url !== "#" && (
            <a href={selectedAudit.doc_url} target="_blank" rel="noreferrer" className="btn btn-primary" style={{ flex: 1, textDecoration: "none", fontSize: "0.85rem", textAlign: "center", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <FolderOpen size={16} style={{ marginRight: "0.5rem" }} />
              Download Report PDF
            </a>
          )}
          <button className="btn btn-outline" style={{ flex: 1 }} onClick={() => setSelectedAudit(null)}>
            Close Scorecard
          </button>
        </div>
      </div>
    </div>
  );
}

export default ScorecardModal;
