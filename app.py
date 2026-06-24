import streamlit as st
import os
import tempfile
import time
import json
import base64
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import extra_streamlit_components as stx
from concurrent.futures import ThreadPoolExecutor
from config import QAConfig
from database import DataManager, AuthManager, SessionLocal, AnalysisQueue, db_import_error

if db_import_error:
    st.error("Database Initialization Error (Traceback below):")
    st.code(db_import_error)
    st.stop()

from core import QAAnalyzer, PDFManager, background_analysis
import html

def _e(val) -> str:
    if val is None:
        return "N/A"
    return html.escape(str(val))

APP_VERSION = "v1.0.0"

_global_executor = ThreadPoolExecutor(max_workers=3)

def _get_executor():
    return _global_executor



class UIHandler:
    @staticmethod
    def get_base64_image(image_path: str):
        try:
            if os.path.exists(image_path):
                with open(image_path, "rb") as img_file:
                    return base64.b64encode(img_file.read()).decode()
            return None
        except Exception as e:
            print(f"Error loading logo: {e}")
            return None

    @staticmethod
    def apply_styles():
        theme = st.session_state.get("theme", "light")

        if theme == "dark":
            bg_color = "#070d19"
            card_bg = "#0f1a30"
            text_main = "#f1f5f9"
            text_light = "#94a3b8"
            border_color = "#1e293b"
            secondary_color = "#f1f5f9"
            input_bg = "#172641"
            tab_hover_bg = "rgba(255, 255, 255, 0.03)"
            primary_light = "rgba(237, 66, 36, 0.08)"
        else:
            bg_color = "#f8fafc"
            card_bg = "#ffffff"
            text_main = "#0a192f"
            text_light = "#546e7a"
            border_color = "#e2e8f0"
            secondary_color = "#0a192f"
            input_bg = "#ffffff"
            tab_hover_bg = "#f8fafc"
            primary_light = "#fff5f0"

        st.markdown(f"""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap');

            :root {{
                --primary-color: {QAConfig.PRIMARY_COLOR};
                --bg-color: {bg_color};
                --card-bg: {card_bg};
                --text-main: {text_main};
                --text-light: {text_light};
                --border-color: {border_color};
                --secondary-color: {secondary_color};
                --input-bg: {input_bg};
                --tab-hover-bg: {tab_hover_bg};
                --primary-light: {primary_light};
                color-scheme: {"dark" if theme == "dark" else "light"} !important;
            }}

            input, select, textarea, button {{
                color-scheme: {"dark" if theme == "dark" else "light"} !important;
            }}

            html, body, [class*="css"] {{
                font-family: 'Outfit', sans-serif;
            }}

            /* Style main container background */
            [data-testid="stAppViewContainer"] {{
                background-color: var(--bg-color) !important;
            }}

            /* Target main content text elements specifically, avoiding sidebar */
            [data-testid="stAppViewContainer"] p,
            [data-testid="stAppViewContainer"] span,
            [data-testid="stAppViewContainer"] label,
            [data-testid="stAppViewContainer"] h1,
            [data-testid="stAppViewContainer"] h2,
            [data-testid="stAppViewContainer"] h3,
            [data-testid="stAppViewContainer"] h4,
            [data-testid="stAppViewContainer"] h5,
            [data-testid="stAppViewContainer"] h6,
            [data-testid="stAppViewContainer"] p *,
            [data-testid="stAppViewContainer"] span *,
            [data-testid="stAppViewContainer"] label * {{
                color: var(--text-main) !important;
            }}

            [data-testid="stAppViewContainer"] p,
            [data-testid="stAppViewContainer"] span[data-testid="stText"],
            [data-testid="stAppViewContainer"] .stMarkdown p {{
                color: var(--text-light) !important;
            }}

            /* Hide Streamlit default branding elements */
            #MainMenu {{visibility: hidden !important;}}
            footer {{visibility: hidden !important;}}
            [data-testid="stDecoration"] {{display: none !important;}}

            /* Style the collapse sidebar button inside the sidebar (when open) */
            [data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] button {{
                color: #ffffff !important;
                background-color: rgba(255, 255, 255, 0.05) !important;
                border: 1px solid rgba(255, 255, 255, 0.1) !important;
                border-radius: 8px !important;
                transition: all 0.2s ease !important;
            }}
            [data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] button:hover {{
                background-color: var(--primary-color) !important;
                color: #ffffff !important;
                border-color: var(--primary-color) !important;
            }}

            /* ── Premium Sidebar Redesign (Always Dark) ── */
            [data-testid="stSidebar"] {{
                background: linear-gradient(180deg, #0a192f 0%, #050d18 100%) !important;
                border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
                box-shadow: 4px 0 24px rgba(15, 23, 42, 0.15) !important;
            }}
            [data-testid="stSidebar"] p,
            [data-testid="stSidebar"] span,
            [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] div,
            [data-testid="stSidebar"] h1,
            [data-testid="stSidebar"] h2,
            [data-testid="stSidebar"] h3,
            [data-testid="stSidebar"] h4,
            [data-testid="stSidebar"] h5,
            [data-testid="stSidebar"] h6,
            [data-testid="stSidebar"] input,
            [data-testid="stSidebar"] button,
            [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
            [data-testid="stSidebar"] p *,
            [data-testid="stSidebar"] span *,
            [data-testid="stSidebar"] label *,
            [data-testid="stSidebar"] div * {{
                color: #ffffff !important;
            }}
            [data-testid="stSidebar"] .sidebar-brand {{
                color: #ffffff !important;
            }}
            [data-testid="stSidebar"] .sidebar-tagline,
            [data-testid="stSidebar"] .user-pill-role {{
                color: rgba(255, 255, 255, 0.55) !important;
            }}
            [data-testid="stSidebar"] hr {{
                border-color: rgba(255, 255, 255, 0.1) !important;
            }}

            /* Modern Navigation List styling for Radio Buttons */
            [data-testid="stSidebar"] div[role="radiogroup"] > label {{
                background: rgba(255, 255, 255, 0.02) !important;
                border: 1px solid rgba(255, 255, 255, 0.04) !important;
                border-radius: 10px !important;
                padding: 12px 16px !important;
                margin-bottom: 8px !important;
                transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
                cursor: pointer !important;
                display: flex !important;
                align-items: center !important;
                gap: 12px !important;
            }}
            [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {{
                background: rgba(255, 255, 255, 0.06) !important;
                border-color: var(--primary-color)60 !important;
                transform: translateX(4px) !important;
            }}
            [data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {{
                background: linear-gradient(90deg, var(--primary-color)20 0%, var(--primary-color)05 100%) !important;
                border-color: var(--primary-color) !important;
                box-shadow: inset 4px 0 0 var(--primary-color), 0 4px 12px rgba(237,66,36,0.08) !important;
                font-weight: 700 !important;
            }}
            [data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child,
            [data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child,
            [data-testid="stSidebar"] div[role="radiogroup"] input[type="radio"],
            [data-testid="stSidebar"] div[role="radiogroup"] div[data-testid="stMarker"] {{
                display: none !important;
            }}
            /* Ensure the text is left-aligned and padded */
            [data-testid="stSidebar"] [data-testid="stRadio"] label p {{
                padding-left: 0px !important;
                margin: 0 !important;
            }}

            /* ── Page Header ── */
            .page-header {{
                background: var(--card-bg) !important;
                border: 1px solid var(--border-color) !important;
                border-left: 5px solid var(--primary-color) !important;
                box-shadow: 0 1px 3px rgba(0,0,0,0.02) !important;
                border-radius: 12px !important;
                padding: 20px 24px !important;
                margin-bottom: 24px !important;
            }}
            .page-header h2 {{
                margin: 0 0 4px 0 !important;
                font-size: 1.5rem !important;
                font-weight: 850 !important;
                color: var(--secondary-color) !important;
                letter-spacing: -0.01em !important;
            }}
            .page-header p {{
                margin: 0 !important;
                color: var(--text-light) !important;
                font-size: 0.9rem !important;
                font-weight: 500 !important;
            }}

            /* ── Professional-Style Cards ── */
            .report-section {{
                background: var(--card-bg) !important;
                border-radius: 12px !important;
                padding: 20px !important;
                margin-bottom: 16px !important;
                border: 1px solid var(--border-color) !important;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02) !important;
            }}

            /* ── Glassmorphic Metric Cards ── */
            .metric-card {{
                background: var(--card-bg) !important;
                border: 1px solid var(--border-color) !important;
                padding: 18px 20px !important;
                border-radius: 12px !important;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02) !important;
                border-left: 4px solid var(--secondary-color) !important;
                text-align: left !important;
                transition: all 0.2s ease !important;
                height: 100% !important;
            }}
            .metric-card:hover {{
                transform: translateY(-2px) !important;
                box-shadow: 0 6px 16px rgba(15, 23, 42, 0.04) !important;
                border-color: var(--primary-color) !important;
            }}
            .metric-label {{
                color: var(--text-light) !important;
                font-size: 0.75rem !important;
                font-weight: 700 !important;
                text-transform: uppercase !important;
                letter-spacing: 0.06em !important;
                margin-bottom: 6px !important;
            }}
            .metric-value {{
                color: var(--secondary-color) !important;
                font-size: 1.8rem !important;
                font-weight: 800 !important;
                line-height: 1.1 !important;
            }}

            /* ── Headings ── */
            h1, h2, h3, h4 {{
                color: var(--secondary-color) !important;
                font-weight: 800 !important;
                letter-spacing: -0.02em !important;
            }}

            /* ── Badges ── */
            .badge {{
                padding: 4px 10px !important;
                border-radius: 20px !important;
                font-size: 0.72rem !important;
                font-weight: 700 !important;
                text-transform: uppercase !important;
                letter-spacing: 0.04em !important;
                display: inline-block !important;
            }}
            .badge-completed  {{ background: #dcfce7 !important; color: {QAConfig.SUCCESS_COLOR} !important; }}
            .badge-processing {{ background: #fef9c3 !important; color: #a16207 !important; }}
            .badge-failed     {{ background: #fee2e2 !important; color: {QAConfig.DANGER_COLOR} !important; }}
            .badge-pending    {{ background: #f1f5f9 !important; color: var(--text-light) !important; }}

            /* ── Forms & Container ── */
            [data-testid="stForm"] {{
                background-color: var(--card-bg) !important;
                border-radius: 12px !important;
                border: 1px solid var(--border-color) !important;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02) !important;
                padding: 24px !important;
            }}

            /* ── Modern Input Fields ── */
            div[data-baseweb="input"], div[data-baseweb="select"], div[data-baseweb="textarea"] {{
                background: var(--input-bg) !important;
                border: 1px solid var(--border-color) !important;
                border-radius: 10px !important;
                transition: all 0.2s ease !important;
            }}
            div[data-baseweb="input"] input,
            div[data-baseweb="select"] select,
            div[data-baseweb="textarea"] textarea,
            div[data-baseweb="input"] input *,
            div[data-baseweb="select"] select *,
            div[data-baseweb="textarea"] textarea * {{
                color: var(--text-main) !important;
            }}
            div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within, div[data-baseweb="textarea"]:focus-within {{
                border-color: var(--primary-color) !important;
                box-shadow: 0 0 0 3px var(--primary-color)20 !important;
            }}

            /* ── File Uploader widget styling ── */
            [data-testid="stFileUploader"] {{
                background-color: var(--card-bg) !important;
                border: 1px dashed var(--border-color) !important;
                border-radius: 12px !important;
                padding: 12px !important;
            }}
            [data-testid="stFileUploader"] section {{
                background-color: var(--card-bg) !important;
                border: none !important;
            }}
            [data-testid="stFileUploader"] section div,
            [data-testid="stFileUploader"] section div *,
            [data-testid="stFileUploader"] section span,
            [data-testid="stFileUploader"] section span * {{
                color: var(--text-main) !important;
            }}
            [data-testid="stFileUploader"] button {{
                background-color: var(--tab-hover-bg) !important;
                color: var(--text-main) !important;
                border: 1px solid var(--border-color) !important;
            }}
            [data-testid="stFileUploader"] button * {{
                color: var(--text-main) !important;
            }}

            /* ── File Uploader uploaded file items styling ── */
            div[data-testid="stFileUploaderFile"] {{
                background-color: var(--card-bg) !important;
                border: 1px solid var(--border-color) !important;
                border-radius: 8px !important;
                padding: 4px 8px !important;
            }}
            div[data-testid="stFileUploaderFile"] *,
            div[data-testid="stFileUploaderFileName"],
            span[data-testid="stFileUploaderFileName"] {{
                background-color: transparent !important;
                color: var(--text-main) !important;
            }}

            /* ── Styled Primary Buttons ── */
            .stButton>button {{
                background: linear-gradient(135deg, var(--primary-color) 0%, #bd341c 100%) !important;
                color: white !important;
                border: none !important;
                border-radius: 10px !important;
                font-weight: 700 !important;
                padding: 10px 24px !important;
                font-size: 0.92rem !important;
                transition: all 0.2s ease !important;
                box-shadow: 0 4px 12px rgba(237,66,36,0.15) !important;
                cursor: pointer !important;
            }}
            .stButton>button * {{
                color: white !important;
            }}
            .stButton>button:hover {{
                transform: translateY(-1px) !important;
                box-shadow: 0 6px 16px rgba(237,66,36,0.25) !important;
                background: linear-gradient(135deg, #bd341c 0%, var(--primary-color) 100%) !important;
            }}

            /* ── Progress & Score Bars ── */
            .score-bar-container {{
                background: var(--border-color) !important;
                border-radius: 8px !important;
                height: 8px !important;
                width: 100% !important;
                margin-top: 8px !important;
                overflow: hidden !important;
            }}
            .score-bar-fill {{
                height: 8px !important;
                border-radius: 8px !important;
            }}

            /* ── Compliance items ── */
            .compliance-row {{
                display: flex !important;
                justify-content: space-between !important;
                align-items: center !important;
                padding: 12px 14px !important;
                border-bottom: 1px solid var(--border-color) !important;
                transition: background 0.2s ease !important;
            }}
            .compliance-row:last-child {{
                border-bottom: none !important;
            }}
            .compliance-row:hover {{
                background: var(--tab-hover-bg) !important;
            }}
            .compliance-item {{
                display: flex !important;
                justify-content: space-between !important;
                align-items: center !important;
                padding: 12px 0 !important;
                border-bottom: 1px solid var(--border-color) !important;
            }}
            .compliance-yes  {{ color: {QAConfig.SUCCESS_COLOR} !important; font-weight: 700 !important; }}
            .compliance-no   {{ color: {QAConfig.DANGER_COLOR} !important;  font-weight: 700 !important; }}

            .usage-card {{
                background: var(--card-bg) !important;
                border-radius: 12px !important;
                padding: 16px 20px !important;
                border-left: 4px solid var(--primary-color) !important;
                border: 1px solid var(--border-color) !important;
                margin-bottom: 10px !important;
            }}

            /* ── Queue & Leaderboard Items ── */
            .queue-item, .queue-card {{
                background: var(--card-bg) !important;
                border-radius: 10px !important;
                padding: 12px 16px !important;
                margin-bottom: 8px !important;
                border: 1px solid var(--border-color) !important;
                box-shadow: 0 1px 2px rgba(0,0,0,0.01) !important;
                transition: all 0.2s ease !important;
            }}
            .queue-item:hover, .queue-card:hover {{
                background: var(--tab-hover-bg) !important;
                border-color: var(--primary-color)40 !important;
                transform: translateX(3px) !important;
            }}

            .leader-card {{
                background: var(--card-bg) !important;
                border-radius: 12px !important;
                padding: 12px 18px !important;
                margin-bottom: 8px !important;
                border: 1px solid var(--border-color) !important;
                box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
                display: flex !important;
                align-items: center !important;
                transition: all 0.2s ease !important;
            }}
            .leader-card:hover {{
                background: var(--tab-hover-bg) !important;
                border-color: var(--primary-color)40 !important;
                transform: translateX(3px) !important;
            }}

            /* ── Compliance Heatmap / Metric Grid ── */
            .compliance-metric-card {{
                background: var(--card-bg) !important;
                border: 1px solid var(--border-color) !important;
                border-radius: 12px !important;
                padding: 16px !important;
                text-align: center !important;
                box-shadow: 0 1px 2px rgba(0,0,0,0.01) !important;
                transition: all 0.2s ease !important;
            }}
            .compliance-metric-card:hover {{
                border-color: #cbd5e1 !important;
                box-shadow: 0 4px 12px rgba(15,23,42,0.03) !important;
            }}

            /* ── Sidebar logo area ── */
            .sidebar-logo {{
                text-align: center !important;
                padding: 24px 16px 16px !important;
            }}
            .sidebar-logo img {{
                width: 90px !important;
                border-radius: 12px !important;
                margin-bottom: 12px !important;
                filter: drop-shadow(0px 8px 16px rgba(237,66,36,0.15)) !important;
            }}
            .sidebar-brand {{
                font-size: 1.25rem !important;
                font-weight: 900 !important;
                color: #ffffff !important;
                letter-spacing: 0.05em !important;
            }}
            .sidebar-tagline {{
                font-size: 0.75rem !important;
                color: rgba(255,255,255,0.45) !important;
                margin-top: 4px !important;
            }}

            /* ── User pill ── */
            .user-pill {{
                background: rgba(255,255,255,0.04) !important;
                border: 1px solid rgba(255,255,255,0.08) !important;
                border-radius: 14px !important;
                padding: 12px 16px !important;
                display: flex !important;
                align-items: center !important;
                gap: 12px !important;
                margin: 16px 0 !important;
            }}
            .user-pill-name {{
                font-weight: 700 !important;
                font-size: 0.9rem !important;
                color: #ffffff !important;
            }}
            .user-pill-role {{
                font-size: 0.72rem !important;
                color: rgba(255,255,255,0.45) !important;
                font-weight: 600 !important;
                text-transform: uppercase !important;
                letter-spacing: 0.05em !important;
            }}

            /* ── Styled Tabs ── */
            .stTabs [data-baseweb="tab-list"] {{
                gap: 8px !important;
                background-color: transparent !important;
                border-bottom: 1px solid var(--border-color) !important;
                padding-bottom: 4px !important;
            }}
            .stTabs [data-baseweb="tab"] {{
                height: 40px !important;
                white-space: pre-wrap !important;
                background-color: var(--card-bg) !important;
                border: 1px solid var(--border-color) !important;
                border-radius: 8px 8px 0 0 !important;
                padding: 10px 16px !important;
                font-weight: 600 !important;
                color: var(--secondary-color) !important;
                transition: all 0.2s ease !important;
            }}
            .stTabs [data-baseweb="tab"]:hover {{
                background-color: var(--tab-hover-bg) !important;
                color: var(--primary-color) !important;
            }}
            .stTabs [aria-selected="true"] {{
                background-color: var(--card-bg) !important;
                color: var(--primary-color) !important;
                border-bottom: 2px solid var(--primary-color) !important;
                font-weight: 700 !important;
            }}
            </style>
        """, unsafe_allow_html=True)


    @staticmethod
    def render_login(cookie_manager):
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1.4, 1])
        with col2:
            logo_base64 = UIHandler.get_base64_image(QAConfig.LOGO_FILE)
            if logo_base64:
                logo_html = f'<img src="data:image/png;base64,{logo_base64}" style="width: 120px; margin-bottom: 16px; border-radius: 10px;">'
            else:
                logo_html = f'<div style="width:80px; height:80px; background:{QAConfig.PRIMARY_COLOR}; border-radius:14px; display:flex; align-items:center; justify-content:center; margin: 0 auto 16px; font-size:2rem;">TP</div>'

            st.markdown(f"""
                <div style='text-align: center; margin-bottom: 28px;'>
                    {logo_html}
                    <h1 style='color: {QAConfig.PRIMARY_COLOR}; font-weight: 800; margin: 0 0 6px; font-size: 2.4rem; letter-spacing: -0.02em;'>TATWEER PROPERT QA</h1>
                    <p style='color: {QAConfig.TEXT_LIGHT}; font-size: 1rem; margin: 0;'>Enterprise Quality Assurance Portal</p>
                    <div style="font-size:0.75rem; background:rgba(237,66,36,0.12); color:{QAConfig.PRIMARY_COLOR}; border: 1px solid rgba(237,66,36,0.25); border-radius:12px; padding:2px 8px; display:inline-block; margin-top:8px; font-weight:600;">{APP_VERSION}</div>
                </div>
            """, unsafe_allow_html=True)

            with st.form("login_form", clear_on_submit=True):
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="••••••••")
                if st.form_submit_button("Sign In", use_container_width=True):
                    is_valid, role = AuthManager.authenticate(username, password)
                    if is_valid:
                        t = str(int(time.time()))
                        token = AuthManager.sign_session(username, role)
                        cookie_manager.set("session_token", token, max_age=30*24*60*60, key=f"st_{t}")
                        st.session_state.logged_in = True
                        st.session_state.username  = username
                        st.session_state.role      = role.lower() if role else ""
                        DataManager.log_activity(username, "Logged In")
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Please try again.")


def render_full_report(res: dict):
    """Renders the full AI analysis result in a structured, readable UI."""
    from core import SECTION_MAX

    score       = res.get("Score", 0)
    call_status = res.get("Call_Status", "N/A")
    overall_status = res.get("Overall_Status", "")
    is_pass = "PASS" in str(overall_status).upper() or "PASS" in str(call_status).upper()
    score_color = QAConfig.SUCCESS_COLOR if is_pass else QAConfig.DANGER_COLOR
    status_text = "PASS" if is_pass else "FAIL"
    call_status = "Clean Pass" if is_pass else "Fail"

    if not is_pass:
        auto_fail_reason = res.get("Auto_Fail_Reason", "None")
        root_cause = res.get("Root_Cause_Analysis", "None")
        st.markdown(f"""
            <div style="background: #fff5f5; border: 1.5px solid #ef4444; border-left: 6px solid #ef4444; padding: 16px; margin-bottom: 20px; border-radius: 8px;">
                <div style="display: flex; align-items: flex-start; gap: 12px;">
                    <div style="color: #ef4444; font-size: 1.5rem; line-height: 1;">⚠️</div>
                    <div style="flex: 1;">
                        <div style="font-weight: 700; color: #ef4444; font-size: 0.95rem; margin-bottom: 4px;">CRITICAL AUTO-FAIL VIOLATION DETECTED</div>
                        <div style="font-size: 0.85rem; color: #7f1d1d; margin-bottom: 8px;">
                            <strong>Auto-Fail Reason:</strong> {_e(auto_fail_reason)}
                        </div>
                        <div style="background: rgba(239, 68, 68, 0.05); border-left: 3px solid #ef4444; padding: 10px; border-radius: 4px;">
                            <div style="font-size: 0.78rem; font-weight: 700; color: #ef4444; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.05em;">Root Cause & Evidence</div>
                            <div style="font-size: 0.82rem; color: #1e293b; font-style: italic; line-height: 1.5;">{_e(root_cause)}</div>
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
        <div class="report-section" style="border-left: 5px solid {score_color};">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                <div>
                    <div style="font-size:0.75rem; color:var(--text-light); font-weight:600; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:4px;">Agent</div>
                    <div style="font-size:1.25rem; font-weight:800; color:var(--secondary-color);">{_e(res.get('Agent_Name','N/A'))}</div>
                    <div style="font-size:0.85rem; color:var(--text-light); margin-top:4px;">Patient: <b style="color:var(--secondary-color);">{_e(res.get('Patient_Name','N/A'))}</b> &nbsp;|&nbsp; Phone: <b style="color:var(--secondary-color);">{_e(res.get('Patient_Phone','N/A'))}</b></div>
                </div>
                <div style="text-align:center; min-width:100px;">
                    <div style="font-size:2.8rem; font-weight:900; color:{score_color}; line-height:1; margin-bottom:4px;">{status_text}</div>
                    <div style="padding:4px 14px; border-radius:20px; background:{score_color}18; color:{score_color}; font-weight:700; font-size:0.78rem; display:inline-block;">{_e(call_status)}</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    col_l, col_r = st.columns([1.1, 0.9])

    with col_l:
        st.markdown("##### Summary & Highlights")
        analysis = res.get("Detailed_Analysis", {})
        st.markdown(f"""
            <div class="report-section" style="background:var(--tab-hover-bg); border-left:4px solid var(--secondary-color); padding:16px;">
                <div style="font-weight:700; color:var(--secondary-color); margin-bottom:6px; font-size:0.88rem;">Call Summary</div>
                <div style="color:var(--secondary-color); font-size:0.84rem; line-height:1.7;">{_e(analysis.get('Human_Narrative','N/A'))}</div>
            </div>
        """, unsafe_allow_html=True)

        sc1, sc2 = st.columns(2)
        with sc1:
            strengths = analysis.get("Strengths", [])
            s_html = "".join([f'<div style="padding:6px 0; border-bottom:1px solid var(--border-color); color:var(--text-main); font-size:0.8rem;">{_e(pt)}</div>' for pt in strengths])
            st.markdown(f"""
                <div class="report-section" style="padding:14px; height: 100%;">
                    <div style="font-weight:700; color:{QAConfig.SUCCESS_COLOR}; font-size:0.85rem; margin-bottom:8px;">Key Strengths</div>
                    {s_html or "<em style='color:#94a3b8; font-size:0.8rem;'>No strengths recorded</em>"}
                </div>
            """, unsafe_allow_html=True)
        with sc2:
            weaknesses = analysis.get("Weaknesses", [])
            w_html = "".join([f'<div style="padding:6px 0; border-bottom:1px solid var(--border-color); color:var(--text-main); font-size:0.8rem;">{_e(pt)}</div>' for pt in weaknesses])
            st.markdown(f"""
                <div class="report-section" style="padding:14px; height: 100%;">
                    <div style="font-weight:700; color:{QAConfig.DANGER_COLOR}; font-size:0.85rem; margin-bottom:8px;">Weaknesses</div>
                    {w_html or "<em style='color:#94a3b8; font-size:0.8rem;'>No weaknesses recorded</em>"}
                </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
            <div class="report-section" style="border-left:4px solid {QAConfig.DANGER_COLOR}; padding:16px;">
                <div style="font-weight:700; color:var(--secondary-color); margin-bottom:4px; font-size:0.88rem;">Main Gap Identified</div>
                <div style="color:var(--text-light); font-size:0.84rem; margin-bottom:12px;">{_e(analysis.get('Main_Problem','N/A'))}</div>
                <div style="font-weight:700; color:{QAConfig.PRIMARY_COLOR}; margin-bottom:6px; font-size:0.88rem;">Recommended Coaching Action</div>
                <div style="color:var(--secondary-color); font-size:0.84rem; background:var(--primary-light); padding:10px; border-radius:8px; font-style:italic; line-height:1.6;">{_e(analysis.get('Proposed_Solution','N/A'))}</div>
            </div>
        """, unsafe_allow_html=True)

    with col_r:
        st.markdown("##### Detailed Scoring")
        scoring_data = res.get("Detailed_Scoring", {})
        for cat, data in scoring_data.items():
            res_val = str(data.get("result", "Pass")).strip()
            res_upper = res_val.upper()

            if "PASS" in res_upper:
                badge_bg = '#DEF7EC'
                badge_color = '#03543F'
                badge_text = 'Pass'
            elif "FAIL" in res_upper:
                badge_bg = '#FDE8E8'
                badge_color = '#9B1C1C'
                badge_text = 'Fail'
            else:
                badge_bg = '#E5E7EB'
                badge_color = '#374151'
                badge_text = 'N/A'

            label = cat.replace("_", " ")

            feedback_html = ""
            if data.get('feedback'):
                feedback_html = f'<div style="font-size:0.75rem; color:#475569; margin-top:8px; line-height:1.4; padding-top:8px; border-top:1px dashed #f1f5f9; font-style:italic;">"{_e(data["feedback"])}"</div>'

            st.markdown(f'<div class="report-section" style="padding:12px 14px; margin-bottom:10px;"><div style="display:flex; justify-content:space-between; align-items:center;"><span style="font-weight:600; font-size:0.82rem; color:var(--text-main);">{_e(label)}</span><span style="font-weight:600; font-size:0.75rem; padding:3px 8px; border-radius:12px; background:{badge_bg}; color:{badge_color}; text-transform:uppercase; letter-spacing:0.025em;">{badge_text}</span></div>{feedback_html}</div>', unsafe_allow_html=True)

        st.markdown("##### Compliance Checklist")
        checklist  = res.get("Compliance_Checklist", {})
        items_html = ""
        for key, val in checklist.items():
            label     = key.replace("_", " ")
            val_upper = str(val).strip().upper()
            if val_upper in ("YES", "PASS", "TRUE", ""):
                badge = f'<span class="compliance-yes"> {_e(val)}</span>'
            elif val_upper in ("NO", "FAIL", "FALSE", ""):
                badge = f'<span class="compliance-no"> {_e(val)}</span>'
            else:
                badge = f'<span style="color:var(--text-light); font-weight:600;">{_e(val)}</span>'
            items_html += f'<div class="compliance-item" style="padding:8px 0; font-size:0.8rem;"><span style="color:var(--text-main); font-weight:500;">{_e(label)}</span>{badge}</div>'

        st.markdown(f'<div class="report-section" style="padding:12px 16px;">{items_html}</div>', unsafe_allow_html=True)

        st.markdown("##### Verification Checks")
        verifications = res.get("Verification_Checks", {})
        for vkey, vval in verifications.items():
            status   = vval.get("status", "N/A")
            evidence = vval.get("evidence", "N/A")
            vcolor   = QAConfig.SUCCESS_COLOR if "PASS" in status.upper() else (QAConfig.DANGER_COLOR if "FAIL" in status.upper() else "#f59e0b")
            st.markdown(f"""
                <div class="report-section" style="padding:12px; border-top:3px solid {vcolor}; margin-bottom:10px;">
                    <div style="font-weight:700; color:var(--text-main); font-size:0.8rem; margin-bottom:2px;">{_e(vkey.replace('_',' '))}</div>
                    <div style="font-size:0.78rem; color:{vcolor}; font-weight:600; margin-bottom:4px;">{_e(status)}</div>
                    <div style="font-size:0.74rem; color:var(--text-light); font-style:italic;">"{_e(evidence)}"</div>
                </div>
            """, unsafe_allow_html=True)


def _page_header(title: str, subtitle: str = ""):
    st.markdown(f"""
        <div class="page-header">
            <h2>{title}</h2>
            {"<p>" + subtitle + "</p>" if subtitle else ""}
        </div>
    """, unsafe_allow_html=True)


def page_analysis():
    _page_header("Analysis Stage", "Upload call recordings to start the AI-powered audit process.")

    col1, col2 = st.columns([1.1, 0.9])

    with col1:
        st.markdown("""
            <div class="report-section">
                <h4 style='margin-top: 0; margin-bottom: 12px; font-weight: 700; color: var(--secondary-color);'>Upload New Recordings</h4>
                <p style='font-size: 0.88rem; color: var(--text-light); margin-bottom: 16px;'>Drag and drop your audio files (MP3/WAV) to start the automated evaluation.</p>
            </div>
        """, unsafe_allow_html=True)

        uploaded_files = st.file_uploader("Drop audio files here", type=["mp3", "wav"], accept_multiple_files=True, label_visibility="collapsed")
        if uploaded_files:
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            if st.button("Launch Analysis", use_container_width=True, type="primary"):
                temp_dir = "./temp_uploads"
                os.makedirs(temp_dir, exist_ok=True)
                for file in uploaded_files:
                    with tempfile.NamedTemporaryFile(dir=temp_dir, delete=False, suffix=os.path.splitext(file.name)[1]) as tmp:
                        tmp.write(file.read())
                        tmp_path = tmp.name

                    item_id = DataManager.add_to_queue(file.name)

                    s3_key = None
                    if QAConfig.is_s3_enabled():
                        try:
                            s3_key = f"audios/{item_id}_{file.name}"
                            from storage import S3Manager
                            S3Manager.upload_file(tmp_path, s3_key)
                            with SessionLocal() as db:
                                queue_item = db.query(AnalysisQueue).filter(AnalysisQueue.id == item_id).first()
                                if queue_item:
                                    queue_item.s3_key = s3_key
                                    db.commit()
                        except Exception as s3_err:
                            st.error(f"S3 Upload failed for {file.name}: {s3_err}")
                            DataManager.update_queue_status(item_id, "Failed", error=f"S3 upload failed: {s3_err}")
                            try:
                                os.remove(tmp_path)
                            except OSError:
                                pass
                            continue

                    task_path = s3_key if QAConfig.is_s3_enabled() else tmp_path

                    if os.environ.get("CELERY_BROKER_URL"):
                        try:
                            from tasks import run_analysis_task
                            run_analysis_task.delay(item_id, task_path)
                        except Exception as cel_err:
                            st.warning(f"Celery queueing failed, falling back to local thread executor: {cel_err}")
                            _get_executor().submit(background_analysis, item_id, task_path)
                    else:
                        _get_executor().submit(background_analysis, item_id, task_path)

                    if QAConfig.is_s3_enabled():
                        try:
                            os.remove(tmp_path)
                        except OSError:
                            pass
                st.success(f"{len(uploaded_files)} file(s) queued successfully!")

    with col2:
        st.markdown("<h4 style='margin-top: 0; margin-bottom: 12px; font-weight: 700;'>Processing Queue</h4>", unsafe_allow_html=True)

        col_refresh, col_auto = st.columns([1, 1])
        with col_refresh:
            if st.button("Refresh Queue", use_container_width=True):
                st.rerun()

        auto_refresh = st.toggle("Auto-refresh (5s)", value=False)

        with SessionLocal() as db:
            failures = db.query(AnalysisQueue).filter(AnalysisQueue.status == "Failed").order_by(AnalysisQueue.id.desc()).limit(3).all()
            for f in failures:
                if f.error_msg:
                    st.error(f"**{f.filename}** failed:\n\n{f.error_msg}")

        with SessionLocal() as db:
            queue = db.query(AnalysisQueue).order_by(AnalysisQueue.id.desc()).limit(10).all()

        has_processing = any(item.status == "Processing" for item in queue)

        if not queue:
            st.info("Queue is empty.")
        else:
            for item in queue:
                status_class = f"badge-{item.status.lower()}"
                err_text = ""
                if item.status == "Failed" and item.error_msg:
                    err_text = f"<div style='font-size:0.75rem; color:{QAConfig.DANGER_COLOR}; margin-top:4px;'>{_e(item.error_msg)}</div>"
                st.markdown(f"""
                    <div class="queue-card">
                        <div style="display: flex; justify-content: space-between; align-items: center; gap: 8px;">
                            <span style='font-size:0.88rem; font-weight:600; color:{QAConfig.SECONDARY_COLOR}; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:210px;' title="{_e(item.filename)}">{_e(item.filename)}</span>
                            <span class='badge {status_class}'>{_e(item.status)}</span>
                        </div>
                        {err_text}
                    </div>
                """, unsafe_allow_html=True)

        if auto_refresh and has_processing:
            from streamlit_autorefresh import st_autorefresh
            st_autorefresh(interval=5000, limit=100, key="queue_autorefresh")
        elif auto_refresh and not has_processing:
            st.info("No active processing — auto-refresh paused.")


def page_review():
    _page_header("Review & Audit", "Select a completed report to review, verify, and save to history.")

    if "last_approved_id" in st.session_state:
        last_id = st.session_state.last_approved_id
        with SessionLocal() as db:
            task = db.query(AnalysisQueue).filter(AnalysisQueue.id == last_id).first()
        if task:
            try:
                res = json.loads(task.result_json)
                st.success(f"Report for file '{task.filename}' has been successfully verified and saved!")

                render_full_report(res)

                patient_phone = str(res.get('Patient_Phone', 'Unknown_Phone')).strip()
                import re
                clean_phone = re.sub(r'[^a-zA-Z0-9_\-]', '', patient_phone)
                if not clean_phone:
                    clean_phone = "Unknown_Phone"

                pdf_data = None
                if QAConfig.is_s3_enabled() and task.pdf_url:
                    try:
                        from storage import S3Manager
                        call_id = res.get("Call_ID", "")
                        s3_key = f"reports/Audit_{call_id}.pdf"
                        client = S3Manager.get_client()
                        cfg = QAConfig.get_s3_config()
                        s3_response = client.get_object(Bucket=cfg["bucket"], Key=s3_key)
                        pdf_data = s3_response['Body'].read()
                    except Exception as e:
                        pdf_data = PDFManager.create_full_pdf(res)
                else:
                    pdf_data = PDFManager.create_full_pdf(res)
                st.download_button(
                    "Download Official PDF Report",
                    data=pdf_data,
                    file_name=f"Audit_{clean_phone}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Verify Another Report", use_container_width=True, type="primary"):
                    del st.session_state.last_approved_id
                    st.rerun()
                return
            except Exception as e:
                if "last_approved_id" in st.session_state:
                    del st.session_state.last_approved_id
        else:
            if "last_approved_id" in st.session_state:
                del st.session_state.last_approved_id

    show_verified = st.checkbox("Show already verified reports", value=False)

    with SessionLocal() as db:
        query = db.query(AnalysisQueue.id, AnalysisQueue.filename, AnalysisQueue.created_at).filter(AnalysisQueue.status == "Completed")
        if not show_verified:
            query = query.filter((AnalysisQueue.call_id == None) | (AnalysisQueue.call_id == ""))
        tasks = query.all()

    if not tasks:
        st.info("No completed reports available for review.")
        return

    search_term    = st.text_input("Search by filename", placeholder="Type to filter...")
    filtered_tasks = [t for t in tasks if search_term.lower() in t.filename.lower()] if search_term else tasks

    if not filtered_tasks:
        st.warning("No results match your search.")
        return

    task_df         = pd.DataFrame([{"ID": t.id, "File": t.filename, "Date": t.created_at} for t in filtered_tasks])
    selected_task_id = st.selectbox(
        "Select a report to audit",
        task_df['ID'].tolist(),
        format_func=lambda x: f"{task_df[task_df['ID'] == x]['File'].values[0]}  ({task_df[task_df['ID'] == x]['Date'].values[0]})"
    )

    with SessionLocal() as db:
        task = db.query(AnalysisQueue).filter(AnalysisQueue.id == selected_task_id).first()

    if not task:
        st.error("Task not found.")
        return

    try:
        res = json.loads(task.result_json)
    except (json.JSONDecodeError, TypeError) as e:
        st.error(f"Could not parse report data. It may be corrupted. Error: {e}")
        return

    verified_keys = [k for k in st.session_state if k.startswith("verified_")]
    if len(verified_keys) > 20:
        for old_key in sorted(verified_keys)[:-20]:
            del st.session_state[old_key]

    is_verified = (f"verified_{selected_task_id}" in st.session_state) or (task.call_id is not None and task.call_id != "")

    if not is_verified:
        st.markdown("<h3 style='margin-bottom:18px;'>Audit Verification</h3>", unsafe_allow_html=True)
        col_left, col_right = st.columns([1.1, 0.9])

        with col_left:
            call_status = res.get("Call_Status", "N/A")
            overall_status = res.get("Overall_Status", "")
            is_pass = "PASS" in str(overall_status).upper() or "PASS" in str(call_status).upper()
            score_color = QAConfig.SUCCESS_COLOR if is_pass else QAConfig.DANGER_COLOR
            status_text = "PASS" if is_pass else "FAIL"
            call_status = "Clean Pass" if is_pass else "Fail"

            if not is_pass:
                auto_fail_reason = res.get("Auto_Fail_Reason", "None")
                root_cause = res.get("Root_Cause_Analysis", "None")
                st.markdown(f"""
                    <div style="background: #fff5f5; border: 1.5px solid #ef4444; border-left: 6px solid #ef4444; padding: 16px; margin-bottom: 20px; border-radius: 8px;">
                        <div style="display: flex; align-items: flex-start; gap: 12px;">
                            <div style="color: #ef4444; font-size: 1.5rem; line-height: 1;">⚠️</div>
                            <div style="flex: 1;">
                                <div style="font-weight: 700; color: #ef4444; font-size: 0.95rem; margin-bottom: 4px;">CRITICAL AUTO-FAIL VIOLATION DETECTED</div>
                                <div style="font-size: 0.85rem; color: #7f1d1d; margin-bottom: 8px;">
                                    <strong>Auto-Fail Reason:</strong> {_e(auto_fail_reason)}
                                </div>
                                <div style="background: rgba(239, 68, 68, 0.05); border-left: 3px solid #ef4444; padding: 10px; border-radius: 4px;">
                                    <div style="font-size: 0.78rem; font-weight: 700; color: #ef4444; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.05em;">Root Cause & Evidence</div>
                                    <div style="font-size: 0.82rem; color: #1e293b; font-style: italic; line-height: 1.5;">{_e(root_cause)}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown(f"""
                <div class="report-section" style="border-left: 5px solid {score_color}; padding: 18px 20px; margin-bottom: 20px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <div style="font-size:0.75rem; color:var(--text-light); font-weight:700; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:2px;">Audited Agent</div>
                            <div style="font-size:1.25rem; font-weight:800; color:var(--text-main);">{_e(res.get('Agent_Name','N/A'))}</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:2rem; font-weight:900; color:{score_color}; line-height:1;">{status_text}</div>
                            <div style="padding:2px 8px; border-radius:12px; background:{score_color}15; color:{score_color}; font-weight:700; font-size:0.75rem; display:inline-block; margin-top:4px;">{_e(call_status)}</div>
                        </div>
                    </div>
                    <div style="font-size:0.85rem; color:var(--text-light); border-top:1px solid var(--border-color); padding-top:12px; margin-top:12px; display:flex; justify-content:space-between;">
                        <span>Patient: <b style="color:var(--text-main);">{_e(res.get('Patient_Name','N/A'))}</b></span>
                        <span>Phone: <b style="color:var(--text-main);">{_e(res.get('Patient_Phone','N/A'))}</b></span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            st.markdown("<h5 style='font-weight:700; margin-bottom:10px;'>Summary & Highlights</h5>", unsafe_allow_html=True)
            analysis = res.get("Detailed_Analysis", {})
            st.markdown(f"""
                <div class="report-section" style="background:var(--tab-hover-bg); border-left:4px solid var(--primary-color); padding:18px; margin-bottom:20px;">
                    <div style="font-weight:700; color:var(--text-main); margin-bottom:6px; font-size:0.9rem;">Call Summary</div>
                    <div style="color:var(--text-main); font-size:0.86rem; line-height:1.75;">{_e(analysis.get('Human_Narrative','N/A'))}</div>
                </div>
            """, unsafe_allow_html=True)

            sc1, sc2 = st.columns(2)
            with sc1:
                strengths = analysis.get("Strengths", [])
                s_html = "".join([f'<div style="padding:6px 0; border-bottom:1px solid var(--border-color); color:var(--text-main); font-size:0.8rem;">{_e(pt)}</div>' for pt in strengths])
                st.markdown(f"""
                    <div class="report-section" style="padding:16px; height: 100%;">
                        <div style="font-weight:700; color:{QAConfig.SUCCESS_COLOR}; font-size:0.85rem; margin-bottom:10px;">Key Strengths</div>
                        {s_html or "<em style='color:var(--text-light); font-size:0.8rem;'>No strengths recorded</em>"}
                    </div>
                """, unsafe_allow_html=True)
            with sc2:
                weaknesses = analysis.get("Weaknesses", [])
                w_html = "".join([f'<div style="padding:6px 0; border-bottom:1px solid var(--border-color); color:var(--text-main); font-size:0.8rem;">{_e(pt)}</div>' for pt in weaknesses])
                st.markdown(f"""
                    <div class="report-section" style="padding:16px; height: 100%;">
                        <div style="font-weight:700; color:{QAConfig.DANGER_COLOR}; font-size:0.85rem; margin-bottom:10px;">Weaknesses</div>
                        {w_html or "<em style='color:var(--text-light); font-size:0.8rem;'>No weaknesses recorded</em>"}
                    </div>
                """, unsafe_allow_html=True)

            st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
            st.markdown(f"""
                <div class="report-section" style="border-left:4px solid {QAConfig.DANGER_COLOR}; padding:18px;">
                    <div style="font-weight:700; color:var(--text-main); margin-bottom:6px; font-size:0.9rem;">Main Gap Identified</div>
                    <div style="color:var(--text-light); font-size:0.86rem; margin-bottom:14px;">{_e(analysis.get('Main_Problem','N/A'))}</div>
                    <div style="font-weight:700; color:var(--primary-color); margin-bottom:8px; font-size:0.9rem;">Recommended Coaching Action</div>
                    <div style="color:var(--text-main); font-size:0.86rem; background:var(--primary-light); padding:12px; border-radius:8px; font-style:italic; line-height:1.75;">{_e(analysis.get('Proposed_Solution','N/A'))}</div>
                </div>
            """, unsafe_allow_html=True)

        with col_right:
            st.markdown("<h5 style='font-weight:700; margin-bottom:10px;'>Scorecard Rubrics & Grading</h5>", unsafe_allow_html=True)
            with st.form(f"verify_{selected_task_id}"):
                call_id = st.text_input("Call ID (Required)", placeholder="e.g. CALL-10293")
                agent   = st.text_input("Agent Name", res.get('Agent_Name', ''))

                st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

                st.markdown("<div style='font-size:0.85rem; font-weight:700; margin-bottom:8px; color:var(--text-light);'>Category Scores</div>", unsafe_allow_html=True)
                scoring_data = res.get("Detailed_Scoring", {})
                for cat, data in scoring_data.items():
                    res_val = str(data.get("result", "Pass")).strip()
                    res_upper = res_val.upper()

                    if "PASS" in res_upper:
                        badge_bg = '#DEF7EC'
                        badge_color = '#03543F'
                        badge_text = 'Pass'
                    elif "FAIL" in res_upper:
                        badge_bg = '#FDE8E8'
                        badge_color = '#9B1C1C'
                        badge_text = 'Fail'
                    else:
                        badge_bg = '#E5E7EB'
                        badge_color = '#374151'
                        badge_text = 'N/A'

                    label = cat.replace("_", " ")
                    st.markdown(f'<div style="margin-bottom:8px; border:1px solid var(--border-color); padding:10px; border-radius:8px; background: var(--card-bg); display:flex; justify-content:space-between; align-items:center;"><span style="font-weight:600; font-size:0.8rem; color:var(--text-main);">{_e(label)}</span><span style="font-weight:600; font-size:0.75rem; padding:3px 8px; border-radius:12px; background:{badge_bg}; color:{badge_color}; text-transform:uppercase; letter-spacing:0.025em;">{badge_text}</span></div>', unsafe_allow_html=True)

                st.markdown("<div style='font-size:0.85rem; font-weight:700; margin-top:14px; margin-bottom:8px; color:var(--text-light);'>Compliance Items</div>", unsafe_allow_html=True)
                checklist = res.get("Compliance_Checklist", {})
                for key, val in checklist.items():
                    label = key.replace("_", " ")
                    val_upper = str(val).strip().upper()
                    if val_upper in ("YES", "PASS", "TRUE", ""):
                        badge_html = f'<span style="color:{QAConfig.SUCCESS_COLOR}; font-weight:700; font-size:0.8rem;"> {_e(val)}</span>'
                    elif val_upper in ("NO", "FAIL", "FALSE", ""):
                        badge_html = f'<span style="color:{QAConfig.DANGER_COLOR}; font-weight:700; font-size:0.8rem;"> {_e(val)}</span>'
                    else:
                        badge_html = f'<span style="color:var(--text-light); font-weight:700; font-size:0.8rem;">{_e(val)}</span>'

                    st.markdown(f"""
                        <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid var(--border-color); font-size:0.8rem;">
                            <span style="color:var(--text-main); font-weight:500;">{_e(label)}</span>
                            {badge_html}
                        </div>
                    """, unsafe_allow_html=True)

                st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
                if st.form_submit_button("Approve & Save to History", use_container_width=True):
                    if call_id:
                        res['Call_ID']    = call_id
                        res['Agent_Name'] = agent

                        pdf_url = None
                        if QAConfig.is_s3_enabled():
                            try:
                                pdf_data = PDFManager.create_full_pdf(res)
                                s3_key = f"reports/Audit_{call_id}.pdf"
                                from storage import S3Manager
                                pdf_url = S3Manager.upload_bytes(pdf_data, s3_key, content_type="application/pdf")
                                res['pdf_url'] = pdf_url
                            except Exception as pdf_err:
                                st.warning(f"S3 PDF upload failed: {pdf_err}")

                        DataManager.save_call_to_history(res)
                        DataManager.link_queue_to_call(selected_task_id, call_id, pdf_url=pdf_url)
                        st.session_state[f"verified_{selected_task_id}"] = True
                        st.session_state.last_approved_id = selected_task_id
                        st.rerun()
                    else:
                        st.error("Call ID is required.")
    else:
        st.success("This report has been verified and saved.")
        render_full_report(res)

        patient_phone = str(res.get('Patient_Phone', 'Unknown_Phone')).strip()
        import re
        clean_phone = re.sub(r'[^a-zA-Z0-9_\-]', '', patient_phone)
        if not clean_phone:
            clean_phone = "Unknown_Phone"

        pdf_data = None
        if QAConfig.is_s3_enabled() and task.pdf_url:
            try:
                from storage import S3Manager
                call_id = res.get("Call_ID", "")
                s3_key = f"reports/Audit_{call_id}.pdf"
                client = S3Manager.get_client()
                cfg = QAConfig.get_s3_config()
                s3_response = client.get_object(Bucket=cfg["bucket"], Key=s3_key)
                pdf_data = s3_response['Body'].read()
            except Exception as e:
                pdf_data = PDFManager.create_full_pdf(res)
        else:
            pdf_data = PDFManager.create_full_pdf(res)
        st.download_button(
            "Download Official PDF Report",
            data=pdf_data,
            file_name=f"Audit_{clean_phone}.pdf",
            mime="application/pdf",
            use_container_width=True
        )


def page_dashboard():
    _page_header("Performance Dashboard", "Real-time analytics and agent performance overview.")

    filt_col1, filt_col2, filt_col3 = st.columns([1.2, 1, 1])
    with filt_col1:
        period = st.selectbox(
            "Select Analysis Period",
            ["Today", "Last 7 Days", "Last 30 Days", "Overall Total"],
            index=2,
            key="dashboard_period_selector"
        )

    import datetime
    now = DataManager.get_egypt_time()
    period_start = None
    if period == "Today":
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "Last 7 Days":
        period_start = now - datetime.timedelta(days=7)
    elif period == "Last 30 Days":
        period_start = now - datetime.timedelta(days=30)

    period_start_str = period_start.strftime("%Y-%m-%d %H:%M:%S") if period_start else None

    df_full = DataManager.get_all_history()

    if df_full.empty:
        st.info("No data available to generate analytics.")
        return

    df = df_full.copy()
    if period_start:
        df['timestamp_dt'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df[df['timestamp_dt'] >= period_start]

    if df.empty:
        st.warning(f"No records found for the selected period ({period}).")
        return

    has_transferred = "transferred" in df.columns
    has_sale        = "sale_closed" in df.columns

    pass_count = df[df["status"].str.contains("Pass", case=False, na=False)] if "status" in df.columns else pd.DataFrame()
    pass_rate  = (len(pass_count) / len(df)) * 100 if len(df) > 0 else 0
    transfers  = len(df[df["transferred"].str.upper() == "YES"]) if has_transferred else 0
    sales      = len(df[df["sale_closed"].str.upper() == "YES"]) if has_sale else 0

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)

    c1.markdown(f'<div class="metric-card" style="border-left-color: {QAConfig.SECONDARY_COLOR} !important;"><div class="metric-label">Total Audits</div><div class="metric-value">{len(df)}</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-card" style="border-left-color: {QAConfig.SUCCESS_COLOR} !important;"><div class="metric-label">Sales Closed</div><div class="metric-value">{sales}</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="metric-card" style="border-left-color: #3b82f6 !important;"><div class="metric-label">Pass Rate</div><div class="metric-value">{pass_rate:.1f}%</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="metric-card" style="border-left-color: #8b5cf6 !important;"><div class="metric-label">Transfers</div><div class="metric-value">{transfers}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_left, col_right = st.columns(2)
    with col_left:
        if "status" in df.columns:
            fig_status = px.pie(
                df, names='status', title="Call Status Distribution",
                color_discrete_sequence=[QAConfig.SUCCESS_COLOR, QAConfig.DANGER_COLOR, "#f59e0b", "#6366f1"],
                hole=0.4
            )
            fig_status.update_layout(margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_status, use_container_width=True)

    with col_right:
        if "agent_name" in df.columns and "score" in df.columns:
            agent_perf = df.groupby('agent_name')['score'].mean().reset_index().sort_values('score', ascending=False)
            agent_perf = agent_perf.rename(columns={'score': 'Pass Rate (%)'})
            fig_agent  = px.bar(
                agent_perf, x='agent_name', y='Pass Rate (%)',
                title="Pass Rate by Agent (%)",
                color='Pass Rate (%)', color_continuous_scale='Oranges',
                labels={'Pass Rate (%)': 'Pass Rate (%)'}
            )
            fig_agent.update_layout(margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_agent, use_container_width=True)

    if 'timestamp' in df.columns and not df['timestamp'].isnull().all():
        df['timestamp_dt'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df_sorted = df.dropna(subset=['timestamp_dt']).sort_values('timestamp_dt')
        if not df_sorted.empty:
            df_sorted['Date'] = df_sorted['timestamp_dt'].dt.date
            daily_trend = df_sorted.groupby('Date')['score'].mean().reset_index().rename(columns={'score': 'Pass Rate (%)'})
            
            fig_trend = px.line(
                daily_trend, x='Date', y='Pass Rate (%)',
                title="Daily Pass Rate Trend (%)",
                markers=True, color_discrete_sequence=[QAConfig.PRIMARY_COLOR],
                labels={'Pass Rate (%)': 'Pass Rate (%)'}
            )
            fig_trend.update_layout(
                margin=dict(l=20, r=20, t=40, b=20), 
                paper_bgcolor='rgba(0,0,0,0)'
            )
            fig_trend.update_yaxes(range=[0, 105])
            st.plotly_chart(fig_trend, use_container_width=True)

    try:
        from database import SessionLocal
        with SessionLocal() as db:
            query = db.query(AnalysisQueue.result_json).filter(AnalysisQueue.status == "Completed")
            if period_start_str:
                query = query.filter(AnalysisQueue.created_at >= period_start_str)
            completed_tasks = query.all()

        checklists = []
        for row in completed_tasks:
            if row[0]:
                try:
                    res_dict = json.loads(row[0])
                    chk = res_dict.get("Compliance_Checklist", {})
                    if chk:
                        checklists.append(chk)
                except Exception:
                    pass

        if checklists:
            st.markdown("<h4 style='margin-top:20px; font-weight:700;'>Critical Compliance Checklist Analysis</h4>", unsafe_allow_html=True)
            st.markdown("<p style='font-size:0.9rem; color:#64748b; margin-bottom:16px;'>Compliance rate of critical audit points across all calls:</p>", unsafe_allow_html=True)

            chk_df = pd.DataFrame(checklists)
            items_to_show = {
                "Mentioned_Monthly_Fee": "Mentioned Monthly Fee",
                "Mentioned_Free_Hardware": "Mentioned Free Hardware (Truthfulness)",
                "Got_I_Agree_Statement": "Customer Consent ('I Agree')",
                "Asked_Competitor_Name_Price": "Asked Competitor Name & Price",
                "Device_Exists": "Identified Existing Device"
            }

            cols = st.columns(len(items_to_show))
            for i, (key, label) in enumerate(items_to_show.items()):
                col = cols[i % len(cols)]
                if key in chk_df.columns:
                    values = chk_df[key].astype(str).str.strip().upper().map(lambda x: 1 if x in ("YES", "TRUE", "Y") else 0)
                    rate = values.mean() * 100
                else:
                    rate = 0.0

                color = QAConfig.SUCCESS_COLOR if rate >= 80 else ("#f59e0b" if rate >= 60 else QAConfig.DANGER_COLOR)
                col.markdown(f"""
                    <div class="compliance-metric-card">
                        <div style="font-size: 0.75rem; color:{QAConfig.TEXT_LIGHT}; font-weight:700; text-transform:uppercase; height:36px; display:flex; align-items:center; justify-content:center; line-height:1.2;">{label}</div>
                        <div style="font-size: 1.8rem; font-weight:900; color: {color}; margin-top:8px;">{rate:.1f}%</div>
                    </div>
                """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
    except Exception as chk_err:
        print(f"Compliance dashboard error: {chk_err}")

    st.markdown("<h4 style='margin-top:20px; font-weight:700;'>Agent Leaderboard</h4>", unsafe_allow_html=True)
    if "agent_name" in df.columns and "score" in df.columns:
        agg_dict = {'Pass_Rate': ('score', 'mean'), 'Total_Calls': ('score', 'count')}
        if has_sale:
            agg_dict['Sales_Closed'] = ('sale_closed', lambda x: (x.str.upper() == 'YES').sum())

        leaderboard = df.groupby('agent_name').agg(**agg_dict).reset_index().sort_values('Pass_Rate', ascending=False).reset_index(drop=True)
        leaderboard.index += 1
        leaderboard['Pass_Rate'] = leaderboard['Pass_Rate'].round(1)

        medals = {1: "#1", 2: "#2", 3: "#3"}
        for idx, row in leaderboard.iterrows():
            medal       = medals.get(idx, f"#{idx}")
            score_color = QAConfig.SUCCESS_COLOR if row['Pass_Rate'] >= 80 else ("#f59e0b" if row['Pass_Rate'] >= 70 else QAConfig.DANGER_COLOR)
            sales_info  = f" &nbsp;|&nbsp; {int(row.get('Sales_Closed', 0))} sales" if 'Sales_Closed' in row else ""
            st.markdown(f"""
                <div class="leader-card">
                    <div style="font-size:1.3rem;">{medal}</div>
                    <div style="flex:1; margin-left:14px;">
                        <div style="font-weight:700; color:{QAConfig.SECONDARY_COLOR}; font-size:0.95rem;">{_e(row['agent_name'])}</div>
                        <div style="font-size:0.78rem; color:{QAConfig.TEXT_LIGHT};">{int(row['Total_Calls'])} calls{sales_info}</div>
                    </div>
                    <div style="font-size:1.6rem; font-weight:900; color:{score_color};">{row['Pass_Rate']}%</div>
                </div>
            """, unsafe_allow_html=True)


def page_manage():
    if st.session_state.get("role") not in ("admin", "supervisor"):
        st.error("Access Denied. This page requires Supervisor or Admin role.")
        return
    _page_header("Manage Audit History", "Edit or delete call records. Supervisors can edit; admins can delete.")
    df = DataManager.get_all_history()

    if df.empty:
        st.info("No history found.")
        return

    search = st.text_input("Search by Agent Name or Call ID", placeholder="Type to filter...")
    if search:
        mask = (
            df['agent_name'].str.contains(search, case=False, na=False) |
            df['call_id'].str.contains(search, case=False, na=False)
        )
        df = df[mask]

    if df.empty:
        st.warning("No records match your search.")
        return

    call_id = st.selectbox("Select Call ID to Edit/Delete", df['call_id'].tolist())
    row     = df[df['call_id'] == call_id].iloc[0]

    ALL_STATUSES   = ["Clean Pass", "Pass with Coaching", "Fail - Coaching Required", "Critical Performance Issue", "Fail", "Pass"]
    current_status = row['status']
    status_index   = ALL_STATUSES.index(current_status) if current_status in ALL_STATUSES else 0

    with st.form("edit_form"):
        new_agent  = st.text_input("Agent Name", row['agent_name'])
        new_score  = st.number_input("Score", 0, 100, int(row['score']))
        new_status = st.selectbox("Status", ALL_STATUSES, index=status_index)

        is_admin = st.session_state.role == "admin"
        col1, col2 = st.columns(2)
        if col1.form_submit_button("Update Record", use_container_width=True):
            DataManager.update_call_history(call_id, {"agent_name": new_agent, "score": new_score, "status": new_status})
            st.success("Record updated.")
            st.rerun()
        if is_admin:
            confirm_delete = st.checkbox("Check here to confirm deletion of this record", value=False)
            if col2.form_submit_button("Delete Record", use_container_width=True):
                if confirm_delete:
                    DataManager.delete_call_history(call_id)
                    st.success("Record deleted.")
                    st.rerun()
                else:
                    st.error("You must check the confirmation box before deleting.")
        else:
            col2.info(" Delete — Admin only")

    st.markdown("#### Full History Table")
    st.dataframe(df, use_container_width=True)

    st.markdown("#### Export")
    csv_data = DataManager.get_all_history().to_csv(index=False).encode("utf-8")
    st.download_button("Download All History as CSV", data=csv_data, file_name="audit_history_export.csv", mime="text/csv", use_container_width=True)


def page_logs():
    if st.session_state.get("role") != "admin":
        st.error("Access Denied. Admin only.")
        return
    _page_header("Activity Logs", "Full audit trail of all user actions in the system.")
    st.dataframe(DataManager.get_activity_logs(), use_container_width=True)


def page_usage():
    if st.session_state.get("role") != "admin":
        st.error("Access Denied. Admin only.")
        return
    _page_header("AI Usage & Cost Tracker", "Monitor token consumption and daily/weekly/monthly AI costs.")

    try:
        from database import engine
        from datetime import datetime, timedelta
        with engine.connect() as conn:
            queue_df = pd.read_sql_query("SELECT id, filename, status, created_at, input_tokens, output_tokens, cost FROM analysis_queue WHERE status = 'Completed' ORDER BY created_at DESC", conn)
    except Exception as e:
        st.error(f"Could not load usage data: {e}")
        return

    if queue_df.empty:
        st.info("No completed analysis runs recorded yet.")
        return

    queue_df['created_at'] = pd.to_datetime(queue_df['created_at'])
    queue_df['input_tokens'] = queue_df['input_tokens'].fillna(0).astype(int)
    queue_df['output_tokens'] = queue_df['output_tokens'].fillna(0).astype(int)
    queue_df['cost'] = queue_df['cost'].fillna(0.0).astype(float)

    now = DataManager.get_egypt_time()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    week_start = now - timedelta(days=7)

    month_start = now - timedelta(days=30)

    df_today = queue_df[queue_df['created_at'] >= today_start]
    df_week  = queue_df[queue_df['created_at'] >= week_start]
    df_month = queue_df[queue_df['created_at'] >= month_start]

    metrics = {
        "Today": {
            "cost": df_today['cost'].sum(),
            "input": df_today['input_tokens'].sum(),
            "output": df_today['output_tokens'].sum(),
            "calls": len(df_today)
        },
        "This Week": {
            "cost": df_week['cost'].sum(),
            "input": df_week['input_tokens'].sum(),
            "output": df_week['output_tokens'].sum(),
            "calls": len(df_week)
        },
        "This Month": {
            "cost": df_month['cost'].sum(),
            "input": df_month['input_tokens'].sum(),
            "output": df_month['output_tokens'].sum(),
            "calls": len(df_month)
        },
        "Overall Total": {
            "cost": queue_df['cost'].sum(),
            "input": queue_df['input_tokens'].sum(),
            "output": queue_df['output_tokens'].sum(),
            "calls": len(queue_df)
        }
    }

    tabs = st.tabs(["Today", "This Week (7d)", "This Month (30d)", "Overall Total"])

    for tab, period in zip(tabs, ["Today", "This Week", "This Month", "Overall Total"]):
        with tab:
            data = metrics[period]
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f'''
                <div class="metric-card">
                    <div class="metric-label">Estimated Cost ({period})</div>
                    <div class="metric-value" style="font-size:1.5rem; color:{QAConfig.PRIMARY_COLOR};">${data["cost"]:.4f}</div>
                </div>
            ''', unsafe_allow_html=True)
            c2.markdown(f'''
                <div class="metric-card">
                    <div class="metric-label">Input Tokens</div>
                    <div class="metric-value" style="font-size:1.5rem;">{data["input"]:,}</div>
                </div>
            ''', unsafe_allow_html=True)
            c3.markdown(f'''
                <div class="metric-card">
                    <div class="metric-label">Output Tokens</div>
                    <div class="metric-value" style="font-size:1.5rem;">{data["output"]:,}</div>
                </div>
            ''', unsafe_allow_html=True)
            c4.markdown(f'''
                <div class="metric-card">
                    <div class="metric-label">Total Analyses</div>
                    <div class="metric-value" style="font-size:1.5rem;">{data["calls"]:,}</div>
                </div>
            ''', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    chart_df = queue_df.copy()
    chart_df['date_only'] = chart_df['created_at'].dt.date
    daily_summary = chart_df.groupby('date_only').agg({
        'cost': 'sum',
        'input_tokens': 'sum',
        'output_tokens': 'sum',
        'id': 'count'
    }).reset_index().rename(columns={'id': 'calls'})

    daily_summary = daily_summary.sort_values('date_only')

    fig = px.bar(
        daily_summary, x='date_only', y='cost',
        title="Daily AI Cost (USD)",
        color='cost',
        labels={'date_only': 'Date', 'cost': 'Cost (USD)'},
        color_continuous_scale=[[0, '#fef2f2'], [0.1, '#fee2e2'], [0.5, '#f87171'], [1, '#ed4224']]
    )
    fig.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        coloraxis_showscale=False
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Record-by-Record Usage Log")

    search_query = st.text_input("Search by filename...", "").strip()
    filtered_df = queue_df
    if search_query:
        filtered_df = queue_df[queue_df['filename'].str.contains(search_query, case=False, na=False)]

    display_df = filtered_df.copy()
    display_df['created_at'] = display_df['created_at'].dt.strftime('%Y-%m-%d %H:%M:%S')
    display_df = display_df.rename(columns={
        'id': 'Task ID',
        'filename': 'Audio File Name',
        'created_at': 'Execution Time',
        'input_tokens': 'Input Tokens',
        'output_tokens': 'Output Tokens',
        'cost': 'Cost (USD)'
    })

    st.dataframe(
        display_df[['Task ID', 'Audio File Name', 'Execution Time', 'Input Tokens', 'Output Tokens', 'Cost (USD)']],
        use_container_width=True,
        hide_index=True
    )


def page_settings():
    if str(st.session_state.get("role", "")).lower() not in ("admin", "supervisor"):
        st.error("Access Denied.")
        return
    _page_header("Settings & Profile", "Manage your account settings, user access, and grading rules.")

    from database import SessionLocal, User, AuthManager
    from core import SECTION_MAX

    def render_password_tab():
        with st.form("change_password_form"):
            st.markdown("<h3 style='margin-top:0;'>Change Password</h3>", unsafe_allow_html=True)
            curr_pass = st.text_input("Current Password", type="password", placeholder="••••••••", key="settings_curr_pass")
            new_pass  = st.text_input("New Password", type="password", placeholder="••••••••", key="settings_new_pass")
            conf_pass = st.text_input("Confirm New Password", type="password", placeholder="••••••••", key="settings_conf_pass")

            if st.form_submit_button("Update Password", use_container_width=True):
                if not curr_pass or not new_pass or not conf_pass:
                    st.error("All fields are required.")
                elif new_pass != conf_pass:
                    st.error("New passwords do not match.")
                elif len(new_pass) < 6:
                    st.error("Password must be at least 6 characters long.")
                else:
                    username = st.session_state.username
                    with SessionLocal() as db:
                        user = db.query(User).filter(User.username == username).first()
                        if user and AuthManager.verify_password(curr_pass, user.password_hash):
                            user.password_hash = AuthManager.hash_password(new_pass)
                            db.commit()
                            st.success("Password updated successfully!")
                            DataManager.log_activity(username, "Changed Password")
                        else:
                            st.error("Incorrect current password.")

    def render_users_tab():
        st.markdown("<h4 style='font-weight:700; margin-bottom:12px;'>Current Accounts</h4>", unsafe_allow_html=True)
        with SessionLocal() as db:
            all_users  = db.query(User).all()
            users_data = [{"ID": u.id, "Username": u.username, "Role": u.role.upper()} for u in all_users]

        if users_data:
            for u in users_data:
                role_color = (
                    QAConfig.PRIMARY_COLOR if u["Role"] == "ADMIN"
                    else "#6366f1" if u["Role"] == "SUPERVISOR"
                    else QAConfig.TEXT_LIGHT
                )
                icon = 'A' if u['Role'] == 'ADMIN' else 'S' if u['Role'] == 'SUPERVISOR' else 'U'
                st.markdown(f"""
                    <div class="report-section" style="display:flex; justify-content:space-between; align-items:center; padding:12px 18px; margin-bottom: 8px;">
                        <div style="display:flex; align-items:center; gap:12px;">
                            <div style="width:36px; height:36px; border-radius:50%; background:{role_color}18; display:flex; align-items:center; justify-content:center; font-size:1.1rem;">{icon}</div>
                            <div>
                                <div style="font-weight:700; color:{QAConfig.SECONDARY_COLOR}; font-size:0.95rem;">{_e(u['Username'])}</div>
                                <div style="font-size:0.72rem; padding:2px 8px; border-radius:10px; background:{role_color}15; color:{role_color}; font-weight:600; display:inline-block; margin-top:2px;">{_e(u['Role'])}</div>
                            </div>
                        </div>
                        <div style="font-size:0.78rem; color:{QAConfig.TEXT_LIGHT};">ID #{u['ID']}</div>
                    </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<h4 style='font-weight:700; margin-bottom:12px;'>Add New Account</h4>", unsafe_allow_html=True)
        with st.form("add_user_form"):
            c1, c2   = st.columns(2)
            new_username = c1.text_input("Username", placeholder="e.g. supervisor1", key="add_user_username")
            new_password = c2.text_input("Password", type="password", placeholder="••••••••", key="add_user_password")
            new_role     = st.selectbox("Role", ["user", "supervisor", "admin"],
                                        format_func=lambda r: {"user": "Auditor", "supervisor": "Supervisor", "admin": "Admin"}[r],
                                        key="add_user_role")

            if st.form_submit_button("Create Account", use_container_width=True):
                if not new_username or not new_password:
                    st.error("Username and password are required.")
                else:
                    with SessionLocal() as db:
                        exists = db.query(User).filter(User.username == new_username).first()
                        if exists:
                            st.error(f"Username '{new_username}' already exists.")
                        else:
                            db.add(User(
                                username      = new_username,
                                password_hash = AuthManager.hash_password(new_password),
                                role          = new_role
                            ))
                            db.commit()
                            DataManager.log_activity(st.session_state.username, f"Created user: {new_username} ({new_role})")
                            st.success(f"Account '{new_username}' created successfully!")
                            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<h4 style='font-weight:700; margin-bottom:12px;'>Edit / Delete Account</h4>", unsafe_allow_html=True)
        with SessionLocal() as db:
            all_users_list = db.query(User).all()
            usernames      = [u.username for u in all_users_list]
            user_roles     = {u.username: u.role for u in all_users_list}

        selected_user = st.selectbox("Select account to edit", usernames,
                                      format_func=lambda u: f"{u}  ({user_roles.get(u,'').upper()})",
                                      key="edit_user_select")

        with st.form("edit_user_form"):
            ec1, ec2      = st.columns(2)
            edit_username = ec1.text_input("New Username (leave blank to keep)", placeholder="", key="edit_user_username")
            edit_password = ec2.text_input("New Password (leave blank to keep)", type="password", placeholder="••••••••", key="edit_user_password")
            edit_role     = st.selectbox(
                "Role",
                ["user", "supervisor", "admin"],
                index=["user", "supervisor", "admin"].index(user_roles.get(selected_user, "user")),
                format_func=lambda r: {"user": "Auditor", "supervisor": "Supervisor", "admin": "Admin"}[r],
                key="edit_user_role"
            )

            col_save, col_del = st.columns(2)
            if col_save.form_submit_button("Save Changes", use_container_width=True):
                with SessionLocal() as db:
                    user_obj = db.query(User).filter(User.username == selected_user).first()
                    if user_obj:
                        can_update = True
                        if edit_username.strip():
                            dup = db.query(User).filter(User.username == edit_username.strip()).first()
                            if dup and dup.username != selected_user:
                                st.error(f"Username '{edit_username}' already taken.")
                                can_update = False

                        if can_update:
                            if edit_username.strip():
                                user_obj.username = edit_username.strip()
                            if edit_password.strip():
                                user_obj.password_hash = AuthManager.hash_password(edit_password.strip())
                            user_obj.role = edit_role
                            db.commit()
                            DataManager.log_activity(st.session_state.username, f"Edited user: {selected_user}")
                            st.success("Account updated successfully!")
                            st.rerun()

            if col_del.form_submit_button("Delete Account", use_container_width=True):
                if selected_user == st.session_state.username:
                    st.error("You cannot delete your own account.")
                else:
                    with SessionLocal() as db:
                        user_obj = db.query(User).filter(User.username == selected_user).first()
                        if user_obj:
                            db.delete(user_obj)
                            db.commit()
                            DataManager.log_activity(st.session_state.username, f"Deleted user: {selected_user}")
                            st.success(f"Account '{selected_user}' deleted.")
                            st.rerun()

    def render_prompt_tab():
        from core import OFFICIAL_SCORECARD_PROMPT, SECTION_MAX
        prompt_cfg = DataManager.get_active_prompt_config()
        current_prompt = prompt_cfg.get("prompt_text", "")
        current_weights = prompt_cfg.get("section_max", SECTION_MAX)

        st.markdown("<h4 style='font-weight:700; margin-bottom:8px;'>AI System Prompt Framework</h4>", unsafe_allow_html=True)
        st.info("**Important Note for Supervisors:** The text below is the scorecard and script guidelines that the AI follows to evaluate the call. You can edit, add, or remove rules, script templates, or questions in **plain, natural English**. **You do NOT need to write any code or JSON format; the system parses the data structure automatically.**")

        new_prompt_text = st.text_area("Scorecard Rules & Script (Instructions & Scorecard Guidelines)", current_prompt, height=350, key="settings_prompt_instructions", label_visibility="collapsed")

        st.markdown("<h4 style='font-weight:700; margin-top:20px; margin-bottom:12px;'>Scorecard Category Weights (Max Scores)</h4>", unsafe_allow_html=True)

        new_weights = {}

        st.markdown("<div style='background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 20px; margin-bottom: 20px;'>", unsafe_allow_html=True)
        cols = st.columns(2)
        categories = list(SECTION_MAX.keys())

        for i, cat in enumerate(categories):
            col = cols[i % 2]
            display_name = cat.replace("_", " ")
            current_max = current_weights.get(cat, SECTION_MAX[cat])
            new_max = col.number_input(f"{display_name} (Max)", min_value=1, max_value=100, value=int(current_max), step=1, key=f"settings_weight_{cat}")
            new_weights[cat] = int(new_max)
        st.markdown("</div>", unsafe_allow_html=True)

        if st.button("Save Scorecard Config", use_container_width=True, key="settings_save_config_btn"):
            if DataManager.save_prompt_config(new_prompt_text, new_weights):
                st.success("AI Scorecard configuration updated and saved successfully!")
                DataManager.log_activity(st.session_state.username, "Updated Prompt and Scorecard Weights")
                st.rerun()
            else:
                st.error("Failed to save scorecard configuration to the database.")

        st.markdown("<hr style='margin: 20px 0;'>", unsafe_allow_html=True)
        if st.button("Reset to Default Scorecard & Prompt", use_container_width=True, key="settings_reset_config_btn"):
            from core import OFFICIAL_SCORECARD_PROMPT, SECTION_MAX
            if DataManager.save_prompt_config(OFFICIAL_SCORECARD_PROMPT, SECTION_MAX):
                st.success("Reset to default configuration successfully!")
                DataManager.log_activity(st.session_state.username, "Reset Prompt to Defaults")
                st.rerun()
            else:
                st.error("Failed to reset scorecard configuration.")

    role = str(st.session_state.get("role", "")).lower()
    if role == "admin":
        tab_password, tab_users, tab_prompt = st.tabs([
            "Change Password",
            "User Management",
            "AI Prompt & Rules"
        ])
        with tab_password:
            render_password_tab()
        with tab_users:
            render_users_tab()
        with tab_prompt:
            render_prompt_tab()
    elif role == "supervisor":
        tab_password, tab_prompt = st.tabs([
            "Change Password",
            "AI Prompt & Rules"
        ])
        with tab_password:
            render_password_tab()
        with tab_prompt:
            render_prompt_tab()
    else:
        render_password_tab()


@st.cache_resource
def initialize_database():
    from core import OFFICIAL_SCORECARD_PROMPT, SECTION_MAX
    DataManager.init_db(default_prompt=OFFICIAL_SCORECARD_PROMPT, default_section_max=SECTION_MAX)

def main():
    st.set_page_config(page_title=QAConfig.PAGE_TITLE, page_icon=QAConfig.PAGE_ICON, layout="wide")

    initialize_database()

    cookie_manager = stx.CookieManager()

    api_key = QAConfig.get_api_key()
    if not api_key:
        st.warning("Warning: GOOGLE_API_KEY is not configured. AI analysis features will not work.")

    if 'logged_in' not in st.session_state:
        token = cookie_manager.get("session_token")
        if token:
            cookie_username, cookie_role = AuthManager.verify_session(token)
            if cookie_username and cookie_role:
                _, db_role = AuthManager.authenticate_by_username(cookie_username)
                if db_role == cookie_role:
                    st.session_state.logged_in = True
                    st.session_state.username  = cookie_username
                    st.session_state.role      = cookie_role.lower() if cookie_role else ""
                else:
                    st.session_state.logged_in = False
            else:
                st.session_state.logged_in = False
        else:
            st.session_state.logged_in = False

    ui = UIHandler()
    ui.apply_styles()

    if not st.session_state.logged_in:
        ui.render_login(cookie_manager)
        return

    with st.sidebar:
        logo_base64 = UIHandler.get_base64_image(QAConfig.LOGO_FILE)
        if logo_base64:
            logo_img = f'<img src="data:image/png;base64,{logo_base64}" style="width:90px; margin-bottom:10px;">'
        else:
            logo_img = f'<div style="width:60px; height:60px; background:{QAConfig.PRIMARY_COLOR}; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:1.6rem; margin: 0 auto 10px;">TP</div>'

        st.markdown(f"""
            <div class="sidebar-logo">
                {logo_img}
                <div class="sidebar-brand">TATWEER PROPERT QA</div>
                <div class="sidebar-tagline">Enterprise Audit System</div>
                <div style="font-size:0.75rem; background:rgba(237,66,36,0.12); color:{QAConfig.PRIMARY_COLOR}; border: 1px solid rgba(237,66,36,0.25); border-radius:12px; padding:2px 8px; display:inline-block; margin-top:8px; font-weight:600;">{APP_VERSION}</div>
            </div>
            <hr style="border-color:rgba(255,255,255,0.08); margin: 0 0 12px;">
        """, unsafe_allow_html=True)

        role_icon = {"admin": "A", "supervisor": "S"}.get(st.session_state.role, "U")
        st.markdown(f"""
            <div class="user-pill">
                <span style="font-size:1.2rem;">{role_icon}</span>
                <div>
                    <div class="user-pill-name">{_e(st.session_state.username)}</div>
                    <div class="user-pill-role">{_e(st.session_state.role)}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        pages = {
            "Analysis Stage": "analysis",
            "Review & Audit": "review",
            "Dashboard":      "dashboard",
        }
        role = st.session_state.role
        if role in ("admin", "supervisor"):
            pages["Manage History"] = "manage"
            pages["Settings & Profile"] = "settings"
        if role == "admin":
            pages["Activity Logs"]   = "logs"
            pages["Usage & Cost"]    = "usage"

        selected_label = st.radio("Main Menu", list(pages.keys()), label_visibility="collapsed")
        page_id        = pages[selected_label]

        st.markdown("<br>", unsafe_allow_html=True)

        if QAConfig.is_default_credentials():
            st.warning("Security Alert: Using default passwords or cookie secret! Please configure secrets.toml immediately.")


        if st.button("Logout", use_container_width=True):
            t = str(int(time.time()))
            cookie_manager.delete("session_token", key=f"dt_{t}")
            st.session_state.logged_in = False
            st.rerun()

        st.markdown(f"<div style='text-align:center; opacity:0.3; font-size:0.7rem; margin-top:8px;'>{APP_VERSION}</div>", unsafe_allow_html=True)

    if   page_id == "analysis":  page_analysis()
    elif page_id == "review":    page_review()
    elif page_id == "dashboard": page_dashboard()
    elif page_id == "manage":    page_manage()
    elif page_id == "logs":      page_logs()
    elif page_id == "usage":     page_usage()
    elif page_id == "settings":  page_settings()


if __name__ == "__main__":
    main()
