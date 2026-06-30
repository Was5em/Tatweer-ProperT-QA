import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from schemas import GeminiAuditResult
import pathlib
import time

# Load environment variables
load_dotenv(override=True)

# Configure Gemini SDK
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

def compress_audio(file_path: str) -> str:
    """
    Downsamples audio to mono 16kHz 64kbps MP3 to reduce bandwidth.
    Falls back to original file if pydub/ffmpeg is not available.
    """
    try:
        from pydub import AudioSegment
        print(f"Attempting audio compression for {file_path}...")
        audio = AudioSegment.from_file(file_path)
        audio = audio.set_channels(1).set_frame_rate(16000)
        
        root, ext = os.path.splitext(file_path)
        compressed_path = f"{root}_compressed.mp3"
        audio.export(compressed_path, format="mp3", bitrate="64k")
        print(f"Audio compressed successfully: {compressed_path}")
        return compressed_path
    except Exception as e:
        print(f"Audio compression bypassed: {e}. (Ensure ffmpeg and pydub are installed). Using original file.")
        return file_path

def analyze_audio(file_path: str, display_name: str) -> dict:
    """
    Uploads audio file to Gemini via Files API, executes evaluation prompt, 
    calculates scores programmatically in Python, and cleans up remote file.
    """
    current_api_key = os.environ.get("GEMINI_API_KEY")
    if not current_api_key:
        raise ValueError("GEMINI_API_KEY is not configured in the backend environment.")
    
    genai.configure(api_key=current_api_key)

    # 1. Compress audio if possible
    processed_path = compress_audio(file_path)

    audio_file = None
    try:
        # 2. Upload to Google Files API
        print(f"Uploading file to Gemini Files API: {processed_path}...")
        audio_file = genai.upload_file(path=processed_path, display_name=display_name)
        print(f"Uploaded remote file name: {audio_file.name}, waiting for active state...")

        # 3. Wait for file to process
        start_time = time.time()
        while audio_file.state.name == "PROCESSING":
            if time.time() - start_time > 180:
                raise TimeoutError("Gemini file processing timed out on Google servers.")
            time.sleep(5)
            audio_file = genai.get_file(audio_file.name)

        if audio_file.state.name == "FAILED":
            raise RuntimeError("Gemini file processing failed on Google servers.")

        # 4. Prompt definition - instructing strict English feedback
        prompt = """
You are a Call Center Quality Assurance Auditor (QA Analyst). Your task is to listen to the attached call recording audio and evaluate the agent's performance strictly based on the following quality scorecard criteria and codes (NC: Normal Error, BC: Business Compliance Error, EC: Critical/Extreme Error).

All feedback, coaching summaries, and descriptions MUST be written in English. Do not write any Arabic in the final JSON response.

Scorecard Criteria:
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

Output the JSON response strictly formatted to match the required schema. Write the coaching summary in 'coaching_summary' in English.
"""

        # 5. Execute generation
        # We read model from environment if specified, else fall back to gemini-1.5-flash
        model_name = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
        print(f"Analyzing audio using model {model_name}...")
        model = genai.GenerativeModel(model_name)
        
        response = model.generate_content(
            [audio_file, prompt],
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=GeminiAuditResult
            )
        )
        
        result_json = json.loads(response.text)
        
        # 6. Programmatic score calculations to ensure mathematical correctness
        cc_score = 100
        bc_score = 100
        ec_score = 100
        nc_score = 100
        
        nc_count = 0
        bc_count = 0
        ec_count = 0
        
        for item in result_json.get("detailed_scoring", []):
            if item.get("pass_fail", "").lower() == "fail":
                desc = item.get("description", "").lower()
                cat = item.get("category", "").lower()
                
                # Check for EC
                if "(ec)" in desc or "(ec)" in cat or "disconnect" in desc or "rude" in desc or "refused escalation" in desc:
                    ec_count += 1
                    ec_score = 0
                # Check for BC
                elif "(bc)" in desc or "(bc)" in cat or "script" in desc or "verification" in desc or "process consistency" in desc or "didn't handle before" in desc or "no data" in desc:
                    bc_count += 1
                    bc_score = max(0, bc_score - 10)
                # Check for NC (Normal Error)
                else:
                    nc_count += 1
                    # Distinguish between Next Steps (NC) and Customer Connection (CC)
                    if "greeting" in desc or "closing" in desc or "greeting" in cat or "closing" in cat or "call control" in desc or "call control" in cat or "hold" in desc or "mute" in desc or "transfer" in desc:
                        nc_score = max(0, nc_score - 10)
                    else:
                        cc_score = max(0, cc_score - 10)

        # Override computed values in JSON return object
        result_json["NC"] = nc_count
        result_json["BC"] = bc_count
        result_json["EC"] = ec_count
        result_json["cc_score"] = cc_score
        result_json["bc_score"] = bc_score
        result_json["ec_score"] = ec_score
        result_json["nc_score"] = nc_score
        
        avg_score = round((cc_score + bc_score + ec_score + nc_score) / 4)
        result_json["status"] = "Fail" if (ec_score == 0 or avg_score < 70) else "Pass"
        
        return result_json
        
    finally:
        # Clean up files
        if audio_file:
            try:
                print(f"Cleaning up remote file from Gemini servers: {audio_file.name}...")
                genai.delete_file(audio_file.name)
                print("Remote file deleted successfully.")
            except Exception as cleanup_err:
                print(f"Failed to delete remote file: {cleanup_err}")
        
        if processed_path != file_path and os.path.exists(processed_path):
            try:
                os.remove(processed_path)
            except OSError:
                pass
