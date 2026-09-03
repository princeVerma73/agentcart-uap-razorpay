# AgentCart — Complete Technical Documentation

> **System Version:** 2.0  
> **Repository:** `agentcart-uap-razorpay`  
> **Protocol Standard:** Universal Agentic Payments (UAP / AP2) over Razorpay Rails

---

## 1. Project Purpose & Features

AgentCart is an autonomous commerce protocol designed to allow AI agents to safely transact on digital storefronts while strictly enforcing deterministic security constraints.

### Key Capabilities:
* **Natural Language Goal & Voice Intake:** Accepts natural language shopping prompts via typing or browser speech recognition (`Web Speech API`).
* **Model Context Protocol (MCP) Catalog Tools:** Dynamic product discovery against authoritative SQLite merchant databases.
* **Deterministic Policy Engine:** Server-side enforcement of:
  1. *Per-Transaction Maximum Spending Limit* (e.g. ₹10,000)
  2. *Autonomous Pre-Authorization Ceiling* (e.g. ₹3,000)
  3. *Daily Cumulative Spending Limit* (e.g. ₹25,000)
* **Cryptographic Human-in-the-Loop (HITL) Gate:** HMAC-SHA256 signed single-use approval tokens for high-value orders. Complete approve and reject paths.
* **Merchant Growth Engine:** Grounded upsell upgrades and cross-sell add-ons with automated price recalculation and dynamic policy re-evaluation.
* **Razorpay Payment Rails:** Support for both live Razorpay Test Mode checkout and mock offline sandbox simulation with server-side HMAC-SHA256 verification.
* **Chained SHA-256 Audit Ledger:** Immutable, cryptographically hashed event stream recording every intent, policy check, HITL decision, and settlement.
* **Order History & Tracker:** Tabular view of all past orders, sessions, statuses, payment IDs, and linked cryptographic audit traces.

---

## 2. Directory Structure

```
agentcart-razorpay/
├── backend/
│   ├── main.py                     # FastAPI REST API, SSE streaming, webhook handlers
│   ├── agent/
│   │   ├── buyer_agent.py          # Core agentic pipeline orchestrator
│   │   ├── buyer_intent.py         # Gemini LLM intent parser & regex fallback
│   │   └── tools.py                # MCP catalog search & discovery tools
│   ├── security/
│   │   └── policy_engine.py        # Deterministic spending bounds & HMAC signing
│   ├── merchant/
│   │   ├── catalog.py              # SQLite merchant inventory & chaos injection
│   │   ├── growth_engine.py        # Upsell & cross-sell compatibility graph
│   │   └── analytics.py            # GMV, conversion rates, and growth metrics
│   ├── payments/
│   │   └── razorpay_client.py      # Razorpay order generation & HMAC verification
│   └── audit/
│       └── ledger.py               # Chained SHA-256 SQLite audit ledger
├── frontend/
│   ├── src/
│   │   ├── App.tsx                 # Main React UI with 6 navigation views
│   │   ├── main.tsx                # React entry point
│   │   └── index.css               # Modern styling tokens & animations
│   ├── index.html                  # HTML5 shell & title
│   ├── package.json                # Frontend dependencies (React, Lucide, Tailwind)
│   └── vite.config.ts              # Vite configuration & proxy routes
├── evals/                          # Test suite (88 comprehensive automated tests)
├── docs/
│   ├── ALL.md                      # This comprehensive technical reference
│   └── PROJECT_UNDERSTANDING.md    # 21-section student & demo guide
└── README.md
```

---

## 3. Architecture & Data Flow

```
+-------------------------------------------------------------------------------+
|                               FRONTEND (React + Vite)                         |
|  [Voice / Text Goal] ──► [Live Trace SSE] ──► [HITL Card] ──► [Order History] |
+-------------------------------------------------------------------------------+
                                      │  ▲
                         HTTP / SSE   │  │  JSON Events
                                      ▼  │
+-------------------------------------------------------------------------------+
|                           FASTAPI BACKEND (Python)                            |
|                                                                               |
|   1. BuyerAgent (Orchestration Loop)                                          |
|      ├── BuyerIntent (Gemini 2.5 Flash / Heuristic Fallback)                  |
|      └── MCP Tools (tool_search_catalog, get_product_details)                 |
|                                                                               |
|   2. Merchant Growth Engine (Contextual Upsells & Cross-Sells)                |
|                                                                               |
|   3. Deterministic PolicyEngine                                               |
|      ├── Replay / Idempotency Check (PersistentIdempotencySet)                |
|      ├── Catalog Integrity & DB Price Recalculation                          |
|      ├── Per-Transaction Limit Check (<= max_single_transaction_limit)        |
|      ├── Daily Spending Limit Check (spent_today + total <= daily_limit)      |
|      └── HITL Gate (HMAC-SHA256 Token if total > auto_approve_limit)          |
|                                                                               |
|   4. Razorpay Client (Live Test Mode or Mock Sandbox)                         |
|      ├── Order Creation (POST /orders)                                        |
|      └── Server-side Signature Verification (HMAC-SHA256)                     |
|                                                                               |
|   5. SHA-256 Chained Cryptographic Audit Ledger                               |
+-------------------------------------------------------------------------------+
```

---

## 4. API Endpoints

### Agent Execution
* `POST /api/agent/run`: Starts an autonomous purchasing run. Returns an SSE stream (`text/event-stream`).
  - Request body: `{ "goal": string, "session_id": string, "max_budget": number }`
* `POST /api/agent/approve-hitl`: Submits cryptographic HITL token to approve an order.
  - Request body: `{ "session_id": string, "proposal": object, "verified_total": number, "hitl_token": string }`
* `POST /api/agent/reject-hitl`: Submits user rejection to halt the pipeline.
  - Request body: `{ "session_id": string, "reason": string }`

### Policy & Guardrails
* `GET /api/policy`: Returns current policy bounds and `spent_today`.
* `POST /api/policy`: Updates policy configuration.

### Orders & Tracking
* `GET /api/orders`: Returns list of all order records with IDs, goals, amounts, statuses, payment IDs, and timestamps.

### Growth & Catalog
* `GET /api/catalog`: Returns all catalog products.
* `POST /api/growth/interact`: Handles user acceptance or rejection of upsells/cross-sells.
* `GET /api/growth/metrics`: Returns real-time conversion and growth metrics.
* `GET /api/growth/merchant-analytics`: Returns GMV and recovery analytics.

### Audit & Security
* `GET /api/audit-logs`: Returns historical audit log entries, optionally filtered by `session_id`.

---

## 5. Security & Verification Mechanics

1. **Zero Financial Authority for LLM:** The LLM is used solely for natural language parsing and product matching. Price arithmetic is calculated by backend code from the SQLite DB.
2. **Deterministic Spending Bounds:** Enforced at the policy layer. No transaction can be initiated if it breaches either single-order or cumulative daily limits.
3. **Cryptographic Sign-Off:** HMAC-SHA256 tokens are bound to session, verified total, and cart digest, signed with `HITL_SIGNING_SECRET`.
4. **Idempotency & Anti-Replay:** Prevents double-charging or replayed payloads.
5. **Audit Chain Integrity:** Sequential SHA-256 cryptographic linkage ensures tamper-evidence.

---

## 6. How to Run Locally

### Prerequisites
* Python 3.10+
* Node.js 18+ and npm

### 1. Backend Setup & Startup
```powershell
# In repository root:
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Start FastAPI server on port 8000
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend Setup & Startup
```powershell
# In frontend directory:
cd frontend
npm install
npm run dev
```
Open browser at `http://localhost:5173`.

### 3. Running Automated Tests
```powershell
# Run the complete 88-test validation suite:
python -m pytest evals/ -v
```
