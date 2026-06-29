# 🏛️ Civio (CivicSentinel) — Autonomous Self-Healing Smart City Operations Platform

[![System Engine](https://img.shields.io/badge/Engine-FastAPI-009688.svg?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![AI Orchestrator](https://img.shields.io/badge/Orchestrator-Gemini%202.0%20Flash-4285F4.svg?style=flat-square&logo=google-gemini&logoColor=white)](https://deepmind.google/technologies/gemini)
[![Database](https://img.shields.io/badge/DB-PostgreSQL%20%7C%20Firestore-336791.svg?style=flat-square&logo=postgresql&logoColor=white)](#)
[![Deployment](https://img.shields.io/badge/Deployment-Render%20%7C%20Cloud%20Run-blue.svg?style=flat-square&logo=render&logoColor=white)](#)

> **"A smart city doesn't wait for its citizens to complain; it predicts, triages, dispatches, and heals itself."**

Civio (originally CivicSentinel) is a production-grade, highly consolidated civic infrastructure monitoring and autonomous resolution platform. By collapsing the traditional gap between citizen report ingest and municipal work dispatch, Civio leverages a multi-model Google Cloud stack (Gemini 2.0 Flash, Vertex AI, Firestore) to build a predictive, self-governing urban operating system.

This repository hosts the unified **Single-Engine FastAPI Application**, serving both the high-throughput JSON API endpoints and the tactical, responsive dark-themed Leaflet Command Console directly via dynamic Jinja2 templating.

---

## 🧠 System Architecture & Engine Topologies

Civio is engineered as a zero-human-intervention dispatch pipeline. When a citizen submits a localized photo report, the request flows through a multi-tier verification and agentic resolution gateway:

```
[Citizen Ingest] ➔ [3-Tier Spam Filter] ➔ [pHash Duplicate Check] ➔ [Metadata EXIF Check]
                                                                            │
┌───────────────────────────────◀───────────────────────────────────────────┘
▼
[Gemini Vision Triage] ➔ [SLA Breach Engine] ➔ [Agentic Resolution Loop] ➔ [Auto-Dispatch Work Order]
                                                        │
                                                        ├──➔ [Outbound SMS/WhatsApp Webhook]
                                                        └──➔ [Postgres / Firestore Document Write]
```

### 1. The Autonomous Agentic Resolution Engine
At the core of the platform lies the reasoning loop (`backend/agents/resolution_agent.py`). Powered by **Gemini 2.0 Flash** via function-calling tool binds, the agent executes a structured ReAct (Reasoning and Action) pipeline:
* **Entity Verification:** Queries internal database tables to fetch issue severity and locate geographical ward bounds.
* **Dynamic Department Routing:** Maps the classified category (e.g. `POTHOLE` or `WATER_LEAK`) to its corresponding municipal department (e.g. `Roads & Bridges` or `Water Supply & Sewerage`).
* **Technical Work Order Synthesis:** Generates a structured JSON engineering work order listing required skills, estimated costs, scheduled repair duration, safety hazards, and material requirements.
* **Notification Dispatch:** Triggers an outbound transactional email (via Resend) and a WhatsApp notification (via Twilio) to update stakeholders.
* **Execution SSE Stream:** Streams intermediate reasoning thoughts, tool calls, and execution logs in real-time using Server-Sent Events (SSE).

### 2. Tri-Layer Spam & Abuse Mitigation Pipeline
To defend municipal servers against malicious or synthetic reports, every submission is scrutinized by three independent verification layers before database persistence:
* **Deterministic Keyword Filters:** Flags known abusive terms, automated test scripts, and coordinate-spoofing attempts.
* **Statistical ML Text Classifier:** A local **Scikit-Learn TF-IDF vectorizer + Logistic Regression pipeline** (`train_spam_model.py`) pre-trained on historical datasets to detect marketing spam and off-topic complaints.
* **Generative Fallback Validator:** A Gemini-driven prompt evaluator that reviews context, ensuring that only authentic civic issues proceed.

### 3. Spatial & Media Authenticity Validation
* **EXIF Fingerprint Extraction:** Reads binary image headers to extract camera make, model, shutter speed, and embedded hardware GPS metadata. Reports lacking valid camera device signatures or containing synthetic generator footprints (DALL-E, Midjourney) are automatically rejected.
* **64-bit Perceptual Image Hashing (pHash):** Computes a 64-bit image fingerprint using discrete cosine transform (DCT) frequency distributions. The platform runs a Hamming Distance calculation against active reports within a 50-meter radius to merge duplicate reports.

### 4. Vertex AI Predictive Infrastructure Decay Modeler
Trained on historical maintenance patterns, BBMP ward data, and contractor performance scores, the decay model (`backend/services/vertex_service.py`) calculates a dynamic **Decay Risk Score (10.0–98.5%)** for city zones. Wards are segmented into geographic grids and assigned risk thresholds, allowing municipalities to schedule preventative repairs 30 days before a failure occurs.

---

## 📁 Repository Map

```filepath
Civio/
├── backend/                        # Unified FastAPI Core Package
│   ├── main.py                     # API gateway configuration & CORS/Session middleware
│   ├── seed.py                     # High-fidelity SQLite/Postgres DB seeder (300+ entries)
│   │
│   ├── agents/                     # LLM Reasoning & Triage agents
│   │   ├── resolution_agent.py     # Gemini ReAct loop for automated work order dispatch
│   │   └── triage_agent.py         # Gemini Vision image parsing & severity scoring
│   │
│   ├── database/                   # Database Connectivity Layer
│   │   └── db.py                   # Multi-driver connector (SQLite / Postgres / Firestore)
│   │
│   ├── routers/                    # Endpoint routers grouped by domain
│   │   ├── issues.py               # RESTful CRUD operations, triage, and verification APIs
│   │   ├── intelligence.py         # Decay forecasting, budget simulators, and pattern graphs
│   │   ├── authority.py            # Operations dashboard stats & work order approvals
│   │   ├── gamification.py         # Quests progress tracker, streaks, and leaderboards
│   │   └── legacy.py               # Jinja2 views router (serves HTML templates directly)
│   │
│   ├── templates/                  # Tactical Jinja2 template views (Bootstrap + Leaflet)
│   │   ├── index.html              # Main Citizen dashboard with real-time leaflet map
│   │   ├── gov.html                # Government Dashboard with live SSE Agent Console
│   │   └── ngo_dashboard.html      # NGO coordination portal & recommendations
│   │
│   └── services/                   # Core business logic and validation helpers
│       ├── gemini_service.py       # Google Generative AI bindings
│       ├── vertex_service.py       # Predictive infrastructure decay modeling
│       ├── validation_service.py   # TF-IDF, pHash, EXIF, and cross-modal consistency check
│       └── email_service.py        # Resend SMTP wrapper
│
├── infra/                          # Deployment Configurations
│   ├── Dockerfile                  # Container definition (Python 3.11-slim base)
│   └── cloudbuild.yaml             # Google Cloud Build pipeline setup
│
├── requirements.txt                # Consolidated, production-tested Python dependencies
├── .env.example                    # Template environment file
└── README.md                       # Comprehensive system documentation
```

---

## 🛠️ Deployment & Execution Setup

### Prerequisite Environment Variables
Rename `.env.example` to `.env` in the root directory:
```bash
SECRET_KEY=secure_session_key_here
PORT=5000

# 1. AI API keys
GEMINI_API_KEY=your_gemini_api_key_from_google_ai_studio

# 2. Database Connection (SQLite fallback if blank)
DATABASE_URL=postgresql://user:pass@host:5432/civio_db

# 3. Notification Clients (Optional)
RESEND_API_KEY=your_resend_api_key
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

### Local Setup
1. **Provision virtual environment & install requirements:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. **Execute DB Seeder:**
   ```bash
   python backend/seed.py
   ```
3. **Start Development Server:**
   ```bash
   python backend/main.py
   ```
   * Open `http://localhost:5000/` to access the Citizen Map Console.
   * Open `http://localhost:5000/docs` to test endpoint JSON schemas.

---

## 🌐 Production Deployment Guide (Render Setup)

Since we consolidated the repository into a single-engine FastAPI structure, **Vercel is no longer needed**. The entire application (both backend APIs and HTML Leaflet interfaces) is served directly from the Render container.

### Step 1: Provision Web Service
1. Create a new **Web Service** in your [Render Dashboard](https://dashboard.render.com/).
2. Connect your Git repository.
3. Configure the following service specifications:
   * **Language:** `Python`
   * **Root Directory:** `.` (Leave default/blank)
   * **Build Command:** `pip install -r requirements.txt`
   * **Start Command:** `python backend/seed.py && uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

### Step 2: Environment Setup
Add the required production environment variables under the **Environment** tab:
* `SECRET_KEY` (a secure random string)
* `GEMINI_API_KEY` (from Google AI Studio)
* `DATABASE_URL` (paste your Render PostgreSQL Connection string, or omit to run on ephemeral SQLite)
* Any optional notification keys (`RESEND_API_KEY`, `TWILIO_ACCOUNT_SID`, etc.)

Once saved, Render will build the container, execute the mock seeder, and host your self-healing city operations center live!
