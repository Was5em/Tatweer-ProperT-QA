const { google } = require("googleapis");
const fs = require("fs");
const path = require("path");

const credentialsPath = path.join(__dirname, "..", process.env.GOOGLE_APPLICATION_CREDENTIALS || "google-credentials.json");

let docsClient = null;
let driveClient = null;

function getClients() {
  if (docsClient && driveClient) return { docsClient, driveClient };

  if (!fs.existsSync(credentialsPath)) {
    throw new Error(`Google credentials file not found at: ${credentialsPath}. Please place your service account credentials file there.`);
  }

  const auth = new google.auth.GoogleAuth({
    keyFile: credentialsPath,
    scopes: [
      "https://www.googleapis.com/auth/documents",
      "https://www.googleapis.com/auth/drive"
    ]
  });

  docsClient = google.docs({ version: "v1", auth });
  driveClient = google.drive({ version: "v3", auth });
  return { docsClient, driveClient };
}

/**
 * Creates a Google Doc, writes evaluation report text, and moves it to the target folder
 * @param {object} data Evaluation report data
 * @returns {Promise<string>} Document edit URL
 */
async function createDocReport(data) {
  const { docsClient, driveClient } = getClients();

  const title = `QA Report - ${data.Agent_Name} - ${data.Call_ID}`;
  console.log(`Creating Google Document: "${title}"...`);

  // 1. Create document
  const doc = await docsClient.documents.create({
    requestBody: { title }
  });
  const documentId = doc.data.documentId;
  console.log(`Document created with ID: ${documentId}`);

  // 2. Prepare the report text in Arabic
  const reportText = `تقرير تقييم جودة المكالمة (QA Audit Report)
==============================================

👤 اسم الموظف: ${data.Agent_Name}
📞 رقم المكالمة: ${data.Call_ID}
📅 تاريخ التقييم: ${data.Call_Timestamp}

----------------------------------------------
📊 النتيجة الإجمالية: ${data.Pass_Fail}
📈 الدرجة الكلية: ${data.Total_Score}
----------------------------------------------

تفاصيل درجات المعايير (Scores):
- درجة الاتصال بالعميل (CC): ${data.CC}/100
- درجة الالتزام بالسياسات (BC): ${data.BC}/100
- درجة وضوح التنفيذ (EC): ${data.EC}/100
- درجة الخطوات القادمة (NC): ${data.NC}/100

⚠️ الأخطاء المرصودة (Errors):
${data.Errors || "لا يوجد أخطاء"}

💡 التقييم والتوجيه الذكي (AI Feedback):
${data.AI_Feedback || "لا يوجد توجيهات إضافية"}

----------------------------------------------
تم إنشاء هذا التقرير تلقائياً بواسطة نظام QA Dashboard.
`;

  // 3. Write text into document
  console.log("Writing report contents into document...");
  await docsClient.documents.batchUpdate({
    documentId,
    requestBody: {
      requests: [
        {
          insertText: {
            location: { index: 1 },
            text: reportText
          }
        }
      ]
    }
  });

  // 4. Move document to target Google Drive folder if configured and not 'root'
  const folderId = process.env.GOOGLE_DRIVE_FOLDER_ID;
  if (folderId && folderId !== "root") {
    try {
      console.log(`Moving document ${documentId} to folder: ${folderId}...`);
      // Get current parents
      const file = await driveClient.files.get({
        fileId: documentId,
        fields: "parents"
      });
      const previousParents = file.data.parents ? file.data.parents.join(",") : "";

      // Move the file to the new folder
      await driveClient.files.update({
        fileId: documentId,
        addParents: folderId,
        removeParents: previousParents,
        fields: "id, parents"
      });
      console.log("Document moved to target folder successfully.");
    } catch (moveError) {
      console.error("Failed to move document to folder:", moveError.message);
      // Don't fail the whole process if only moving to folder fails
    }
  }

  // 5. Make the file readable by anyone with the link + explicitly share with supervisors
  try {
    console.log("Sharing document: making it readable to anyone with link...");
    await driveClient.permissions.create({
      fileId: documentId,
      requestBody: {
        role: "reader",
        type: "anyone"
      }
    });
    console.log("Document permission updated to 'anyone with link can view'.");
  } catch (shareError) {
    console.log(`Note: 'Anyone' sharing restricted by domain policy: ${shareError.message}. Proceeding with explicit sharing.`);
  }

  // Explicitly share with GMAIL_USER and SUPERVISOR_EMAILS to bypass domain policies
  try {
    const supervisorEmails = (process.env.SUPERVISOR_EMAILS || "").split(",");
    const userEmail = process.env.GMAIL_USER;
    const emailsToShare = [...supervisorEmails, userEmail]
      .map(e => e.trim())
      .filter(Boolean);

    for (const email of emailsToShare) {
      if (email.includes("@") && !email.includes("company.com")) {
        console.log(`Sharing document explicitly with user: ${email}`);
        await driveClient.permissions.create({
          fileId: documentId,
          sendNotificationEmail: false, // Don't spam them with google drive emails
          requestBody: {
            role: "reader",
            type: "user",
            emailAddress: email
          }
        });
      }
    }
    console.log("Explicit user permissions added successfully.");
  } catch (explicitError) {
    console.error("Failed to explicitly share document with users:", explicitError.message);
  }

  return `https://docs.google.com/document/d/${documentId}/edit`;
}

module.exports = {
  createDocReport
};
