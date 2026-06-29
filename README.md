# 🏛️ Civio & 🌆 AreaPulse — The Dual-Engine Civic Intelligence Ecosystem

> **"Your city, self-healing & hyper-responsive."**  
> Welcome to the unified repository for **Civio (CivicSentinel)** and **AreaPulse**. This monorepo combines two powerful, production-grade civic infrastructure platforms into a single, comprehensive ecosystem. By combining Google-centric predictive and agentic AI (Civio) with a high-throughput Flask, Groq Llama, and PostgreSQL reporting backbone (AreaPulse), this workspace offers a complete suite of tools for citizens, government authorities, and NGOs.

---

## 🌟 The Vision: Agentic, Predictive, and Hyper-Responsive

Modern municipal administration is broken. Traditional complaint portals demand lengthy forms, lack duplicate filtering, and require manual routing, resulting in months of backlog. 

This ecosystem solves these challenges by combining two complementary paradigms:

1. **Civio (Next-Gen Agentic & Predictive Engine):** Focuses on *autonomous self-healing* and *forecasting*. It predicts road and utility decay 30 days before they fail, auto-drafts engineering work orders via Gemini 2.0 Flash function-calling, and flags SLA breaches before they occur.
2. **AreaPulse (High-Performance Map-First Reporting):** Focuses on *5-second reporting* and *high-throughput scale*. It features visual AR-assisted camera scanning using Groq Llama, a Twilio WhatsApp chatbot, and a PostgreSQL-backed spatial index.

---

## 🚀 Combined Core Features

### 🧠 1. Civio (Predictive & Agentic Engine)
* **Agentic Resolution Engine:** An autonomous Gemini 2.0 reasoning loop (`backend/agents/resolution_agent.py`) that uses tools to fetch issue details, verify category-to-department routing, draft technical work orders, schedule repairs, and notify citizens.
* **Vertex AI Decay Forecasting:** Computes dynamic **Decay Risk Scores (10.0–98.5)** for city zones using historical density, unresolved critical issues, contractor failure rates, and road age.
* **CFO Budget Impact Simulator:** An interactive tool demonstrating the cost benefits of immediate action vs. deferred maintenance over a 1-to-12 month horizon, complete with Gemini-generated CFO briefs.
* **SLA Breach Predictor:** Automatically identifies issues that have elapsed 70%+ of their allotted SLA time and escalates them to the chief engineer 48 hours before breach.
* **Neighborhood Pulse Scan:** Mobile-first video patrol triaged in real-time, auto-logging defects from a video stream and awarding citizen XP.

### ⚡ 2. AreaPulse (Map-First Reporting Engine)
* **5-Second AR Cam Reporting:** Point-and-shoot camera capture running on Llama models that auto-detects categories, severities, and coordinates.
* **PostgreSQL Spatial DB:** Implements high-scale concurrent spatial querying using psycopg connection pools.
* **Multi-Channel Workflows:** Dynamic WhatsApp reporting, Map-tap submissions, and a comprehensive government triage queue with live countdown timers.

### 🛡️ 3. Shared AI Security & Verification Pipeline
Both engines leverage shared, multi-layered data validation modules in the workspace:
* **3-Layer Spam Classifier:** A cascade filter consisting of keyword blacklists, a locally trained **Scikit-Learn TF-IDF + Logistic Regression** pipeline, and a Gemini LLM fallback.
* **EXIF Metadata Inspection:** Extracts camera-device and GPS info from images to flag synthetic/AI-generated assets (DALL-E/Midjourney) lacking device metadata.
* **Perceptual Hashing (pHash):** Runs 64-bit image hashing and Hamming distance calculations to merge duplicate photos within a 50-meter radius.

---

## 📊 Dual-Platform Tech Stack

| Component | Civio Stack | AreaPulse Stack | Shared / Synergy |
| :--- | :--- | :--- | :--- |
| **Frontend UI** | Next.js 14 App Router, Tailwind, shadcn/ui | HTML5, Bootstrap, custom Leaflet Maps | Unified styling and local static routes |
| **Backend API** | FastAPI, Pydantic, Server-Sent Events | Flask, Python Session, Gunicorn | Shared local utility scripts |
| **AI Framework** | Gemini 2.0 Flash, Vertex AI | Groq Llama-4-Scout | Custom scikit-learn classifiers |
| **Database** | Firebase Firestore, SQLite | PostgreSQL (psycopg), SQLite | Co-located schema designs |
| **Messaging** | Firebase Cloud Messaging, Twilio | Twilio WhatsApp Webhook | Combined webhook listeners |
| **Storage** | Google Cloud Storage | Local directory / CDN | Shared media encoders |

---

## 🛠️ Combined Architecture Diagram

```mermaid
graph TD
    %% Clients
    subgraph Clients [Frontend Interfaces]
        NextJS["Next.js App (Civio Dashboard)"]
        FlaskUI["Flask Templates (AreaPulse Map)"]
        ARCam["AR Camera Scanner (PWA)"]
    end

    %% Webhook & Routers
    subgraph Gateways [Gateways]
        FastAPIGw["FastAPI Gateway (:8000)"]
        FlaskGw["Flask Web Server (:5000)"]
        Twilio["Twilio WhatsApp API"]
    end

    %% Databases
    subgraph StorageLayer [Data & Storage]
        Firestore["Firestore (Realtime)"]
        Postgres["PostgreSQL DB"]
        SQLiteDB["SQLite (civio.db / Local Fallback)"]
    end

    %% AI Engines
    subgraph AIEngines [AI Engine & Models]
        GeminiEngine["Gemini 2.0 Flash Agent"]
        VertexEngine["Vertex AI Decay Predictor"]
        GroqEngine["Groq Llama-4 Engine"]
        SpamML["Scikit-Learn (spam_clf.pkl)"]
    end

    %% Connections
    NextJS --> FastAPIGw
    FlaskUI --> FlaskGw
    ARCam --> FlaskGw
    Twilio --> FastAPIGw & FlaskGw

    FastAPIGw --> SQLiteDB & Firestore
    FlaskGw --> Postgres & SQLiteDB

    FastAPIGw --> GeminiEngine & VertexEngine & SpamML
    FlaskGw --> GroqEngine & SpamML
```

---

## 📁 Repository Directory Map

```filepath
Civio/
├── backend/                        # Civio FastAPI Backend
│   ├── main.py                     # API gateway containing routers
│   ├── seed.py                     # Demo seeder for 300+ issues & users
│   ├── requirements.txt            # FastAPI python dependencies
│   ├── database/db.py              # Firestore / SQLite interface
│   ├── agents/                     # Gemini Triage & Autonomous Resolution agents
│   └── services/                   # Gemini, Vertex, Maps, and Validation services
│
├── frontend/                       # Civio Next.js 14 Frontend
│   ├── package.json                # Next.js npm dependencies
│   └── src/app/                    # Next.js App routes (NGO, Authority, Pulse Scan, Quests, Map)
│
├── app.py                          # AreaPulse Flask Main Server
├── ai_engine.py                    # AreaPulse Groq Llama Prompts & Pipelines
├── classifier.py                   # AreaPulse Text-to-Severity and Category Classifiers
├── database.py                     # AreaPulse PostgreSQL / SQLite database operations
├── email_sender.py                 # AreaPulse automated municipal email dispatch
├── train_spam_model.py             # Script to train scikit-learn TF-IDF spam models
├── requirements_areapulse.txt      # AreaPulse python dependencies
├── templates/                      # AreaPulse HTML templates
├── models/                         # Trained model artifacts & master datasets
│   └── spam_clf.pkl                # Shared pre-trained Scikit-Learn Spam pipeline
│
└── infra/                          # Docker & Cloud Build configurations
```

---

## 🚀 Setup & Execution Guide

### Prerequisite Environment Variables
Create a `.env` file in the root directory:
```env
# Shared API Keys
GEMINI_API_KEY=your-gemini-key
GROQ_API_KEY=your-groq-key

# Civio (FastAPI + Firestore)
FIREBASE_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# AreaPulse (Flask + PostgreSQL)
DATABASE_URL=postgresql://user:pass@localhost:5432/areapulse
SECRET_KEY=areapulse-dev-secret-2026

# Twilio (WhatsApp & SMS)
TWILIO_ACCOUNT_SID=your-sid
TWILIO_AUTH_TOKEN=your-token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

---

### Running Civio (FastAPI + Next.js)

#### 1. Start the Civio FastAPI Backend
```bash
# Navigate to the backend directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Seed the database with mock issues, users, and quests
python seed.py

# Launch the FastAPI app
python main.py
```
*API docs will be live at `http://localhost:8000/docs`.*

#### 2. Start the Civio Next.js Frontend
```bash
# Navigate to the frontend directory
cd ../frontend

# Install node dependencies
npm install

# Run the dev server
npm run dev
```
*The Civio app will be live at `http://localhost:3000`.*

---

### Running AreaPulse (Flask)

```bash
# Install AreaPulse specific dependencies
pip install -r requirements_areapulse.txt

# (Optional) Re-train the Spam Classification ML pipeline
python train_spam_model.py

# Launch the Flask app
python -m flask run --port=5000
```
*The AreaPulse dashboard will be live at `http://localhost:5000`.*

---

> Combined with 💻, 🤖, and Google Cloud Platform for the future of smart cities.
