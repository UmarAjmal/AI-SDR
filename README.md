# Codenter AI SDR Platform

Autonomous, Multi-Tenant AI Sales Development Representative (SDR) Platform engineered strictly according to the **Codenter AI SDR Developer Product Specification** (v1.0) and architectural guidelines.

---

## 🌟 Overview & Architecture

Codenter AI SDR is an enterprise autonomous outbound and inbound sales execution engine built on deterministic safety controls, grounded RAG verification, and real-time deliverability safeguards.

### Core Architectural Pillars
1. **Deterministic Rules > AI Guesswork:**
   - Inbound opt-outs ("unsubscribe", "stop", "remove me") intercepted by **deterministic regex before any LLM call**, achieving strict 100% recall.
   - Hard-coded daily mailbox caps (30–50 sends/day), randomized pacing jitter (120s–300s), and 9 absolute sequence stop conditions.
2. **Strict Grounding & Zero Hallucination:**
   - Bounded prompt context (top 2–3 pgvector chunks, max 3,000 tokens).
   - Structured JSON validation via Pydantic schemas. Every SDR response requires verified source provenance (`source_url`, `extraction_timestamp`).
3. **Multi-Tenant Isolation & Encryption:**
   - Single-tenant DB query enforcement (`workspace_id == current_workspace.id`) derived strictly from verified JWT claims.
   - Provider OAuth secrets encrypted at rest with AES-256-GCM envelope encryption.
4. **14-Intent Inbound Taxonomy:**
   - Multi-class intent classifier (`POSITIVE_INTEREST`, `PRICING`, `PRODUCT_QUESTION`, `OBJECTION`, `REQUEST_INFO`, `NOT_INTERESTED`, `UNSUBSCRIBE`, `WRONG_PERSON`, `REFERRAL`, `TIMING`, `MEETING_REQUEST`, `HUMAN_REQUEST`, `OUT_OF_SCOPE`, `AUTO_REPLY`).
   - Auto-replies permitted only when `confidence >= 0.85` and intent is safe; otherwise routed to the Human-in-the-Loop Inbox.
5. **Apple Frosted Acrylic & Squircle Design Language:**
   - Built with React 18, Vite, and Tailwind CSS.
   - Translucent 3D frosted acrylic layers (`backdrop-blur-xl`, specular top reflections, double glass borders).
   - Dynamic Secondary Accent Engine (Cobalt Blue `#1D4ED8`, Indigo `#4F46E5`, Emerald `#059669`, Violet `#7C3AED`, Amber `#D97706`).
   - Continuous Apple squircle curvature on all interactive surfaces.

---

## 📂 Project Structure

```
├── apps/
│   ├── api/                  # FastAPI REST API (Auth, Leads, Campaigns, Inbox, Calendar, Analytics)
│   ├── worker/               # Celery asynchronous distributed worker tasks
│   └── web/                  # React 18 + Vite + Tailwind CSS Web Dashboard
├── packages/
│   ├── ai/                   # ModelGateway (Claude 3.5 Sonnet / GPT-4o fallback), Agents, Intent Taxonomy
│   ├── analytics/            # Funnel calculation, token cost metering, 5-question audit event stream
│   ├── calendar/             # Timezone-aware slot proposal, 15-min buffers, atomic slot locking
│   ├── campaign/             # Finite state machine, scheduler, business hours, pacing jitter
│   ├── common/               # DB models, Pydantic schemas, AES-256 encryption, Redis distributed locks
│   ├── compliance/           # Deterministic pre-LLM opt-out regex gate, suppression lists
│   ├── crm/                  # Abstract CRM provider interface & HubSpot integration
│   ├── email/                # MIME parsing, quote stripping, double-send protection, mailboxes
│   ├── lead_intelligence/    # 0–100 ICP deterministic scoring, NFAT qualification engine
│   └── website_intelligence/ # Headless Playwright crawler, boilerplate cleaner, pgvector RAG
├── tests/
│   └── unit/                 # 76+ comprehensive async unit & lifecycle tests
├── server.bat                # Windows Batch interactive server control script
├── server.ps1                # PowerShell interactive server control script
├── server.sh                 # Unix/Bash interactive server control script
├── requirements.txt          # Python dependencies
└── pytest.ini                # Pytest configuration
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- PostgreSQL 16 with `pgvector` (or SQLite for local unit testing)
- Redis 7 (for Celery queues and distributed locks)

### 2. Backend Setup
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate    # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env

# Deploy / verify Supabase Schema (PostgreSQL 17 + pgvector + 24 tables)
python infra/setup_supabase.py
```

### 3. Frontend Setup
```bash
cd apps/web
npm install
npm run build    # Verify production compilation
```

### 4. Running the Platform
You can use the interactive server controller script:
* **Windows CMD:** `server.bat`
* **PowerShell:** `.\server.ps1`
* **Linux / macOS / Git Bash:** `./server.sh`

Select Option `[1]` to launch both the FastAPI backend (`http://127.0.0.1:8000`) and the Vite React frontend (`http://localhost:5173`).

---

## 🧪 Testing & Validation

Run the test suite:
```bash
pytest tests/ -v -k "not celery"
```
All 76 lifecycle tests validate deterministic recall, tenant boundary isolation, state transitions, and cryptographic security.
