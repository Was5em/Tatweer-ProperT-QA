const { google } = require("googleapis");
const fs = require("fs");
const path = require("path");

const credentialsPath = path.join(__dirname, "..", process.env.GOOGLE_APPLICATION_CREDENTIALS || "google-credentials.json");

let sheetsClient = null;

function getSheetsClient() {
  if (sheetsClient) return sheetsClient;

  if (!fs.existsSync(credentialsPath)) {
    throw new Error(`Google credentials file not found at: ${credentialsPath}. Please place your service account credentials file there.`);
  }

  const auth = new google.auth.GoogleAuth({
    keyFile: credentialsPath,
    scopes: [
      "https://www.googleapis.com/auth/spreadsheets",
      "https://www.googleapis.com/auth/drive.file"
    ]
  });

  sheetsClient = google.sheets({ version: "v4", auth });
  return sheetsClient;
}

function sanitize(val) {
  if (typeof val !== "string") return val;
  const trimmed = val.trim();
  // Prevent Formula Injection by prepending single quote
  if (/^[=+\-@]/.test(trimmed)) return "'" + trimmed;
  return trimmed;
}

/**
 * Appends a new evaluation row to Google Sheet
 * @param {object} data The evaluation result data
 */
async function appendToSheet(data) {
  const spreadsheetId = process.env.GOOGLE_SHEET_ID;
  if (!spreadsheetId) {
    throw new Error("GOOGLE_SHEET_ID is not configured in backend/.env.");
  }

  const client = getSheetsClient();

  const values = [
    [
      sanitize(data.Call_ID),
      sanitize(data.Agent_Name),
      data.Call_Timestamp,
      data.Pass_Fail,
      data.Total_Score,
      data.CC,
      data.BC,
      data.EC,
      data.NC,
      sanitize(data.Errors),
      sanitize(data.AI_Feedback)
    ]
  ];

  console.log(`Appending evaluation row to sheet ID: ${spreadsheetId}...`);
  await client.spreadsheets.values.append({
    spreadsheetId,
    range: "A:K", // Appends to the sheet (expects Call_ID in A, Agent_Name in B, etc.)
    valueInputOption: "USER_ENTERED",
    insertDataOption: "INSERT_ROWS",
    resource: { values }
  });
  console.log("Evaluation row appended to Google Sheet successfully.");
}

/**
 * Fetches all audited calls from the Google Sheet
 * @returns {Promise<Array>} List of audited call objects
 */
async function readHistoryFromSheet() {
  const spreadsheetId = process.env.GOOGLE_SHEET_ID;
  if (!spreadsheetId) {
    throw new Error("GOOGLE_SHEET_ID is not configured in backend/.env.");
  }

  try {
    const client = getSheetsClient();
    console.log(`Fetching history from sheet ID: ${spreadsheetId}...`);
    
    // Fetch all data in columns A to K (excluding the header row at index 0)
    const response = await client.spreadsheets.values.get({
      spreadsheetId,
      range: "A2:K" // Fetch all rows dynamically from the first sheet
    });

    const rows = response.data.values || [];
    console.log(`Fetched ${rows.length} rows from Google Sheets.`);

    // Map rows to objects
    return rows.map((row, index) => ({
      id: index + 2, // Keep sheet row index for reference
      Call_ID: row[0] || "",
      Agent_Name: row[1] || "Unknown Agent",
      Call_Timestamp: row[2] || "",
      Pass_Fail: row[3] || "N/A",
      Total_Score: row[4] || "0%",
      CC: Number(row[5]) || 0,
      BC: Number(row[6]) || 0,
      EC: Number(row[7]) || 0,
      NC: Number(row[8]) || 0,
      Errors: row[9] || "لا يوجد",
      AI_Feedback: row[10] || ""
    })).reverse(); // Return newest first

  } catch (error) {
    console.error("Error reading history from Google Sheet:", error.message);
    // Return empty list if sheet is not initialized or accessible yet
    return [];
  }
}

module.exports = {
  appendToSheet,
  readHistoryFromSheet
};
