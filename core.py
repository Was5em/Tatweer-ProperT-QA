from google import genai
from google.genai import types
import json
import time
import os
import platform
from typing import Dict, Any
import typing_extensions as typing

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_ARABIC = True
except ImportError:
    HAS_ARABIC = False

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def register_unicode_font():
    local_font = "DejaVuSans.ttf"
    if os.path.exists(local_font):
        try:
            pdfmetrics.registerFont(TTFont("UnicodeFont", local_font))
            pdfmetrics.registerFont(TTFont("UnicodeFont-Bold", local_font))
            return "UnicodeFont"
        except Exception:
            pass

    if platform.system() == "Windows":
        paths = [
            ("C:\\Windows\\Fonts\\arial.ttf", "C:\\Windows\\Fonts\\arialbd.ttf"),
            ("C:\\Windows\\Fonts\\tahoma.ttf", "C:\\Windows\\Fonts\\tahomabd.ttf"),
        ]
        for p_normal, p_bold in paths:
            if os.path.exists(p_normal):
                try:
                    pdfmetrics.registerFont(TTFont("UnicodeFont", p_normal))
                    if os.path.exists(p_bold):
                        pdfmetrics.registerFont(TTFont("UnicodeFont-Bold", p_bold))
                    else:
                        pdfmetrics.registerFont(TTFont("UnicodeFont-Bold", p_normal))
                    return "UnicodeFont"
                except Exception:
                    pass

    return "Helvetica"

UNICODE_FONT = register_unicode_font()

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import Flowable
import io
from pydub import AudioSegment
from config import QAConfig
from database import DataManager, SessionLocal, AnalysisQueue


class SectionResult(typing.TypedDict):
    Result:       typing.Literal['Pass', 'Fail', 'N/A']
    Errors_Found: list[str]
    Evidence:     str

class PassFailSections(typing.TypedDict):
    Company_Image:                   SectionResult
    Data_System_Accuracy:            SectionResult
    Product_Knowledge_Process:       SectionResult
    Professionalism_Etiquette:       SectionResult
    Soft_Skills_Behavior:            SectionResult
    Standard_Verification:            SectionResult
    Business_Requirement_Process:    SectionResult
    Violation_of_Privacy_Policies:   SectionResult

SECTION_MAX: Dict[str, int] = {
    "Business_Critical":    25,
    "End_User_Critical":    25,
    "Compliance_Critical":  25,
    "Non_Critical":         25,
}

class QAResponseSchema(typing.TypedDict):
    Campaign:            typing.Literal['Tatweer Misr', 'Proper T']
    Call_Type:           str
    Customer_Name:       str
    Customer_Phone:      str
    Call_Date:           str
    FCR:                 typing.Literal['Yes', 'No', 'NA']
    FCR_Reason:          str
    Customer_Feedback:   typing.Literal['Positive', 'Negative', 'NA']
    Customer_Feedback_Comment: str
    Overall_Status:      typing.Literal['Pass', 'Fail']
    Auto_Fail_Triggered: typing.Literal['Yes', 'No']
    Auto_Fail_Reason:    str
    Root_Cause_Analysis: str
    Sections:            PassFailSections
    Strengths:           list[str]
    Coaching_Notes:      list[str]
    Final_Summary:       str

OFFICIAL_SCORECARD_PROMPT = """You are an Expert QA Auditor for Tatweer Misr and Proper T campaigns, reviewing call center audio recordings.
Your task is to audit the call based only on what is clearly heard in the recording or transcript.
Do not assume anything that was not said. You must evaluate the call using an Error-Based Deductive model.
The goal is to determine the correct campaign, the call type, check for FCR (First Call Resolution), customer feedback, and list any specific errors committed by the agent.

## Campaign & Call Type Identification Rules:
- Identify if the call belongs to the **Tatweer Misr** campaign or the **Proper T** campaign:
  - **Tatweer Misr**: Related to real estate inquiries, sales, resales, handovers, community issues, collections, general complaints, or customer relations.
  - **Proper T**: Related to facility management and maintenance requests (plumbing, electrical work, carpentry, air conditioning, civil work, housekeeping, pest control, pool service).
- Identify the specific **Call Type** matching the conversation.
  - Allowed Tatweer Misr call types: Sales, Resale, Client Relation, Technical client Relation, Collection and Credit Control, Handover, Community, General Inquiry, General Complaint.
  - Allowed Proper T call types: Plumbing Work, Electric Work, Carpentry Work, Aluminum Works, Air Conditioning Work, Civil Works, Housekeeping Service, Houskeeping Process, Pest Control Services, Private pools Services.

## Core Evaluation Sections:
You must audit the call against the following 8 sections. For each section, you must return a list of specific error reasons committed by the agent. Choose ONLY from the exact list provided under each section below. If no errors occurred in a section, return an empty list.

1. **Company_Image**:
   Error checklist (choose only from these):
   - `Using Wrong Company name (BC)` (e.g. greeting Tatweer Misr instead of Proper T or vice versa, or mentioning a wrong project)
   - `Didn't maintain a positive Company image (BC)` (e.g. speaking badly about the company)
   - `Didn't adhere to Company policies (BC)`
   - `Used poor language with foreigners (BC)`
   - `Talking with others during call (BC)`

2. **Data_System_Accuracy**:
   Error checklist (choose only from these):
   - `Didn't Correct data when required (EC)`
   - `Didn't Log or Update Complaint (EC)`
   - `Enter wrong data reservation (EC)`
   - `No Data/Enter wrong data (BC)`
   - `Didn't correct data when required (BC)`
   - `Didn't log call activity (BC)`
   - `Delay activity log (BC)`
   - `Wrong call activity tree/type (BC)`
   - `Missing/Wrong activity description (BC)`
   - `Didn't close the call activity (BC)`
   - `System Useless Usage (BC)`
   - `Minor activity mistake (NC)`

3. **Product_Knowledge_Process**:
   Error checklist (choose only from these):
   - `Didn't follow search process`
   - `Didn't check system history`
   - `Didn't describe or handle information/ service (EC)`
   - `Incomplete Information (EC)`
   - `Wrong Information (EC)`
   - `Didn't ask effective questions (EC)`

4. **Professionalism_Etiquette**:
   Error checklist (choose only from these):
   - `Didn't Welcome the customer (NC)`
   - `Didn't address customer by his name/title (NC)`
   - `Addressed customer by wrong name (NC)`
   - `Addressed customer with direct speech (NC)`
   - `Using Wrong Gender Type (NC)`
   - `Disconnected the call (EC)`
   - `Hold/Mute/Transfer violation (EC)`
   - `No transfer/wrong transfer (EC)`
   - `Didn't wait for proper time before ending call (EC)`
   - `No response and customer closed the call (EC)`
   - `Delay in closing the call (BC)`
   - `Ineffective questions/Info (NC)`
   - `Didn't follow Transfer/Mute/ Dead Air / Hold protocol (NC)`
   - `Exceeding hold time (NC)`
   - `Hold Trials (NC)`
   - `Didn't Collect the Data in Smart way (NC)`
   - `Didn't keep the conversation on track (NC)`
   - `Unable to explain (NC)`
   - `Ineffective verification (NC)`
   - `Exceeding hold time/Trials (EC)`
   - `Ineffective verification (EC)`
   - `Delay in responding (NC)`
   - `Inaccurate greeting time (NC)`
   - `No greeting/closing at all (NC)`
   - `Wrong greeting/closing structure (NC)`
   - `Didn't offer extra assistance (NC)`
   - `Improper greeting /closing tone (NC)`
   - `Delay in responding (BC)`
   - `Scripted/Monotony/sleepy/bored/cold/unwelcome/ unfriendly tone (NC)`
   - `Very fast/unclear (NC)`
   - `Not confident/hesitant (NC)`
   - `Sharp voice tone (NC)`
   - `Unfriendly tone (NC)`

5. **Soft_Skills_Behavior**:
   Error checklist (choose only from these):
   - `Interrupting the customer (NC)`
   - `Didn't reflect with the customer (NC)`
   - `Not Empathic (NC)`
   - `Didn't apologize to customer (NC)`
   - `Assumption (NC)`
   - `Not focused/Let customer repeat the information (NC)`
   - `Used repetitive word (NC)`
   - `Used language not matched with the customer (NC)`
   - `Used unprofessional/negative expressions (NC)`
   - `Didn't avoid mouth noise (NC)`
   - `Raising Headset/ Whispering (NC)`
   - `Rude behavior/Blaming & Provoking customer (EC)`
   - `Showing carelessness to cancelation requests (EC)`
   - `Didn't handle before escalation (BC)`
   - `Refused escalation to SPV (EC)`

6. **Standard_Verification**:
   Error checklist (choose only from these):
   - `Didn't ask about required data`
   - `Didn't verify/confirm/validate data`
   - `Didn't collect customer data`

7. **Business_Requirement_Process**:
   Error checklist (choose only from these):
   - `Didn't describe Script/info (BC)`
   - `Incomplete Script/info (BC)`
   - `Didn't follow process consistency (BC)`

8. **Violation_of_Privacy_Policies**:
   Error checklist (choose only from these):
   - `Didn't make security verification (CC)`

## First Call Resolution (FCR) and Customer Feedback Rules:
- **First Call Resolution (FCR)**: Did the agent resolve the customer's query or issue completely during this call without needing further callback or transfer? Output Yes, No, or NA.
- **FCR Reason**: If FCR is No, explain why in Arabic or English (e.g. "Escalated to engineering department", "Agent promised to check and call back"). If FCR is Yes or NA, this must be "None".
- **Customer Feedback**: Determine the customer's sentiment by the end of the call (Positive, Negative, or NA).
- **Customer Feedback Comment**: Comments or evidence supporting the sentiment.
"""


class QAAnalyzer:
    def __init__(self):
        self.client = genai.Client(api_key=QAConfig.get_api_key())

    def compress_audio(self, input_path: str) -> str:
        try:
            audio = AudioSegment.from_file(input_path)
            audio = audio.set_channels(1).set_frame_rate(16000)
            compressed_path = input_path.replace(os.path.splitext(input_path)[1], ".mp3")
            audio.export(compressed_path, format="mp3", bitrate="64k")
            return compressed_path
        except Exception as e:
            raise RuntimeError(f"Audio compression failed: {e}. Ensure ffmpeg is installed and the file is not corrupted.")


    def analyze_audio_final(self, file_path: str) -> Dict[str, Any]:
        processed_path = self.compress_audio(file_path)
        max_retries = 5
        audio_file = None

        try:
            for attempt in range(max_retries):
                try:
                    if audio_file:
                        try:
                            self.client.files.delete(name=audio_file.name)
                        except Exception:
                            pass
                        audio_file = None

                    audio_file = self.client.files.upload(file=processed_path)

                    import time
                    start_time = time.time()
                    while audio_file.state.name == "PROCESSING":
                        if time.time() - start_time > 180:
                            raise TimeoutError("Gemini audio file processing timed out on Google GenAI servers after 3 minutes.")
                        time.sleep(5)
                        audio_file = self.client.files.get(name=audio_file.name)

                    prompt_cfg = DataManager.get_active_prompt_config()
                    prompt = prompt_cfg.get("prompt_text", OFFICIAL_SCORECARD_PROMPT)
                    active_section_max = prompt_cfg.get("section_max", SECTION_MAX)

                    model_id = QAConfig.MODEL_NAME.replace("models/", "")

                    response = self.client.models.generate_content(
                        model=model_id,
                        contents=[prompt, audio_file],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=QAResponseSchema
                        )
                    )

                    usage = response.usage_metadata
                    DataManager.log_usage(usage.prompt_token_count, usage.candidates_token_count)

                    result = json.loads(response.text)
                    result["_tokens_input"] = usage.prompt_token_count
                    result["_tokens_output"] = usage.candidates_token_count

                    sections_data = result.get("Sections", {})

                    # Classify errors programmatically based on naming conventions and checklist mapping
                    bc_errors = []
                    ec_errors = []
                    cc_errors = []
                    nc_errors = []

                    for section_name, sec_data in sections_data.items():
                        errors = sec_data.get("Errors_Found", [])
                        evidence = sec_data.get("Evidence", "")
                        for err in errors:
                            err_str = str(err).strip()
                            # Check classifications
                            if "(BC)" in err_str or "before escalation" in err_str or "describe Script/info" in err_str or "Incomplete Script/info" in err_str or "process consistency" in err_str:
                                bc_errors.append((section_name, err_str, evidence))
                            elif "(CC)" in err_str or "security verification" in err_str:
                                cc_errors.append((section_name, err_str, evidence))
                            elif "(EC)" in err_str or "Checking System" in section_name or "search process" in err_str or "system history" in err_str:
                                ec_errors.append((section_name, err_str, evidence))
                            else:
                                nc_errors.append((section_name, err_str, evidence))

                    bc_count = len(bc_errors)
                    ec_count = len(ec_errors)
                    cc_count = len(cc_errors)
                    nc_count = len(nc_errors)

                    bc_pct = 100.0 if bc_count == 0 else 0.0
                    ec_pct = 100.0 if ec_count == 0 else 0.0
                    cc_pct = 100.0 if cc_count == 0 else 0.0
                    nc_pct = max(0.0, 100.0 - (nc_count * 12.5))

                    result["bc_pct"] = bc_pct
                    result["ec_pct"] = ec_pct
                    result["cc_pct"] = cc_pct
                    result["nc_pct"] = nc_pct

                    overall_score = (bc_pct + ec_pct + cc_pct + nc_pct) / 4.0
                    has_critical_fail = (bc_count > 0 or ec_count > 0 or cc_count > 0)

                    # Backward compatibility map
                    result["Patient_Name"] = result.get("Customer_Name", "N/A")
                    result["Patient_Phone"] = result.get("Customer_Phone", "N/A")

                    if has_critical_fail:
                        result["Overall_Status"] = "Fail"
                        result["Call_Status"] = "Fail"
                        result["Score"] = 0
                        result["Auto_Fail_Triggered"] = "Yes"
                        reasons = []
                        if bc_count > 0: reasons.append(f"{bc_count} Business Critical Errors")
                        if ec_count > 0: reasons.append(f"{ec_count} End-User Critical Errors")
                        if cc_count > 0: reasons.append(f"{cc_count} Compliance Critical Errors")
                        result["Auto_Fail_Reason"] = ", ".join(reasons)
                        
                        root_cause_parts = []
                        for sec, err, ev in (bc_errors + ec_errors + cc_errors):
                            root_cause_parts.append(f"[{sec}] Error: {err}. Evidence: {ev}")
                        result["Root_Cause_Analysis"] = " | ".join(root_cause_parts)
                    else:
                        result["Overall_Status"] = "Pass"
                        result["Call_Status"] = "Clean Pass" if nc_count == 0 else "Pass with Gaps"
                        result["Score"] = round(overall_score)
                        result["Auto_Fail_Triggered"] = "No"
                        result["Auto_Fail_Reason"] = "None"
                        result["Root_Cause_Analysis"] = "None"

                    # Map to the Detailed_Scoring structure mapped to the 4 categories
                    bc_feedback = "; ".join([f"{err} ({ev})" for sec, err, ev in bc_errors]) or "No Business Critical errors."
                    ec_feedback = "; ".join([f"{err} ({ev})" for sec, err, ev in ec_errors]) or "No End-User Critical errors."
                    cc_feedback = "; ".join([f"{err} ({ev})" for sec, err, ev in cc_errors]) or "No Compliance Critical errors."
                    nc_feedback = "; ".join([f"{err} ({ev})" for sec, err, ev in nc_errors]) or "No Non-Critical errors."

                    scoring = {
                        "Business_Critical": {
                            "score": bc_pct / 4.0,
                            "feedback": bc_feedback,
                            "result": "Pass" if bc_pct == 100 else "Fail"
                        },
                        "End_User_Critical": {
                            "score": ec_pct / 4.0,
                            "feedback": ec_feedback,
                            "result": "Pass" if ec_pct == 100 else "Fail"
                        },
                        "Compliance_Critical": {
                            "score": cc_pct / 4.0,
                            "feedback": cc_feedback,
                            "result": "Pass" if cc_pct == 100 else "Fail"
                        },
                        "Non_Critical": {
                            "score": nc_pct / 4.0,
                            "feedback": nc_feedback,
                            "result": "Pass" if nc_pct >= 70 else "Fail"
                        }
                    }
                    result["Detailed_Scoring"] = scoring

                    # Map sections to build campaign Compliance Checklist
                    result["Compliance_Checklist"] = {
                        "Campaign": result.get("Campaign", "N/A"),
                        "Call_Type": result.get("Call_Type", "N/A"),
                        "First_Call_Resolution_FCR": result.get("FCR", "NA"),
                        "Customer_Sentiment": result.get("Customer_Feedback", "NA"),
                        "Privacy_Check": "Pass" if cc_pct == 100 else "Fail",
                        "BC_Violations": "None" if bc_pct == 100 else f"{bc_count} errors",
                        "EC_Violations": "None" if ec_pct == 100 else f"{ec_count} errors",
                        "Sale_Closed": "Yes" if not has_critical_fail else "No",
                        "Behavior_Flag": result.get("Auto_Fail_Reason", "None")
                    }

                    # Map to build legacy Verification Checks
                    result["Verification_Audit"] = {
                        "Data_Collection": {
                            "status": "Fail" if any("collect customer data" in err for sec, err, ev in nc_errors) else "Pass",
                            "evidence": "Collected customer details during the call"
                        },
                        "Data_Verification": {
                            "status": "Fail" if any("verify/confirm/validate data" in err for sec, err, ev in nc_errors) else "Pass",
                            "evidence": "Verified customer details during the call"
                        },
                        "Required_Questions": {
                            "status": "Fail" if any("ask about required data" in err for sec, err, ev in nc_errors) else "Pass",
                            "evidence": "Asked all required verification questions"
                        }
                    }
                    result["Verification_Checks"] = result["Verification_Audit"]

                    # Map to build legacy Detailed_Analysis
                    strengths = result.get("Strengths", [])
                    coaching_notes = result.get("Coaching_Notes", [])
                    final_summary = result.get("Final_Summary", "")
                    auto_fail_reason = result.get("Auto_Fail_Reason", "None")

                    main_prob = auto_fail_reason if auto_fail_reason != "None" else (
                        coaching_notes[0] if coaching_notes else "No critical gaps identified."
                    )
                    prop_sol = "\n".join(coaching_notes) if coaching_notes else (
                        "Agent met expectations. Continue monitoring."
                    )

                    result["Detailed_Analysis"] = {
                        "Strengths": strengths,
                        "Weaknesses": coaching_notes,
                        "Main_Problem": main_prob,
                        "Proposed_Solution": prop_sol,
                        "Human_Narrative": final_summary
                    }

                    return result

                except Exception as e:
                    err_str = str(e).upper()
                    if ("429" in err_str or "503" in err_str or "UNAVAILABLE" in err_str or "INTERNAL" in err_str) and attempt < max_retries - 1:
                        time.sleep((2 ** attempt) * 5)
                        continue
                    raise e
        finally:
            if audio_file:
                try:
                    self.client.files.delete(name=audio_file.name)
                except Exception:
                    pass
            if processed_path != file_path:
                try:
                    if os.path.exists(processed_path):
                        os.remove(processed_path)
                except OSError:
                    pass


_PDF_PRIMARY  = colors.HexColor("#ed4224")
_PDF_DARK     = colors.HexColor("#112240")
_PDF_MID      = colors.HexColor("#546E7A")
_PDF_LIGHT_BG = colors.HexColor("#F5F7FA")
_PDF_GREEN    = colors.HexColor("#28A745")
_PDF_RED      = colors.HexColor("#DC3545")
_PDF_AMBER    = colors.HexColor("#F59E0B")
_PDF_DIVIDER  = colors.HexColor("#E2E8F0")

_PAGE_W, _PAGE_H = A4
_MARGIN = 18 * mm


class _ScoreCircle(Flowable):
    def __init__(self, score, status, size=60):
        Flowable.__init__(self)
        self.score  = score
        self.status = status
        self.size   = size
        self.width  = size
        self.height = size + 16

    def draw(self):
        r  = self.size / 2
        cx = r
        cy = r + 10
        status_upper = self.status.upper()
        if "PASS" in status_upper:
            ring = _PDF_GREEN
            txt = "PASS"
        else:
            ring = _PDF_RED
            txt = "FAIL"

        font_bold = "UnicodeFont-Bold" if UNICODE_FONT == "UnicodeFont" else "Helvetica-Bold"

        self.canv.setFillColor(colors.white)
        self.canv.setStrokeColor(ring)
        self.canv.setLineWidth(3)
        self.canv.circle(cx, cy, r, fill=1, stroke=1)

        self.canv.setFillColor(ring)
        self.canv.setFont(font_bold, 12)
        self.canv.drawCentredString(cx, cy - 4, txt)

        badge_w = max(len(self.status) * 5.5, 70)
        bx = cx - badge_w / 2
        self.canv.setFillColor(ring)
        self.canv.roundRect(bx, 0, badge_w, 12, 6, fill=1, stroke=0)
        self.canv.setFillColor(colors.white)
        self.canv.setFont(font_bold, 6.5)
        self.canv.drawCentredString(cx, 3.5, self.status.upper())


class _SectionHeader(Flowable):
    def __init__(self, title, width=None):
        Flowable.__init__(self)
        self.title = title
        self.width = width or (_PAGE_W - 2 * _MARGIN)
        self.height = 18

    def draw(self):
        self.canv.setFillColor(_PDF_DARK)
        self.canv.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        self.canv.setFillColor(colors.white)
        font_bold = "UnicodeFont-Bold" if UNICODE_FONT == "UnicodeFont" else "Helvetica-Bold"
        self.canv.setFont(font_bold, 9)
        self.canv.drawString(8, 5, self.title)



class _ProgressBar(Flowable):
    def __init__(self, pct, color=None, width=None, height=5):
        Flowable.__init__(self)
        self.pct    = pct
        self.color  = color
        self.width  = width or (_PAGE_W - 2 * _MARGIN)
        self.height = height

    def draw(self):
        self.canv.setFillColor(colors.HexColor("#E2E8F0"))
        self.canv.roundRect(0, 0, self.width, self.height, 2, fill=1, stroke=0)
        if self.pct > 0:
            fc = self.color or (_PDF_GREEN if self.pct >= 80 else (_PDF_AMBER if self.pct >= 60 else _PDF_RED))
            self.canv.setFillColor(fc)
            self.canv.roundRect(0, 0, max(4, self.width * self.pct / 100), self.height, 2, fill=1, stroke=0)


class PDFManager:
    @staticmethod
    def _s(text: Any) -> str:
        if text is None:
            return "N/A"
        text = str(text)
        for bad, good in {
            '\u2013': '-', '\u2014': '-', '\u2018': "'", '\u2019': "'",
            '\u201c': '"', '\u201d': '"', '\u2026': '...', '\u00a0': ' ',
            '\u2022': '-', '\u00b7': '-', '\u25cf': '-',
            '<': '&lt;', '>': '&gt;', '&': '&amp;',
        }.items():
            text = text.replace(bad, good)

        if HAS_ARABIC and any(u'\u0600' <= c <= u'\u06FF' for c in text):
            try:
                reshaped = arabic_reshaper.reshape(text)
                text = get_display(reshaped)
            except Exception:
                pass

        if UNICODE_FONT == "Helvetica":
            return text.encode('latin-1', 'replace').decode('latin-1')
        return text

    @staticmethod
    def create_full_pdf(res: Dict[str, Any]) -> bytes:
        try:
            buf = io.BytesIO()
            W   = _PAGE_W - 2 * _MARGIN

            doc = SimpleDocTemplate(
                buf, pagesize=A4,
                leftMargin=_MARGIN, rightMargin=_MARGIN,
                topMargin=18 * mm,  bottomMargin=18 * mm,
                title="Tatweer ProperT QA QA Audit Report",
            )

            base = getSampleStyleSheet()
            def sty(name, parent="Normal", **kw):
                return ParagraphStyle(name, parent=base[parent], **kw)

            font_regular = UNICODE_FONT
            font_bold = "UnicodeFont-Bold" if UNICODE_FONT == "UnicodeFont" else "Helvetica-Bold"
            font_italic = "UnicodeFont" if UNICODE_FONT == "UnicodeFont" else "Helvetica-Oblique"

            S = {
                "title":       sty("rt", fontSize=18, fontName=font_bold,
                                    textColor=_PDF_PRIMARY, alignment=TA_CENTER, spaceAfter=2),
                "sub":         sty("rs", fontSize=8, fontName=font_regular,
                                    textColor=_PDF_MID, alignment=TA_CENTER, spaceAfter=4),
                "lbl":         sty("fl", fontSize=9, fontName=font_bold, textColor=_PDF_DARK),
                "val":         sty("fv", fontSize=9, fontName=font_regular, textColor=_PDF_MID),
                "cat":         sty("cl", fontSize=9, fontName=font_bold, textColor=_PDF_DARK),
                "fb":          sty("fb", fontSize=8, fontName=font_regular, textColor=_PDF_MID,
                                    leading=12, spaceAfter=4),
                "body":        sty("bd", fontSize=8.5, fontName=font_regular, textColor=_PDF_DARK,
                                    leading=13, spaceAfter=4),
                "body_italic": sty("bi", fontSize=8.5, fontName=font_italic,
                                    textColor=_PDF_MID, leading=13, spaceAfter=4),
                "sec_lbl":     sty("sl", fontSize=9, fontName=font_bold, textColor=_PDF_PRIMARY),
                "footer":      sty("ft", fontSize=7, fontName=font_regular,
                                    textColor=_PDF_MID, alignment=TA_CENTER),
            }

            _s  = PDFManager._s
            sp  = lambda h=4: Spacer(1, h)
            hr  = lambda: HRFlowable(width="100%", thickness=0.5, color=_PDF_DIVIDER, spaceAfter=4)

            story = []

            logo_path = QAConfig.LOGO_FILE
            has_logo = False
            if os.path.exists(logo_path):
                try:
                    logo_img = Image(logo_path, width=16 * mm, height=16 * mm)
                    has_logo = True
                except Exception:
                    has_logo = False

            if has_logo:
                title_style = ParagraphStyle(
                    "HeaderTitle",
                    parent=S["title"],
                    fontSize=18,
                    leading=20,
                    alignment=TA_LEFT,
                    spaceAfter=0
                )
                subtitle_style = ParagraphStyle(
                    "HeaderSub",
                    parent=S["sub"],
                    fontSize=8.5,
                    leading=10,
                    alignment=TA_LEFT,
                    spaceAfter=0
                )

                title_p = Paragraph(f"<b><font color='{_PDF_PRIMARY.hexval()}'>TATWEER PROPERT QA</font></b>", title_style)
                sub_p = Paragraph("Enterprise QA Audit Report", subtitle_style)

                text_tbl = Table([[title_p], [sub_p]], colWidths=[65 * mm])
                text_tbl.setStyle(TableStyle([
                    ("VALIGN", (0,0),(-1,-1), "MIDDLE"),
                    ("LEFTPADDING", (0,0),(-1,-1), 0),
                    ("RIGHTPADDING", (0,0),(-1,-1), 0),
                    ("TOPPADDING", (0,0),(-1,-1), 0),
                    ("BOTTOMPADDING", (0,0),(-1,-1), 0),
                ]))

                left_tbl = Table([[logo_img, text_tbl]], colWidths=[20 * mm, 65 * mm])
                left_tbl.setStyle(TableStyle([
                    ("VALIGN", (0,0),(-1,-1), "MIDDLE"),
                    ("LEFTPADDING", (0,0),(-1,-1), 0),
                    ("RIGHTPADDING", (0,0),(-1,-1), 0),
                    ("TOPPADDING", (0,0),(-1,-1), 0),
                    ("BOTTOMPADDING", (0,0),(-1,-1), 0),
                ]))

                campaign_style = ParagraphStyle(
                    "HeaderCampaign",
                    parent=S["sub"],
                    fontSize=8,
                    leading=11,
                    alignment=TA_RIGHT,
                )
                campaign_p = Paragraph(
                    f"<b>{_s(res.get('Campaign', 'Tatweer Misr'))}</b><br/>Call Type: {_s(res.get('Call_Type', 'General Inquiry'))}<br/>QA Call Evaluation",
                    campaign_style
                )

                header_tbl = Table([[left_tbl, campaign_p]], colWidths=[W * 0.65, W * 0.35])
                header_tbl.setStyle(TableStyle([
                    ("VALIGN", (0,0),(-1,-1), "MIDDLE"),
                    ("LEFTPADDING", (0,0),(-1,-1), 0),
                    ("RIGHTPADDING", (0,0),(-1,-1), 0),
                    ("TOPPADDING", (0,0),(-1,-1), 0),
                    ("BOTTOMPADDING", (0,0),(-1,-1), 0),
                ]))
                story.append(header_tbl)
            else:
                story.append(Paragraph("TATWEER PROPERT QA", S["title"]))
                story.append(Paragraph("Enterprise QA Audit Report", S["sub"]))
                story.append(Paragraph(
                    f"{_s(res.get('Campaign', 'Tatweer Misr'))} &nbsp;|&nbsp; Call Type: {_s(res.get('Call_Type', 'General Inquiry'))} &nbsp;|&nbsp; QA Call Evaluation",
                    S["sub"]))

            story.append(sp(2))
            story.append(hr())
            story.append(sp(2))

            score       = res.get("Score", 0)
            call_status = res.get("Call_Status", "N/A")

            story.append(_SectionHeader("■  GENERAL OVERVIEW", width=W))
            story.append(sp(6))

            info_data = []
            for lbl, val in [
                ("Call ID",      res.get("Call_ID", "N/A")),
                ("Agent",        res.get("Agent_Name", "N/A")),
                ("Customer",     res.get("Customer_Name", res.get("Patient_Name", "N/A"))),
                ("Phone",        res.get("Customer_Phone", res.get("Patient_Phone", "N/A"))),
                ("Call Date",    res.get("Call_Date", "N/A")),
                ("FCR",          res.get("FCR", "NA")),
                ("Feedback",     res.get("Customer_Feedback", "NA")),
                ("Status",       call_status),
            ]:
                info_data.append([Paragraph(_s(lbl), S["lbl"]), Paragraph(_s(val), S["val"])])

            info_tbl = Table(info_data, colWidths=[30 * mm, 85 * mm])
            info_tbl.setStyle(TableStyle([
                ("TOPPADDING",    (0,0),(-1,-1), 3),
                ("BOTTOMPADDING",(0,0),(-1,-1), 3),
                ("LEFTPADDING",  (0,0),(-1,-1), 0),
                ("ROWBACKGROUNDS",(0,0),(-1,-1), [colors.white, _PDF_LIGHT_BG]),
                ("LINEBELOW",    (0,-1),(-1,-1), 0.3, _PDF_DIVIDER),
            ]))

            overview_tbl = Table([[info_tbl, _ScoreCircle(score, call_status)]],
                                  colWidths=[W - 75, 75])
            overview_tbl.setStyle(TableStyle([
                ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
                ("LEFTPADDING",  (0,0),(-1,-1), 0),
                ("RIGHTPADDING", (0,0),(-1,-1), 0),
                ("TOPPADDING",   (0,0),(-1,-1), 0),
                ("BOTTOMPADDING",(0,0),(-1,-1), 0),
            ]))
            story.append(overview_tbl)
            story.append(sp(10))

            if "FAIL" in call_status.upper():
                auto_fail_reason = res.get("Auto_Fail_Reason", "None")
                root_cause = res.get("Root_Cause_Analysis", "None")
                
                alert_title_style = ParagraphStyle(
                    "AlertTitle",
                    parent=S["lbl"],
                    textColor=_PDF_RED,
                    fontSize=9.5,
                    fontName=font_bold,
                    spaceAfter=4
                )
                alert_desc_style = ParagraphStyle(
                    "AlertDesc",
                    parent=S["body"],
                    textColor=_PDF_DARK,
                    fontSize=8.5,
                    leading=12
                )
                
                alert_content = [
                    Paragraph("<b>CRITICAL AUTO-FAIL VIOLATION DETECTED</b>", alert_title_style),
                    Paragraph(f"<b>Auto-Fail Reason:</b> {_s(auto_fail_reason)}", alert_desc_style),
                    Paragraph(f"<b>Root Cause & Evidence:</b> {_s(root_cause)}", alert_desc_style)
                ]
                
                alert_tbl = Table([[alert_content]], colWidths=[W])
                alert_tbl.setStyle(TableStyle([
                    ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#FFF5F5")),
                    ("BOX", (0,0), (-1,-1), 1.5, _PDF_RED),
                    ("TOPPADDING", (0,0), (-1,-1), 8),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 8),
                    ("LEFTPADDING", (0,0), (-1,-1), 10),
                    ("RIGHTPADDING", (0,0), (-1,-1), 10),
                ]))
                story.append(alert_tbl)
                story.append(sp(10))

            story.append(_SectionHeader("■  DETAILED SCORING", width=W))
            story.append(sp(6))

            scoring     = res.get("Detailed_Scoring", {})

            prompt_cfg = DataManager.get_active_prompt_config()
            active_section_max = prompt_cfg.get("section_max", SECTION_MAX)

            for cat, data in scoring.items():
                label     = cat.replace("_", " ")
                res_val   = data.get("result", "Pass").upper()
                
                if "PASS" in res_val:
                    res_label = "Pass"
                    sc = _PDF_GREEN
                    pct = 100
                    bar_color = _PDF_GREEN
                elif "N/A" in res_val or "NA" in res_val:
                    res_label = "N/A"
                    sc = _PDF_MID
                    pct = 100
                    bar_color = colors.HexColor("#CBD5E1")
                else:
                    res_label = "Fail"
                    sc = _PDF_RED
                    pct = 0
                    bar_color = _PDF_RED

                row = Table([[
                    Paragraph(_s(label), S["cat"]),
                    Paragraph(_s(res_label),
                               ParagraphStyle("tmp", parent=S["cat"], textColor=sc, alignment=TA_RIGHT)),
                ]], colWidths=[W * 0.75, W * 0.25])
                row.setStyle(TableStyle([
                    ("LEFTPADDING",  (0,0),(-1,-1), 0),
                    ("RIGHTPADDING", (0,0),(-1,-1), 0),
                    ("TOPPADDING",   (0,0),(-1,-1), 0),
                    ("BOTTOMPADDING",(0,0),(-1,-1), 2),
                ]))

                cat_block = []
                cat_block.append(row)
                cat_block.append(sp(2))
                if data.get("feedback"):
                    cat_block.append(Paragraph(_s(data["feedback"]), S["fb"]))
                cat_block.append(sp(3))
                story.append(KeepTogether(cat_block))

            story.append(sp(6))

            checklist = res.get("Compliance_Checklist", {})
            chk_rows  = []
            for key, val in checklist.items():
                vu = str(val).strip().upper()
                if vu in ("YES","PASS","TRUE"):
                    badge, vc = "✓ Yes", _PDF_GREEN
                elif vu in ("NO","FAIL","FALSE"):
                    badge, vc = "✗ No", _PDF_RED
                else:
                    badge, vc = _s(val), _PDF_MID
                chk_rows.append([
                    Paragraph(_s(key.replace("_", " ")), S["val"]),
                    Paragraph(badge, ParagraphStyle("cv", parent=S["val"],
                               textColor=vc, fontName="Helvetica-Bold", alignment=TA_RIGHT)),
                ])

            chk_tbl = Table(chk_rows, colWidths=[W * 0.7, W * 0.3])
            chk_tbl.setStyle(TableStyle([
                ("TOPPADDING",    (0,0),(-1,-1), 4),
                ("BOTTOMPADDING",(0,0),(-1,-1), 4),
                ("LEFTPADDING",  (0,0),(-1,-1), 0),
                ("LINEBELOW",    (0,0),(-1,-2), 0.3, _PDF_DIVIDER),
                ("ROWBACKGROUNDS",(0,0),(-1,-1), [colors.white, _PDF_LIGHT_BG]),
            ]))

            story.append(KeepTogether([
                _SectionHeader("■  COMPLIANCE CHECKLIST", width=W),
                sp(6),
                chk_tbl,
                sp(10)
            ]))

            analysis   = res.get("Detailed_Analysis", {})
            strengths  = analysis.get("Strengths", [])
            weaknesses = analysis.get("Weaknesses", [])

            def _bullets(items, icon, color):
                out = []
                for item in items:
                    out.append(Paragraph(
                        f'<font color="{color.hexval()}">{icon}</font>  {_s(item)}',
                        S["body"]))
                return out or [Paragraph("None recorded.", S["body_italic"])]

            def _col_hdr(txt, color):
                return Paragraph(txt, ParagraphStyle("ch", parent=S["sec_lbl"],
                                   textColor=color, spaceAfter=4))

            analysis_tbl = Table([[
                [_col_hdr("Strengths", _PDF_GREEN)]            + _bullets(strengths,  "✓", _PDF_GREEN),
                [_col_hdr("Areas for Improvement", _PDF_RED)]  + _bullets(weaknesses, "✗", _PDF_RED),
            ]], colWidths=[W * 0.5 - 4, W * 0.5 - 4])
            analysis_tbl.setStyle(TableStyle([
                ("VALIGN",       (0,0),(-1,-1), "TOP"),
                ("LEFTPADDING",  (0,0),(-1,-1), 6),
                ("RIGHTPADDING", (0,0),(-1,-1), 6),
                ("TOPPADDING",   (0,0),(-1,-1), 6),
                ("BOTTOMPADDING",(0,0),(-1,-1), 6),
                ("BOX",          (0,0),(0,0), 0.5, _PDF_DIVIDER),
                ("BOX",          (1,0),(1,0), 0.5, _PDF_DIVIDER),
                ("BACKGROUND",   (0,0),(0,0), colors.HexColor("#F0FFF4")),
                ("BACKGROUND",   (1,0),(1,0), colors.HexColor("#FFF5F5")),
            ]))

            story.append(KeepTogether([
                _SectionHeader("■  PERFORMANCE ANALYSIS", width=W),
                sp(6),
                analysis_tbl,
                sp(10)
            ]))

            gap_tbl = Table([
                [Paragraph("Main Problem\nIdentified", S["lbl"]),
                 Paragraph(_s(analysis.get("Main_Problem", "N/A")), S["body"])],
                [Paragraph("Coaching Script", S["lbl"]),
                 Paragraph(_s(analysis.get("Proposed_Solution", "N/A")),
                            ParagraphStyle("cs2", parent=S["body"], textColor=_PDF_PRIMARY))],
            ], colWidths=[38 * mm, W - 38 * mm])
            gap_tbl.setStyle(TableStyle([
                ("TOPPADDING",    (0,0),(-1,-1), 6),
                ("BOTTOMPADDING",(0,0),(-1,-1), 6),
                ("LEFTPADDING",  (0,0),(-1,-1), 6),
                ("VALIGN",       (0,0),(-1,-1), "TOP"),
                ("LINEBELOW",    (0,0),(-1,-2), 0.3, _PDF_DIVIDER),
                ("BACKGROUND",   (0,0),(0,-1), _PDF_LIGHT_BG),
            ]))

            story.append(KeepTogether([
                _SectionHeader("■  CRITICAL GAP & CORRECTIVE ACTION", width=W),
                sp(6),
                gap_tbl,
                sp(10)
            ]))

            story.append(KeepTogether([
                _SectionHeader("■  AUDITOR'S FINAL SUMMARY", width=W),
                sp(6),
                Paragraph(_s(analysis.get("Human_Narrative", "N/A")), S["body"]),
                sp(10)
            ]))

            def draw_page_decorations(canvas, doc_obj):
                canvas.saveState()
                canvas.setStrokeColor(_PDF_DIVIDER)
                canvas.setLineWidth(0.5)
                canvas.line(_MARGIN, 15 * mm, _PAGE_W - _MARGIN, 15 * mm)

                canvas.setFont(font_regular, 7.5)
                canvas.setFillColor(_PDF_MID)
                footer_text = "Tatweer ProperT QA System  |  Assurance Hub Marketing  |  Confidential"
                canvas.drawString(_MARGIN, 10 * mm, footer_text)

                page_num = f"Page {doc_obj.page}"
                canvas.drawRightString(_PAGE_W - _MARGIN, 10 * mm, page_num)
                canvas.restoreState()

            doc.build(story, onFirstPage=draw_page_decorations, onLaterPages=draw_page_decorations)
            return buf.getvalue()

        except Exception as e:
            print(f"PDF Error: {str(e)}")
            return b""


def background_analysis(item_id: int, file_path: str):
    import re
    import traceback
    from storage import S3Manager
    import tempfile
    import os

    local_temp_path = None
    try:
        DataManager.update_queue_status(item_id, "Processing")

        if QAConfig.is_s3_enabled():
            s3_key = file_path
            suffix = os.path.splitext(s3_key)[1] or ".mp3"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                local_temp_path = tmp.name

            print(f"Downloading audio from S3 key '{s3_key}' to '{local_temp_path}'")
            S3Manager.download_file(s3_key, local_temp_path)
            actual_file_path = local_temp_path
        else:
            actual_file_path = file_path

        analyzer = QAAnalyzer()
        result   = analyzer.analyze_audio_final(actual_file_path)

        input_tokens  = result.get("_tokens_input", 0)
        output_tokens = result.get("_tokens_output", 0)
        cost = QAConfig.calculate_cost(input_tokens, output_tokens)

        result["_cost"] = cost

        original_filename = ""
        with SessionLocal() as db:
            queue_item = db.query(AnalysisQueue).filter(AnalysisQueue.id == item_id).first()
            if queue_item:
                original_filename = queue_item.filename

        filename_phone = ""
        if original_filename:
            match = re.search(r'\b\d{10}\b', original_filename)
            if not match:
                match = re.search(r'\d{10}', original_filename)
            if match:
                filename_phone = match.group(0)

        current_phone = str(result.get("Customer_Phone", result.get("Patient_Phone", ""))).strip()
        is_invalid = (
            not current_phone or
            current_phone.lower() in ("n/a", "unknown", "none") or
            not any(c.isdigit() for c in current_phone) or
            current_phone == result.get("Customer_Name", result.get("Patient_Name", ""))
        )
        if is_invalid and filename_phone:
            result["Customer_Phone"] = filename_phone
            result["Patient_Phone"] = filename_phone

        DataManager.update_queue_status(
            item_id, "Completed",
            result=json.dumps(result),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost
        )
    except Exception as e:
        traceback.print_exc()
        DataManager.update_queue_status(item_id, "Failed", error=str(e))
    finally:
        try:
            if local_temp_path and os.path.exists(local_temp_path):
                os.remove(local_temp_path)
        except OSError:
            pass
        try:
            if not QAConfig.is_s3_enabled() and file_path and os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            pass
