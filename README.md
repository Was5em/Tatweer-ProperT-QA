# 🛡️ OS Precision Audit — Enterprise QA Platform

![Version](https://img.shields.io/badge/version-v2.3.2-orange?style=for-the-badge)
![Python](https://img.shields.io/badge/python-3.11+-blue?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/fastapi-latest-teal?style=for-the-badge)
![Vanilla JS](https://img.shields.io/badge/vanilla_js-HTML5/CSS3-gold?style=for-the-badge)

> AI-powered Quality Assurance system for auditing Medical Alert call center recordings. Built for **Assurance Hub Marketing** as a fully standalone, white-labeled Web Application (completely free of Streamlit).

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture & Tech Stack](#architecture--tech-stack)
- [Key Features](#key-features)
- [Project Structure](#project-structure)
- [Installation & Running](#installation--running)
- [Configuration & Secrets](#configuration--secrets)
- [Docker Deployment](#docker-deployment)
- [User Roles](#user-roles)
- [Scoring System](#scoring-system)
- [Changelog](#changelog)

---

## Overview

OS Precision Audit is an enterprise-grade QA platform that automatically analyzes call center audio recordings using Google's Gemini AI. It scores agents against an official 100-point scorecard, generates compliance reports, and provides actionable coaching insights — all in a secure, role-based web interface.

This version has been migrated from Streamlit to a modern **Single Page Application (SPA)** client-server architecture. The frontend is built from scratch with standard web technologies (HTML5, CSS3, Vanilla JS) to replicate the look, feel, and layout of a professional QA audit dashboard, and is served directly by a robust **FastAPI** backend exposing structured SQL database endpoints.

---

## Architecture & Tech Stack

The application is split into two cleanly separated layers served under a single port:

| Layer | Technology |
|---|---|
| **Frontend** | HTML5 / CSS3 / Vanilla Javascript (Single Page Application layout, Chart.js for reports, drag-and-drop file uploads) |
| **Backend Framework** | FastAPI (Python 3.11+) served via Uvicorn |
| **AI Model** | Google Gemini Flash (`models/gemini-2.5-flash`) with structured JSON schema output |
| **Audio Processing** | pydub + ffmpeg |
| **PDF Generation** | reportlab |
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
  - **Left Side:** Audit details, AI-transcribed summary, strengths/weaknesses, and generated coaching scripts.
  - **Right Side:** Grading scorecard with section score progress indicators, critical compliance checklist status (✅ / ❌), and immediate supervisor approval forms.
- One-click approval and audit history archiving.
- Direct PDF report generation and download.

### 📊 Performance Dashboard
- KPI Blocks: Total Audits, Average Score, Sales Closed, Pass Rate, and Transfer Rate.
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
├── api.py           # FastAPI server (REST endpoints, static files mount)
├── core.py          # Gemini AI QA analysis engine, PDF generation (ReportLab)
├── database.py      # SQLAlchemy models, AuthManager, DataManager
├── config.py        # Centralized configurations (branding, AI settings, secrets)
├── requirements.txt # Python package dependencies
├── packages.txt     # System package requirements (ffmpeg)
├── Dockerfile       # Container definition (configured for FastAPI on port 8000)
├── docker-compose.yml # Docker Compose config (Postgres, Redis, Celery, App stack)
├── logo.png         # Brand logo (displayed in sidebar)
├── static/          # Single Page Application assets
│   ├── index.html   # Main SPA HTML structure (Login, Sidebar, Views)
│   ├── style.css    # Modern CSS3 stylesheet (Navy/Red branding)
│   └── app.js       # Client router, fetch handlers, Chart.js setups
└── README.md        # This file
```

---

## Installation & Running

### 1. Clone the repository
```bash
git clone https://github.com/your-org/os-precision-audit.git
cd os-precision-audit
```

### 2. Install system dependencies
Install `ffmpeg` (required for audio processing):
*   **Linux (Ubuntu/Debian):** `sudo apt update && sudo apt install -y ffmpeg`
*   **macOS (Homebrew):** `brew install ffmpeg`
*   **Windows (Chocolatey):** `choco install ffmpeg`

### 3. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Web Server
Launch the FastAPI server using Uvicorn:
```bash
python -m uvicorn api:app --host 127.0.0.1 --port 8000
```
Open your browser and navigate to `http://127.0.0.1:8000/` to access the application.

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

# --- AWS S3 / Cloud Storage (Optional / Production) ---
# AWS_ACCESS_KEY_ID=your_aws_access_key
# AWS_SECRET_ACCESS_KEY=your_aws_secret_key
# AWS_REGION=us-east-1
# AWS_S3_BUCKET=your_s3_bucket_name
# AWS_S3_ENDPOINT_URL=https://endpoint.url (optional for S3-compatible providers)
```

---

## Docker Deployment

To launch the entire stack (FastAPI web server, PostgreSQL database, Redis broker, and Celery background workers) using Docker:

```bash
# Build and launch the containerized application
docker-compose up -d --build
```

The application will build the environment, perform database migrations, and expose the portal on **port 8000** (`http://your-server-ip:8000`).

---

## User Roles

| Role | Web View Access | Permissions |
|---|---|---|
| **👤 Auditor (User)** | Analysis, Review, Dashboard | Upload audio, view analysis, view dashboard stats. |
| **👔 Supervisor** | Analysis, Review, Dashboard, History, Settings | Approve audits, edit call histories, edit AI prompts. |
| **🛡️ Admin** | All Views (incl. Logs, Costs, Users) | Full rights, user accounts management, system logs, token usage view. |

---

## Evaluation System

Evaluation is based on a non-numerical **Pass / Fail / N/A** model across 8 sections.

| Section | Mandatory / Optional | Evaluation Scope |
|---|:---:|---|
| Section 1 - Introduction and Call Purpose | Mandatory | Agent name, company name/safety role, call purpose |
| Section 2 - Current Device / Competitor Handling | Conditional | Competitor verification (N/A if customer has no current device) |
| Section 3 - Product Awareness and Product Knowledge | Mandatory | Emergency assistance purpose (N/A/Pass if customer has prior device) |
| Section 4 - Qualification Questions | Optional | Nice-to-have questions (e.g. living alone, conditions, medications) |
| Section 5 - Pricing Transparency | Mandatory | Monthly fee disclosure ($29-$75 price range) |
| Section 6 - Data Verification | Mandatory | DOB, full shipping address verification |
| Section 7 - Consent and Transfer | Mandatory | Device type discussed, monthly fee recap, clear agreement statement |
| Section 8 - Objections, Questions, and Customer Understanding | Mandatory | Handling customer questions, objections, or confusion |

### Overall Status
*   **Pass**: All mandatory applicable sections pass and no automatic fail conditions are present.
*   **Fail**: Any mandatory section fails or an automatic fail condition is triggered.
*   **Auto-Fail Reason & Root Cause**: On Fail, the AI Auditor documents the reason and provides detailed root cause analysis with exact transcript quotes.

---

## Changelog

### v2.3.2 (Current Release)
- 🩺 **Medical Alert Guidelines Update:** Integrated updated Medical Alert campaign guidelines with critical vs. non-critical classification rules.
- ⚙️ **Programmatic Evaluation Safeguards:** Implemented Python-level programmatic validation for overall pass/fail status calculations, preventing LLM calculation and count errors.
- 📊 **Unified Scorecard Metrics:** Consolidated evaluation outputs mapping overall Pass to 100/Clean Pass and Fail to 0/Fail in database layers for seamless backward compatibility.

### v2.3.1
- ⚙️ **AI Agent Name Precision:** Refined AI agent name extraction prompt rule to restrict role/title extraction (e.g. Medical Alert Specialist) and require actual personal names.
- 🐛 **UI Rendering Fixes:** Corrected UnboundLocalError in Streamlit's `page_review` and resolved indented HTML string rendering blocks within scorecard category views.

### v2.3.0
- 📋 **Pass / Fail / N/A Scorecard:** Replaced the legacy numerical scoring model with a section-by-section Pass/Fail/NA audit framework matching the supervisor's requirements.
- 🎨 **Non-Numerical Reports:** Redesigned PDF report scoreboard and detailed progress cards to display text states instead of scores.
- 🔄 **Compatibility Mapping:** Implemented backend structural conversion from Pass/Fail to legacy metrics to keep the existing historical dashboards fully functional.

### v2.2.0
- 🗄️ **PostgreSQL Support:** Added support for PostgreSQL as a production-grade relational database, enabling high concurrency and scaling. Support is dynamically enabled via environment variables.
- ☁️ **S3 Cloud Storage Migration:** Integrated AWS S3 and S3-compatible object storage (e.g. MinIO, Cloudflare R2) using `boto3` to store uploaded audio files and generated PDF reports, enabling stateless VPS/container hosting.
- 🔒 **Security Upgrades:** Implemented Unix expiration timestamps on session tokens and sanitized HTML-rendered views against Stored XSS.
- 💵 **Cost Logic Centralization:** Consolidated Gemini API pricing calculations under a single central configuration helper.

### v2.1.0
- 🚀 **Streamlit Removal:** Migrated from Streamlit to a standalone FastAPI client-server backend.
- 🎨 **UI Redesign:** Replaced simple layouts with an HTML5/CSS3 Single Page App featuring split-screen audits, custom menus, and dark-navy/orange company color styling.
- 📈 **Chart.js Integration:** Replaced Plotly with client-side Chart.js rendering for responsive statistics.
- 🗄️ **SQL Database Integrations:** Implemented ORM routes for users, prompts, usage logs, queue, and history.
- 🐋 **Docker Alignment:** Updated Dockerfile and docker-compose.yml configurations to map and serve uvicorn on port 8000.
