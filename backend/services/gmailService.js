const nodemailer = require("nodemailer");

/**
 * Creates Nodemailer transporter from env config
 */
function getTransporter() {
  const user = process.env.GMAIL_USER;
  const pass = process.env.GMAIL_PASS;

  if (!user || !pass || user.includes("YOUR_GMAIL") || pass.includes("YOUR_GMAIL")) {
    console.warn("Gmail SMTP credentials are not configured. Emails will be logged to console instead.");
    return null; // Return null so we fall back to console logging instead of crashing
  }

  return nodemailer.createTransport({
    service: "gmail",
    auth: { user, pass }
  });
}

/**
 * Sends a beautiful HTML report to supervisors
 * @param {object} data The evaluation report data
 * @param {string} docUrl Link to the Google Doc
 */
async function sendSupervisorReport(data, docUrl) {
  const transporter = getTransporter();
  const recipients = process.env.SUPERVISOR_EMAILS || "supervisor@company.com";
  const subject = `[QA Alert] تقرير تقييم مكالمة - ${data.Agent_Name} | ${data.Pass_Fail}`;

  const passColor = data.Pass_Fail === "Pass" ? "#10b981" : "#ef4444";

  const htmlMessage = `
<div style="font-family: Arial, sans-serif; direction: rtl; text-align: right; border: 1px solid #e2e8f0; padding: 25px; border-radius: 12px; max-width: 650px; margin: 0 auto; background-color: #ffffff; color: #1e293b;">
  <h2 style="color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 12px; margin-top: 0;">🚨 تقرير تقييم مكالمة جديد</h2>

  <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
    <tr>
      <td style="padding: 8px; font-weight: bold; width: 35%; border-bottom: 1px solid #f1f5f9;">👤 اسم الموظف:</td>
      <td style="padding: 8px; border-bottom: 1px solid #f1f5f9;">${data.Agent_Name}</td>
    </tr>
    <tr style="background-color: #f8fafc;">
      <td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #f1f5f9;">📞 رقم المكالمة:</td>
      <td style="padding: 8px; border-bottom: 1px solid #f1f5f9;">${data.Call_ID}</td>
    </tr>
    <tr>
      <td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #f1f5f9;">🕐 التاريخ والوقت:</td>
      <td style="padding: 8px; border-bottom: 1px solid #f1f5f9;">${data.Call_Timestamp}</td>
    </tr>
    <tr style="background-color: #f8fafc;">
      <td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #f1f5f9;">📊 الدرجة الكلية:</td>
      <td style="padding: 8px; font-weight: bold; font-size: 16px; border-bottom: 1px solid #f1f5f9;">${data.Total_Score}</td>
    </tr>
    <tr>
      <td style="padding: 8px; font-weight: bold; border-bottom: 1px solid #f1f5f9;">✅ النتيجة:</td>
      <td style="padding: 8px; border-bottom: 1px solid #f1f5f9;">
        <span style="color: ${passColor}; font-weight: bold; font-size: 16px;">
          ${data.Pass_Fail === "Pass" ? "ناجح (Pass)" : "راسب (Fail)"}
        </span>
      </td>
    </tr>
  </table>

  <h3 style="color: #475569; margin-bottom: 10px;">📊 تفاصيل درجات المعايير</h3>
  <table style="width: 100%; border-collapse: collapse; margin: 15px 0; text-align: center;">
    <thead>
      <tr style="background-color: #1a73e8; color: white;">
        <th style="border: 1px solid #dddddd; padding: 12px; font-size: 14px;">الاتصال بالعميل (CC)</th>
        <th style="border: 1px solid #dddddd; padding: 12px; font-size: 14px;">الالتزام بالسياسات (BC)</th>
        <th style="border: 1px solid #dddddd; padding: 12px; font-size: 14px;">وضوح التنفيذ (EC)</th>
        <th style="border: 1px solid #dddddd; padding: 12px; font-size: 14px;">الخطوات القادمة (NC)</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td style="border: 1px solid #dddddd; padding: 12px; font-size: 18px; font-weight: bold; color: #1e293b;">${data.CC}</td>
        <td style="border: 1px solid #dddddd; padding: 12px; font-size: 18px; font-weight: bold; color: #1e293b;">${data.BC}</td>
        <td style="border: 1px solid #dddddd; padding: 12px; font-size: 18px; font-weight: bold; color: #1e293b;">${data.EC}</td>
        <td style="border: 1px solid #dddddd; padding: 12px; font-size: 18px; font-weight: bold; color: #1e293b;">${data.NC}</td>
      </tr>
    </tbody>
  </table>

  <p style="margin-top: 20px; margin-bottom: 5px;"><b>⚠️ الأخطاء المكتشفة:</b></p>
  <div style="background-color: #fff5f5; padding: 15px; border-right: 5px solid #ef4444; border-radius: 4px; margin-bottom: 20px; font-size: 14px; line-height: 1.5;">
    ${data.Errors || "لا يوجد أخطاء مرصودة."}
  </div>

  <p style="margin-top: 10px; margin-bottom: 5px;"><b>💡 التقييم والتوجيه الذكي (AI Feedback):</b></p>
  <div style="background-color: #f0f7ff; padding: 15px; border-right: 5px solid #1a73e8; border-radius: 4px; margin-bottom: 25px; font-size: 14px; line-height: 1.6; white-space: pre-line;">
    ${data.AI_Feedback}
  </div>

  <div style="margin-top: 30px; padding: 20px; background-color: #f8fafc; border-radius: 8px; text-align: center; border: 1px solid #e2e8f0;">
    <p style="margin-top: 0; font-weight: bold; color: #475569;">📄 التقرير المفصل مستندات (Google Docs):</p>
    <a href="${docUrl}" target="_blank" style="display: inline-block; background-color: #1a73e8; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 14px; box-shadow: 0 2px 4px rgba(26,115,232,0.2);">اضغط هنا لفتح التقرير كاملاً</a>
  </div>

  <p style="color: #94a3b8; font-size: 12px; text-align: center; margin-top: 25px; border-top: 1px solid #f1f5f9; padding-top: 15px;">تم الإرسال تلقائياً بواسطة نظام QA Dashboard</p>
</div>
  `;

  if (!transporter) {
    console.log("=== SIMULATED EMAIL TO SUPERVISOR ===");
    console.log(`To: ${recipients}`);
    console.log(`Subject: ${subject}`);
    console.log(`Link: ${docUrl}`);
    return;
  }

  console.log(`Sending supervisor report email to: ${recipients}...`);
  await transporter.sendMail({
    from: `"QA Dashboard" <${process.env.GMAIL_USER}>`,
    to: recipients,
    subject: subject,
    html: htmlMessage
  });
  console.log("Supervisor report email sent successfully.");
}

/**
 * Sends a technical alert to the dev team in case of analysis failure
 * @param {object} metadata Call metadata info
 * @param {string} errorDetails Details of the error
 */
async function sendTechAlert(metadata, errorDetails) {
  const transporter = getTransporter();
  const recipient = process.env.TECH_EMAIL || "tech-team@company.com";
  const subject = `⚠️ [QA System Error] فشل تحليل مكالمة - ${metadata.call_id}`;

  const htmlMessage = `
<div style="font-family: Arial, sans-serif; direction: rtl; text-align: right; border: 1px solid #fee2e2; padding: 20px; border-radius: 8px; max-width: 600px; margin: 0 auto; background-color: #fffef2;">
  <h2 style="color: #dc2626; border-bottom: 2px solid #dc2626; padding-bottom: 10px; margin-top: 0;">⚠️ فشل تحليل مكالمة تلقائياً</h2>
  <p>حدث خطأ أثناء معالجة أو تحليل المكالمة التالية، يرجى المراجعة الفنية واليدوية للمكالمة:</p>
  <ul style="padding-right: 20px; line-height: 1.6;">
    <li><b>اسم الموظف:</b> ${metadata.agent_name || "Unknown"}</li>
    <li><b>رقم المكالمة:</b> ${metadata.call_id}</li>
    <li><b>التاريخ:</b> ${metadata.formatted_date}</li>
    <li><b>تفاصيل الخطأ الفني:</b> <span style="color: #dc2626; font-family: monospace;">${errorDetails}</span></li>
  </ul>
</div>
  `;

  if (!transporter) {
    console.log("=== SIMULATED EMAIL TO TECH TEAM ===");
    console.log(`To: ${recipient}`);
    console.log(`Subject: ${subject}`);
    console.log(`Error: ${errorDetails}`);
    return;
  }

  console.log(`Sending technical alert email to: ${recipient}...`);
  await transporter.sendMail({
    from: `"QA System Alert" <${process.env.GMAIL_USER}>`,
    to: recipient,
    subject: subject,
    html: htmlMessage
  });
  console.log("Technical alert email sent successfully.");
}

module.exports = {
  sendSupervisorReport,
  sendTechAlert
};
