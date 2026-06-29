import os
import json
import google.generativeai as genai
from schemas import GeminiAuditResult

# Configure Gemini SDK
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

def analyze_audio(file_path: str, display_name: str) -> dict:
    """
    Uploads audio file to Gemini, executes evaluation prompt with structured response schema, 
    and deletes the file from Gemini servers when done.
    """
    current_api_key = os.environ.get("GEMINI_API_KEY")
    if not current_api_key:
        raise ValueError("GEMINI_API_KEY is not configured in the backend environment.")
    
    genai.configure(api_key=current_api_key)

    print(f"Uploading file {file_path} to Gemini File Manager...")
    audio_file = genai.upload_file(path=file_path, display_name=display_name)
    print(f"File uploaded successfully. URI: {audio_file.uri}")

    prompt = """
You are a Call Center Quality Assurance Auditor (QA Analyst). Your task is to listen to the attached call recording audio and evaluate the agent's performance strictly based on the following quality scorecard criteria and codes (NC: Normal Error, BC: Business Compliance Error, EC: Critical/Extreme Error):

1. Professionalism & Etiquette:
- Addressing Customer (NC - Affects CC score):
  * Didn't Welcome the customer
  * Didn't address customer by his name/title
  * Addressed customer by wrong name
  * Addressed customer with direct speech
  * Using Wrong Gender Type
- Avoiding & Disconnecting call (EC - Critical Violation, affects EC score):
  * Disconnected the call
  * Hold/Mute/Transfer violation
  * No transfer/wrong transfer
  * Didn't wait for proper time before ending call
  * No response and customer closed the call
- Call Control (NC/BC/EC - Affects corresponding score):
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
- Greeting & Closing (NC/BC - Affects corresponding score):
  * Delay in responding (NC)
  * Inaccurate greeting time (NC)
  * No greeting/closing at all (NC)
  * Wrong greeting/closing structure (NC)
  * Didn't offer extra assistance (NC)
  * Improper greeting/closing tone (NC)
  * Delay in responding (BC)
- Tone Of Voice (NC - Affects CC score):
  * Scripted/Monotony/sleepy/bored/cold/unwelcome/unfriendly tone
  * Very fast/unclear
  * Not confident/hesitant
  * Sharp voice tone
  * Unfriendly tone

2. Soft Skills & Behavior:
- Empathic Listening (NC - Affects CC score):
  * Interrupting the customer
  * Didn't reflect with the customer
  * Not Empathic
  * Didn't apologize to customer
  * Assumption
  * Not focused/Let customer repeat the information
- Professionalism & courtesy (NC - Affects CC score):
  * Used repetitive word
  * Used language not matched with the customer
  * Used unprofessional/negative expressions
  * Didn't avoid mouth noise
  * Raising Headset/ Whispering
- Rude/Unacceptable Behavior (EC - Critical Violation, affects EC score):
  * Rude behavior/Blaming & Provoking customer
  * Showing carelessness to cancelation requests
- SPV Escalation Process (BC/EC - Affects corresponding score):
  * Didn't handle before escalation (BC)
  * Refused escalation to SPV (EC)

3. Standard Verification (Affects BC score):
  * Didn't ask about required data (e.g. name, account, verification info)
  * Didn't verify/confirm/validate data
  * Didn't collect customer data

4. Business Requirement & process:
- Script compliance (BC - Affects BC score):
  * Didn't describe Script/info
  * Incomplete Script/info
  * Didn't follow process consistency

Calculate 4 scores (from 0 to 100):
1. CC (Customer Connection): Starts at 100. Deduct 10 points for each NC infraction committed under Addressing Customer, Tone of Voice, Empathic Listening, and Professionalism/Courtesy.
2. BC (Business Compliance): Starts at 100. Deduct 10 points for each BC infraction committed under Greeting/Closing, SPV Escalation, Verification, and Script Compliance.
3. EC (Execution Clarity): Starts at 100. Deduct 100 points (immediate 0) if any EC infraction under Avoiding Call, Call Control, Rude Behavior, or SPV Escalation is committed.
4. NC (Next Steps): Starts at 100. Deduct 10 points for each NC infraction committed under Greeting/Closing and Call Control.

Evaluation Rules:
- If ANY Critical Error (EC) is committed, the status is automatically "Fail".
- Otherwise, the status is "Pass" if the average of CC, BC, EC, NC scores is 70 or above.

Output the JSON response strictly formatted to match the required schemas. Highlight any errors committed in 'Errors' in Arabic. Write the coaching summary in 'AI_Feedback' (coaching_summary) in Arabic.
"""

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        print("Analyzing audio using Gemini 2.5 Flash...")
        response = model.generate_content(
            [audio_file, prompt],
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=GeminiAuditResult
            )
        )
        
        # Parse output JSON string
        result_json = json.loads(response.text)
        return result_json

    finally:
        # Guarantee cleanup of remote file
        try:
            print(f"Deleting remote file {audio_file.name} from Gemini File Manager...")
            genai.delete_file(name=audio_file.name)
            print("Remote file deleted successfully.")
        except Exception as cleanup_error:
            print(f"Failed to delete remote file from Gemini File Manager: {cleanup_error}")
