const { GoogleGenerativeAI } = require("@google/generative-ai");
const { GoogleAIFileManager } = require("@google/generative-ai/server");

// Initialize Gemini SDKs
let genAI;
let fileManager;

if (process.env.GEMINI_API_KEY) {
  genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
  fileManager = new GoogleAIFileManager(process.env.GEMINI_API_KEY);
}

/**
 * Analyzes call audio file using Google Gemini 2.5 Flash
 * @param {string} filePath Local path to the audio file
 * @param {string} mimeType Mime-type of the audio file (e.g. audio/mp3, audio/wav)
 * @returns {Promise<object>} Parsed evaluation JSON
 */
async function analyzeAudio(filePath, mimeType) {
  if (!process.env.GEMINI_API_KEY || process.env.GEMINI_API_KEY.includes("YOUR_GEMINI_API_KEY")) {
    throw new Error("Gemini API key is not configured. Please set GEMINI_API_KEY in the backend/.env file.");
  }

  let uploadResult;
  try {
    console.log(`Uploading file ${filePath} to Gemini File Manager...`);
    uploadResult = await fileManager.uploadFile(filePath, {
      mimeType: mimeType,
      displayName: `Call_Audio_${Date.now()}`
    });
    console.log(`File uploaded successfully. URI: ${uploadResult.file.uri}`);

    const prompt = `
أنت خبير تقييم جودة مكالمات خدمة العملاء (QA Analyst). مهمتك هي الاستماع للمكالمة الصوتية المرفقة وتقييم أداء الموظف بدقة وبناءً على مصفوفة تدقيق جودة المكالمات الرسمية التالية:

1. Professionalism & Etiquette (الاحترافية واللباقة):
- Addressing Customer (مخالفات مناداة العميل - تؤثر على درجة CC):
  * Didn't Welcome the customer (NC)
  * Didn't address customer by his name/title (NC)
  * Addressed customer by wrong name (NC)
  * Addressed customer with direct speech (NC)
  * Using Wrong Gender Type (NC)
- Avoiding & Disconnecting call (مخالفات تجنب وتفادي المكالمات - تؤثر على درجة EC):
  * Disconnected the call (EC)
  * Hold/Mute/Transfer violation (EC)
  * No transfer/wrong transfer (EC)
  * Didn't wait for proper time before ending call (EC)
  * No response and customer closed the call (EC)
- Call Control (مخالفات التحكم في المكالمة - تؤثر على الدرجات المقابلة):
  * Delay in closing the call (BC)
  * Ineffective questions/Info (NC)
  * Didn't follow Transfer/Mute/Dead Air/Hold protocol (NC)
  * Exceeding hold time (NC)
  * Hold Trials (NC)
  * Didn't Collect the Data in Smart way (NC)
  * Didn't keep the conversation on track (NC)
  * Unable to explain (NC)
  * Ineffective verification (NC)
  * Exceeding hold time/Trials (EC)
  * Ineffective verification (EC)
- Greeting & Closing (الترحيب والإنهاء - تؤثر على الدرجات المقابلة):
  * Delay in responding (NC)
  * Inaccurate greeting time (NC)
  * No greeting/closing at all (NC)
  * Wrong greeting/closing structure (NC)
  * Didn't offer extra assistance (NC)
  * Improper greeting/closing tone (NC)
  * Delay in responding (BC)
- Tone Of Voice (نبرة الصوت - تؤثر على درجة CC):
  * Scripted/Monotony/sleepy/bored/cold/unwelcome/unfriendly tone (NC)
  * Very fast/unclear (NC)
  * Not confident/hesitant (NC)
  * Sharp voice tone (NC)
  * Unfriendly tone (NC)

2. Soft Skills & Behavior (المهارات الناعمة والسلوك):
- Empathic Listening (الاستماع والتعاطف - تؤثر على درجة CC):
  * Interrupting the customer (NC)
  * Didn't reflect with the customer (NC)
  * Not Empathic (NC)
  * Didn't apologize to customer (NC)
  * Assumption (NC)
  * Not focused/Let customer repeat the information (NC)
- Professionalism & courtesy (اللباقة والاحترافية - تؤثر على درجة CC):
  * Used repetitive word (NC)
  * Used language not matched with the customer (NC)
  * Used unprofessional/negative expressions (NC)
  * Didn't avoid mouth noise (NC)
  * Raising Headset/ Whispering (NC)
- Rude/Unacceptable Behavior (السلوك غير المقبول - تؤثر على درجة EC):
  * Rude behavior/Blaming & Provoking customer (EC)
  * Showing carelessness to cancelation requests (EC)
- SPV Escalation Process (عملية تصعيد المشرفين):
  * Didn't handle before escalation (BC)
  * Refused escalation to SPV (EC)

3. Standard Verification (التحقق والتوثيق - تؤثر على درجة BC):
  * Didn't ask about required data (مثال: عدم التحقق من الاسم أو رقم الحساب)
  * Didn't verify/confirm/validate data
  * Didn't collect customer data

4. Business Requirement & process (متطلبات العمل والعمليات):
- Script compliance (الالتزام بنص السيناريو - تؤثر على درجة BC):
  * Didn't describe Script/info (BC)
  * Incomplete Script/info (BC)
  * Didn't follow process consistency (BC)

قم باحتساب الدرجات الأربعة (من 0 إلى 100):
1. CC (Customer Connection): تعتمد على الترحيب ونبرة الصوت والتعاطف والاحترافية واللباقة. اخصم من درجة CC بناءً على مخالفات NC المرتكبة في هذه الأقسام.
2. BC (Business Compliance): تعتمد على التحقق والتوثيق والالتزام بالسيناريو ومستندات العمل. اخصم من درجة BC بناءً على مخالفات BC المرتكبة.
3. EC (Execution Clarity): تعتمد على وضوح الحل وعدم تجنب المكالمة أو ارتكاب سلوك غير مقبول. اخصم من درجة EC المرتكبة.
4. NC (Next Steps): تعتمد على خطوات إنهاء المكالمة وعرض المساعدة الإضافية وخطوات المتابعة. اخصم من درجة NC بناءً على مخالفات الترحيب والإنهاء ومخالفات التحكم.

معايير النجاح والرسوب (Pass/Fail):
- يعتبر الموظف ناجحاً (Pass) إذا كان متوسط الدرجات الأربعة لا يقل عن 70%، ولم يتم ارتكاب أي مخالفة من نوع (EC) (حيث أي مخالفة EC تؤدي فوراً لرسوب الموظف وتصفير المعيار المقابل، أو خفض التقييم لـ Fail).
- يعتبر الموظف راسباً (Fail) إذا كان المتوسط أقل من 70% أو ارتكب أي مخالفة جسيمة من نوع (EC).

يجب كتابة أسباب الخصم والمخالفات المرتكبة بالتفصيل باللغة العربية في حقل "Errors".
يجب كتابة توجيهات مفصلة للموظف باللغة العربية لتحسين نبرته وأدائه في حقل "AI_Feedback".
`;

    console.log("Analyzing audio using Gemini 2.5 Flash...");
    const model = genAI.getGenerativeModel({
      model: "gemini-2.5-flash",
      generationConfig: {
        responseMimeType: "application/json",
        responseSchema: {
          type: "object",
          properties: {
            Pass_Fail: {
              type: "string",
              enum: ["Pass", "Fail"]
            },
            Scores: {
              type: "object",
              properties: {
                CC: { type: "integer" },
                BC: { type: "integer" },
                EC: { type: "integer" },
                NC: { type: "integer" }
              },
              required: ["CC", "BC", "EC", "NC"]
            },
            Errors: {
              type: "array",
              items: { type: "string" }
            },
            AI_Feedback: { type: "string" }
          },
          required: ["Pass_Fail", "Scores", "Errors", "AI_Feedback"]
        }
      }
    });

    const response = await model.generateContent([
      {
        fileData: {
          fileUri: uploadResult.file.uri,
          mimeType: uploadResult.file.mimeType
        }
      },
      prompt
    ]);

    let responseText = response.response.text();
    console.log("Raw response received from Gemini.");

    // Clean up markdown markers if Gemini returned them despite prompt instructions
    responseText = responseText
      .replace(/```json/gi, '')
      .replace(/```/g, '')
      .trim();

    const parsedData = JSON.parse(responseText);
    return parsedData;

  } catch (error) {
    console.error("Error during Gemini analysis:", error);
    throw error;
  } finally {
    // Always clean up the uploaded file from the Gemini server
    if (uploadResult && uploadResult.file) {
      try {
        console.log(`Deleting remote file ${uploadResult.file.name} from Gemini File Manager...`);
        await fileManager.deleteFile(uploadResult.file.name);
        console.log("Remote file deleted successfully.");
      } catch (cleanupError) {
        console.error("Failed to delete remote file from Gemini File Manager:", cleanupError);
      }
    }
  }
}

module.exports = {
  analyzeAudio
};
