# 🛡️ Tatweer ProperT QA — Enterprise QA Platform

![Version](https://img.shields.io/badge/version-v1.0.0-orange?style=for-the-badge)
![Python](https://img.shields.io/badge/python-3.11+-blue?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/fastapi-latest-teal?style=for-the-badge)
![Vanilla JS](https://img.shields.io/badge/vanilla_js-HTML5/CSS3-gold?style=for-the-badge)

> AI-powered Quality Assurance platform for auditing call center recordings. Automatically detects campaign types and evaluates agents against specialized rubrics for **Tatweer Misr** (Real Estate Sales & Customer Service) and **Proper T** (Facility Management & Maintenance). Built as a fully standalone Single Page Application.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture & Tech Stack](#architecture--tech-stack)
- [Key Features](#key-features)
- [Project Structure](#project-structure)
- [Installation & Running](#installation--running)
- [Configuration & Secrets](#configuration--secrets)
- [User Roles](#user-roles)
- [Evaluation & Scoring System](#evaluation--scoring-system)
- [Changelog](#changelog)

---

## Overview

Tatweer ProperT QA is an enterprise-grade QA platform that automatically analyzes call center audio recordings using Google's Gemini AI. It identifies the correct campaign (Tatweer Misr or Proper T) and call type, grades agents against an official error-based deductive scorecard, flags critical compliance violations, and provides coaching recommendations — all through a modern web interface.

The application is structured as a **Single Page Application (SPA)** with a vanilla HTML5/CSS3/JS client communicating with a high-performance **FastAPI** backend. All evaluations, history logs, and user credentials are secure and managed via SQLAlchemy.

---

## Architecture & Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | HTML5 / CSS3 / Vanilla Javascript (Single Page Application layout, Chart.js for reports, drag-and-drop file uploads) |
| **Backend Framework** | FastAPI (Python 3.11+) served via Uvicorn |
| **AI Model** | Google Gemini Flash (`models/gemini-2.5-flash`) with structured JSON schema output |
| **Audio Processing** | pydub + ffmpeg |
| **PDF Generation** | reportlab (supports Unicode/Arabic formatting) |
| **Database** | SQLite (default/dev) / PostgreSQL (production) with SQLAlchemy ORM |
| **Auth & Sessions** | Cryptographic HMAC session signing (Zero JWT/OAuth dependency, fast session state) |

---

## Key Features

### 🎧 Web Analysis Stage
- Drag and drop call recordings (MP3/WAV) to launch analysis.
- Live background processing queue with progress badges.
- Powered by **Gemini 2.5 Flash** with structured validation and retries.

### 📜 Side-by-Side Review & Audit
- **Split Screen Layout:**
  - **Left Side:** Audit details, automatic Campaign/Call Type tags, AI-transcribed summary, strengths/weaknesses, and generated coaching scripts.
  - **Right Side:** Grading scorecard with section score indicators, critical compliance checklist status (✅ / ❌), and supervisor approval forms.
- One-click approval and audit history archiving.
- Direct PDF report generation and download.

### 📊 Performance Dashboard
- KPI Blocks: Total Audits, Average Score, FCR Resolved, Pass Rate, and Positive Feedback.
- Interactive charts powered by **Chart.js** (Call Status Distribution, Average Agent Score, Performance Trend).
- Compliance rates for critical checklist items.
- 🏆 Agent Leaderboard with gold, silver, and bronze ranking medals.

### ⚙️ Audit History & Settings
- Fully searchable and editable audit logs (Supervisors/Admins).
- User Management panel (Admin only) to create, edit, and delete system credentials.
- AI System Prompt Framework editor to tune scoring behavior and adjust scorecard category weights.

---

## Project Structure

```
os-precision-audit/
├── backend/            # FastAPI Backend
│   ├── main.py         # REST endpoints & static frontend mount
│   ├── database.py     # Database connection setup (SQLite/Postgres)
│   ├── models.py       # SQLAlchemy database model definitions
│   ├── schemas.py      # Pydantic schemas (FastAPI & Gemini output)
│   ├── services/
│   │   ├── gemini_service.py # Files API uploading, prompting & calculations
│   │   └── pdf_service.py    # English PDF report rendering via xhtml2pdf
│   ├── templates/      # Jinja2 PDF HTML templates
│   └── requirements.txt  # Python requirements
├── frontend/           # React + Vite Frontend
│   ├── src/
│   │   ├── App.jsx     # Main React Dashboard
│   │   ├── main.jsx    # React mounting entrypoint
│   │   ├── index.css   # Main stylesheet (Premium SaaS variables)
│   │   └── App.css     # React layout styles
│   ├── index.html      # HTML entrypoint
│   └── package.json    # Frontend npm dependencies
├── Dockerfile          # Multi-stage Docker build config
├── docker-compose.yml  # Local stack containerization setup
├── package.json        # Concurrent workspace scripts
└── README.md           # This file
```

---

## Installation & Running

### 1. Clone the repository
```bash
git clone https://github.com/Was5em/Tatweer-ProperT-QA.git
cd Tatweer-ProperT-QA
```

### 2. Install system dependencies
Ensure `ffmpeg` is installed for handling audio files (required by pydub):
*   **Linux (Ubuntu/Debian):** `sudo apt update && sudo apt install -y ffmpeg`
*   **macOS (Homebrew):** `brew install ffmpeg`
*   **Windows (Chocolatey):** `choco install ffmpeg`

### 3. Install npm and python dependencies
Run the automated installation script:
```bash
npm run install:all
```
Set up the virtual environment in `backend/` and install requirements:
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate # Linux/macOS
pip install -r requirements.txt
cd ..
```

### 4. Run the Dev Servers
Start both the Vite development server (port 5173) and the FastAPI server (port 5000) concurrently:
```bash
npm run dev
```
Open your browser and navigate to `http://localhost:5173/` to access the portal.

---

## Configuration & Secrets

Secrets and settings are loaded from environment variables (or fallback defaults). Define these in a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_gemini_api_key_here
COOKIE_SIGNING_SECRET=generate_a_long_secure_random_key
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
AUDITOR_USERNAME=auditor1
AUDITOR_PASSWORD=user123

# --- PostgreSQL Connection (Optional / Production) ---
# DB_HOST=localhost
# DB_PORT=5432
# DB_NAME=qa_database
# DB_USER=postgres
# DB_PASSWORD=postgres_password
# OR fallback to a single URL string:
# DATABASE_URL=postgresql://postgres:postgres_password@localhost:5432/qa_database
```

---

## User Roles

| Role | Web View Access | Permissions |
|---|---|---|
| **👤 Auditor (User)** | Analysis, Review, Dashboard | Upload audio, view analysis, view dashboard stats. |
| **👔 Supervisor** | Analysis, Review, Dashboard, History, Settings | Approve audits, edit call histories, edit AI prompts. |
| **🛡️ Admin** | All Views (incl. Logs, Costs, Users) | Full rights, user accounts management, system logs, token usage view. |

---

## Evaluation & Scoring System

Evaluations utilize an **Error-Based Deductive Model** across 8 sections:

1. **Company Image** (Greeting, representing the right company name/project)
2. **Data/System Accuracy** (Correctness in reservation data and complaint logging)
3. **Product Knowledge/Process** (Handling questions, search process, and info correctness)
4. **Professionalism/Etiquette** (Welcome/closing protocol, voice tone, hold/mute/transfer etiquette)
5. **Soft Skills/Behavior** (Interrupting, empathy, apologies, and escalation handling)
6. **Standard Verification** (Collecting and confirming customer details)
7. **Business Requirement/Process** (Adherence to scripts and process consistency)
8. **Violation of Privacy Policies** (Security verification and privacy compliance)

### Grading Calculations
Errors are dynamically mapped to four categories:
*   **Business Critical (BC)**: Binary score (100% if no BC errors, 0% if any error is committed).
*   **End-User Critical (EC)**: Binary score (100% if no EC errors, 0% if any error is committed).
*   **Compliance Critical (CC)**: Binary score (100% if no CC errors, 0% if any error is committed).
*   **Non-Critical (NC)**: Graded score starting at 100%, deducting 12.5% for each NC error: `NC% = max(0, 100 - (NC_errors * 12.5))`.

### Overall Score & Status
*   **Overall Score** is calculated as the average of the categories: `(BC% + EC% + CC% + NC%) / 4`.
*   **Pass**: No critical errors (BC, EC, CC) are committed, and the overall score meets the threshold.
*   **Fail**: Any critical error (BC, EC, or CC) automatically drops the respective category percentage to 0%, resulting in an overall **Fail** status and zeroing the final score.

---

## Changelog

### v1.0.0 (Current Release)
- 🏢 **Multi-Campaign Support:** Adapted the entire platform to evaluate **Tatweer Misr** (Real Estate CS/Sales) and **Proper T** (Facility Management) calls.
- 🗣️ **Auto-Detection:** Gemini automatically identifies the campaign and call type from the audio recording context.
- 📐 **Deductive Scoring Model:** Replaced old criteria with the Error-Based Deductive model using 8 sections and specific error codes (BC, EC, CC, NC).
- 📂 **Frontend Metadatas:** Updated the Single Page Application UI and history tables to dynamically display Campaign, Call Type, FCR, and Customer Feedback metrics.
- 📝 **PDF Reporting Layout:** Refactored ReportLab PDF generation to display campaign parameters, call types, and category percentage scorecards.
