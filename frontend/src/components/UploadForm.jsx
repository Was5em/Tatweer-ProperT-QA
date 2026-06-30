import React, { useState } from "react";
import axios from "axios";
import { UploadCloud } from "lucide-react";

function UploadForm({ API_URL, fetchData, setAuditing, setCurrentStep, setLatestResult, setAuditError }) {
  const [agentName, setAgentName] = useState("");
  const [callId, setCallId] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);

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

  return (
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
          disabled={!selectedFile}
          style={{ width: "100%", padding: "0.9rem" }}
        >
          Start AI Audit
        </button>
      </form>
    </div>
  );
}

export default UploadForm;
