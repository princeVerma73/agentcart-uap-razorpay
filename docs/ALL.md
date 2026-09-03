# AgentCart — Complete Technical Documentation

> **System Version:** 2.0 (Final Verified Release)  
> **Repository:** `agentcart-uap-razorpay`  
> **Protocol Standard:** Universal Agentic Payments (UAP / AP2) over Razorpay Rails

---

## 1. Project Purpose & Architecture

AgentCart is an autonomous agentic commerce protocol designed to allow AI buyer agents to discover products, negotiate offers, and execute payments within **hard, deterministic financial guardrails** on **Razorpay rails**.

### Core Authority Boundary:
* **LLM (Gemini 2.5 Flash / Heuristic Fallback):** Limited strictly to reasoning, natural language goal parsing, and recommendation explanation. **Zero Financial Authority**.
* **Deterministic Policy Engine (Python):** Enforces spending limits, calculates cart totals from the authoritative SQLite database, generates single-use HMAC-SHA256 tokens for high-value orders, and enforces replay protection.
* **Payment Rails (Razorpay Service):** Creates Razorpay orders, manages checkout modals, and verifies signatures server-side.
* **Audit Ledger (SQLite):** Maintains an immutable, tamper-evident SHA-256 chained event log.

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
│   └── PROJECT_UNDERSTANDING.md    # 26-section study & demo guide
├── README.md                       # Main repository README
└── SUBMISSION_CHECKLIST.md         # Final buildathon submission checklist
```

---

## 3. End-to-End Execution Flow

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

## 4. Three Spending Policies & Limits

1. **Per-Transaction Limit (Default: ₹10,000.00):**
   - Hard cap on single order amount.
   - Breach: Immediately blocks order with `REJECTED_OVER_BUDGET`.
2. **Auto-Approve Ceiling (Default: ₹3,000.00):**
   - Autonomous pre-authorization threshold.
   - Orders $\le$ ₹3,000: Auto-approved autonomously on Razorpay rails.
   - Orders $>$ ₹3,000 and $\le$ ₹10,000: Requires Human-in-the-Loop (HITL) cryptographic approval.
3. **Daily Spending Limit (Default: ₹25,000.00):**
   - Cumulative 24-hour spending budget across all settled transactions today.
   - Breach: Hard block with `REJECTED_OVER_DAILY_BUDGET`.

---

## 5. Verified Demo Scenarios

| Scenario | Goal | Calculation | Policy Gate | Outcome |
| :--- | :--- | :---: | :---: | :--- |
| **1. Autonomous Purchase** | *"Buy 3 HDMI cables for my office"* | $3 \times ₹799 = \mathbf{₹2,397}$ | $\le$ ₹3,000 Ceiling | Settled autonomously, receipt displayed |
| **2. HITL Approval** | *"Purchase 1 Keychron K2 keyboard"* $\rightarrow$ Approve | $1 \times ₹6,499 = \mathbf{₹6,499}$ | ₹3,001–₹10,000 Range | User clicks **"Approve & Settle"** $\rightarrow$ Settled |
| **3. HITL Rejection** | *"Purchase 1 Keychron K2 keyboard"* $\rightarrow$ Reject | $1 \times ₹6,499 = \mathbf{₹6,499}$ | ₹3,001–₹10,000 Range | User clicks **"Reject Proposal"** $\rightarrow$ Halted, 0 capture |
| **4. Hard Policy Block** | *"Buy 13 HDMI cables for my office"* | $13 \times ₹799 = \mathbf{₹10,387}$ | $>$ ₹10,000 Limit | **HARD BLOCK**, 0 payment calls, 0 settlement |
| **5. Cross-Sell Add to Cart** | Add Anker USB-C Hub to HDMI cables | $₹2,397 + ₹2,499 = \mathbf{₹4,896}$ | $>$ ₹3,000 Ceiling | Recalculates total $\rightarrow$ Triggers HITL $\rightarrow$ Settled |
| **6. Order History & Audit** | Click **Order History** tab | N/A | Authoritative List | Shows all transactions; **"View Logs"** links to SHA-256 ledger |
| **7. Voice Input** | Click Mic icon $\rightarrow$ Speak shopping goal | N/A | Speech Recognition | Transcribes into goal box $\rightarrow$ Executes smoothly |

---

## 6. Complete API Endpoints Reference

| Endpoint | Method | Request Payload | Response Schema | Description |
| :--- | :---: | :--- | :--- | :--- |
| `/api/agent/run` | `POST` | `{"goal": str, "session_id": str, "max_budget": float}` | `text/event-stream` (SSE) | Executes live agent purchase pipeline |
| `/api/agent/approve-hitl` | `POST` | `{"session_id": str, "proposal": dict, "verified_total": float, "hitl_token": str}` | `{"status": "SUCCESS", "order": dict, "settlement": dict, "verified_total": float}` | Validates HMAC token and settles order |
| `/api/agent/reject-hitl` | `POST` | `{"session_id": str, "reason": str}` | `{"status": "REJECTED"}` | Records rejection and halts pipeline |
| `/api/policy` | `GET` | None | `{"max_single_transaction_limit": float, "auto_approve_limit": float, "daily_spending_limit": float, "spent_today": float}` | Returns current spending policies & daily spent |
| `/api/policy` | `POST` | `{"max_single_transaction_limit": float, "auto_approve_limit": float, "daily_spending_limit": float, ...}` | Updated Policy Dict | Updates spending policy bounds |
| `/api/orders` | `GET` | None | `{"orders": [{"order_id": str, "session_id": str, "goal": str, "amount": float, "status": str, "payment_id": str, "timestamp": str}]}` | Returns complete order history |
| `/api/catalog` | `GET` | None | `{"products": [Product, ...]}` | Fetches live merchant catalog |
| `/api/growth/interact` | `POST` | `{"session_id": str, "offer_type": str, "action": "accept"|"reject", "product_id": str, ...}` | `{"status": "SUCCESS", "total_amount": float, "verification": dict}` | Processes add-to-cart or decline actions |
| `/api/growth/metrics` | `GET` | None | `{"total_sessions": int, "purchases": int, "conversion_rate": float, "average_order_value": float, "incremental_revenue": float}` | Growth metrics |
| `/api/growth/merchant-analytics` | `GET` | None | `{"gmv": float, "failure_recoveries": int, "hitl_gate_ratio": float}` | Merchant GMV and recovery analytics |
| `/api/audit-logs` | `GET` | Query `?session_id=...` | `{"logs": [{"id": int, "session_id": str, "event_type": str, "status": str, "summary": str, "cryptographic_hash": str, "timestamp": str}]}` | Retrieves SHA-256 audit ledger |

---

## 7. How to Run Locally

### 1. Backend Server Setup & Run
```powershell
# In repository root:
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend UI Setup & Run
```powershell
# In frontend directory:
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

### 3. Automated Test Suite
```powershell
python -m pytest evals/ -v
```

---

## 8. Verified Test & Build Status

* **Backend Test Suite:** `python -m pytest evals/ -v` $\rightarrow$ **88/88 passed (100%) in 12.28s**.
* **Frontend Production Build:** `cd frontend && npm run build` $\rightarrow$ **Success (`✓ built in 4.26s`, 0 errors)**.

---

## 9. FINAL PROJECT STATUS

> **Status:** **FEATURE-COMPLETE & VERIFIED FOR FINAL DEMO**  
> All requirements are implemented, tested, and validated. No further feature development is required.
