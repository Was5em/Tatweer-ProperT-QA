require("dotenv").config();
const express = require("express");
const cors = require("cors");
const multer = require("multer");
const fs = require("fs");
const path = require("path");

const geminiService = require("./services/geminiService");
const googleSheetsService = require("./services/googleSheetsService");
const googleDocsService = require("./services/googleDocsService");
const gmailService = require("./services/gmailService");

const app = express();
const PORT = process.env.PORT || 5000;

// Enable CORS and JSON parsing with restricted origin
const corsOptions = {
  origin: process.env.ALLOWED_ORIGINS 
    ? process.env.ALLOWED_ORIGINS.split(",") 
    : ["http://localhost:5173", "http://127.0.0.1:5173"],
  optionsSuccessStatus: 200
};
app.use(cors(corsOptions));
app.use(express.json());

// Ensure the local uploads directory exists
const uploadsDir = path.join(__dirname, "uploads");
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir);
  console.log(`Created uploads directory at: ${uploadsDir}`);
}

// Set up Multer for audio file uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, uploadsDir);
  },
  filename: (req, file, cb) => {
    cb(null, `call_${Date.now()}_${file.originalname}`);
  }
});

const upload = multer({
  storage,
  limits: { fileSize: 50 * 1024 * 1024 }, // 50MB limit
  fileFilter: (req, file, cb) => {
    // Only accept audio files
    if (file.mimetype && file.mimetype.startsWith("audio/")) {
      cb(null, true);
    } else {
      cb(new Error("Only audio files are allowed!"), false);
    }
  }
});

/**
 * Helper to clamp values between 0 and 100
 */
function clamp(n) {
  n = Number(n) || 0;
  return Math.max(0, Math.min(100, n));
}

/**
 * Route: POST /api/audit
 * Uploads an audio call, runs Gemini analysis, updates Sheets/Docs, sends email notifications.
 */
app.post("/api/audit", upload.single("audio"), async (req, res) => {
  const file = req.file;
  if (!file) {
    return res.status(400).json({ success: false, error: "Please upload an audio file." });
  }

  const body = req.body || {};
  const agentName = (body.agent_name || "Unknown Agent").trim();
  const callId = (body.call_id || `CALL-${Date.now()}`).trim();
  const now = new Date();
  
  // Date format matching the ar-EG Cairo format
  const formattedDate = now.toLocaleDateString("ar-EG", {
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", timeZone: "Africa/Cairo"
  });

  const metadata = {
    agent_name: agentName,
    call_id: callId,
    formatted_date: formattedDate
  };

  const localFilePath = file.path;

  try {
    console.log(`Starting QA audit process for agent: "${agentName}", Call ID: "${callId}"...`);

    // 1. Analyze using Gemini
    const evaluation = await geminiService.analyzeAudio(localFilePath, file.mimetype);
    console.log("Gemini audio analysis complete.");

    // 2. Parse scores and calculate total
    const scores = evaluation.Scores || {};
    const cc = clamp(scores.CC);
    const bc = clamp(scores.BC);
    const ec = clamp(scores.EC);
    const nc = clamp(scores.NC);
    const totalScore = cc + bc + ec + nc;
    const percentage = Math.round(totalScore / 4);

    const errorsText = Array.isArray(evaluation.Errors)
      ? evaluation.Errors.join(" | ")
      : (evaluation.Errors || "لا يوجد");

    const scorecard = {
      Call_ID: callId,
      Agent_Name: agentName,
      Call_Timestamp: formattedDate,
      Pass_Fail: evaluation.Pass_Fail || "Fail",
      Total_Score: `${percentage}%`,
      CC: cc,
      BC: bc,
      EC: ec,
      NC: nc,
      Errors: errorsText,
      AI_Feedback: evaluation.AI_Feedback || "لا توجد نصائح إضافية."
    };

    // 3. Create Google Doc Report
    let docUrl = "#";
    try {
      docUrl = await googleDocsService.createDocReport(scorecard);
      console.log(`Google Doc report ready: ${docUrl}`);
    } catch (docError) {
      console.error("Failed to create Google Doc report:", docError.message);
      scorecard.Errors += ` | [تنبيه نظام: فشل إنشاء مستند Google Doc: ${docError.message}]`;
    }

    // 4. Log to Google Sheets Dashboard
    try {
      await googleSheetsService.appendToSheet(scorecard);
    } catch (sheetError) {
      console.error("Failed to append to Google Sheets Dashboard:", sheetError.message);
      scorecard.Errors += ` | [تنبيه نظام: فشل التسجيل في جدول البيانات: ${sheetError.message}]`;
    }

    // 5. Send Gmail Report to Supervisors
    try {
      await gmailService.sendSupervisorReport(scorecard, docUrl);
    } catch (emailError) {
      console.error("Failed to send supervisor email report:", emailError.message);
    }

    // Clean up local uploaded file
    fs.unlinkSync(localFilePath);
    console.log(`Cleaned up local file: ${localFilePath}`);

    return res.status(200).json({
      success: true,
      data: {
        ...scorecard,
        doc_url: docUrl
      }
    });

  } catch (error) {
    console.error("Error during call audit process:", error);

    // Send Tech Alert email on failure
    try {
      await gmailService.sendTechAlert(metadata, error.message);
    } catch (emailError) {
      console.error("Failed to send technical alert email:", emailError.message);
    }

    // Clean up local uploaded file on error
    if (fs.existsSync(localFilePath)) {
      fs.unlinkSync(localFilePath);
    }

    return res.status(500).json({
      success: false,
      error: `Failed to audit call audio: ${error.message}`
    });
  }
});

/**
 * Route: GET /api/history
 * Fetches all past call audits directly from the Google Sheets database.
 */
app.get("/api/history", async (req, res) => {
  try {
    const history = await googleSheetsService.readHistoryFromSheet();
    return res.status(200).json({ success: true, data: history });
  } catch (error) {
    return res.status(500).json({ success: false, error: error.message });
  }
});

/**
 * Route: GET /api/stats
 * Aggregates statistics and trends from history for the dashboard graphs.
 */
app.get("/api/stats", async (req, res) => {
  try {
    const history = await googleSheetsService.readHistoryFromSheet();

    if (!history || history.length === 0) {
      return res.status(200).json({
        success: true,
        data: {
          totalAudits: 0,
          passRate: "0%",
          avgScore: 0,
          avgCC: 0,
          avgBC: 0,
          avgEC: 0,
          avgNC: 0,
          trends: [],
          agentRankings: []
        }
      });
    }

    const totalAudits = history.length;
    const passes = history.filter(item => item.Pass_Fail === "Pass").length;
    const passRate = `${Math.round((passes / totalAudits) * 100)}%`;

    let totalScoreSum = 0;
    let ccSum = 0, bcSum = 0, ecSum = 0, ncSum = 0;

    history.forEach(item => {
      const numericScore = parseInt(item.Total_Score) || 0;
      totalScoreSum += numericScore;
      ccSum += item.CC;
      bcSum += item.BC;
      ecSum += item.EC;
      ncSum += item.NC;
    });

    const avgScore = Math.round(totalScoreSum / totalAudits);
    const avgCC = Math.round(ccSum / totalAudits);
    const avgBC = Math.round(bcSum / totalAudits);
    const avgEC = Math.round(ecSum / totalAudits);
    const avgNC = Math.round(ncSum / totalAudits);

    // Format trends data (take last 10 audits chronologically)
    const trends = [...history]
      .reverse()
      .slice(-10)
      .map(item => ({
        name: item.Call_Timestamp.split(" ")[0] || "", // extract date
        score: parseInt(item.Total_Score) || 0,
        agent: item.Agent_Name
      }));

    // Rank agents by average score
    const agentStats = {};
    history.forEach(item => {
      const score = parseInt(item.Total_Score) || 0;
      if (!agentStats[item.Agent_Name]) {
        agentStats[item.Agent_Name] = { name: item.Agent_Name, sum: 0, count: 0 };
      }
      agentStats[item.Agent_Name].sum += score;
      agentStats[item.Agent_Name].count += 1;
    });

    const agentRankings = Object.values(agentStats)
      .map(agent => ({
        name: agent.name,
        avgScore: Math.round(agent.sum / agent.count),
        count: agent.count
      }))
      .sort((a, b) => b.avgScore - a.avgScore)
      .slice(0, 5); // top 5 agents

    return res.status(200).json({
      success: true,
      data: {
        totalAudits,
        passRate,
        avgScore,
        avgCC,
        avgBC,
        avgEC,
        avgNC,
        trends,
        agentRankings
      }
    });

  } catch (error) {
    return res.status(500).json({ success: false, error: error.message });
  }
});

// Global error handler
app.use((err, req, res, next) => {
  if (err instanceof multer.MulterError) {
    return res.status(400).json({ success: false, error: `Upload error: ${err.message}` });
  }
  if (err.message === "Only audio files are allowed!") {
    return res.status(400).json({ success: false, error: err.message });
  }
  return res.status(500).json({ success: false, error: err.message || "Internal server error" });
});

// Start the server
app.listen(PORT, () => {
  console.log(`QA Audit Application server running on port ${PORT}...`);
});
