# AgentCart: Complete Project Understanding & Architectural Study Guide

> **Target Audience:** Presenters, Hackathon Evaluators, Interviewers, and Developers.  
> **Project Scope:** Autonomous AI Commerce Protocol with Deterministic Spend Policy Guardrails, Razorpay Rails Integration, and SHA-256 Chained Cryptographic Audit Ledger.

---

## 1. What is AgentCart?

### WHAT IS IT?
**AgentCart** is an autonomous agentic commerce protocol and execution layer. It allows AI buyer agents (such as Google Gemini with heuristic fallbacks) to convert natural language shopping goals into secure, controlled transactions on digital storefronts over **Razorpay rails**.

### WHY DO WE NEED IT?
Normal e-commerce is built for human clicks: a human browses a website, adds items to a cart, checks the total, and enters payment card details.

In **Agentic Commerce**, autonomous software agents make purchases on behalf of humans or enterprises. Giving an AI agent direct, unbounded access to a credit card or payment API is dangerous:
1. **Price Hallucination:** An LLM might hallucinate that a ₹10,000 keyboard costs ₹500 and attempt to buy 20 units.
2. **Prompt Injection & Adversarial Exploits:** Malicious product descriptions or website content can inject hidden prompts instructing the agent to send funds to an unauthorized merchant.
3. **Unbounded Spending Spree:** A runaway automation loop could repeatedly order items and drain corporate treasury.
4. **Lack of Accounting Auditability:** AI non-determinism makes financial reconciliation impossible without cryptographic proofs.

### HOW DOES IT WORK?
AgentCart introduces **Bounded Autonomy with Zero Financial Authority for the AI**:
* The AI agent is restricted to **reasoning** (intent extraction, search, recommendation ranking).
* All prices, math, limits, approvals, and settlements are executed by a **deterministic Python Policy Engine** using authoritative SQLite database records.
* Small purchases ($\le$ ₹3,000) are pre-authorized autonomously.
* High-value purchases (₹3,001 to ₹10,000) trigger a **Human-in-the-Loop (HITL)** cryptographic approval gate.
* Orders exceeding ₹10,000 or the cumulative daily limit of ₹25,000 are **hard-blocked** by the server before any payment rail is touched.
* Every event is linked sequentially into a **tamper-evident SHA-256 audit ledger**.

### WHERE IS IT IMPLEMENTED?
* **Buyer Agent Orchestrator:** [`backend/agent/buyer_agent.py`](file:///c:/INTERNSHIP/agentcart-razorpay/backend/agent/buyer_agent.py)
* **Deterministic Policy Engine:** [`backend/security/policy_engine.py`](file:///c:/INTERNSHIP/agentcart-razorpay/backend/security/policy_engine.py)
* **Authoritative Catalog:** [`backend/merchant/catalog.py`](file:///c:/INTERNSHIP/agentcart-razorpay/backend/merchant/catalog.py)
* **Razorpay Payment Rails:** [`backend/payments/razorpay_client.py`](file:///c:/INTERNSHIP/agentcart-razorpay/backend/payments/razorpay_client.py)
* **Cryptographic Audit Ledger:** [`backend/audit/ledger.py`](file:///c:/INTERNSHIP/agentcart-razorpay/backend/audit/ledger.py)
* **React Dashboard:** [`frontend/src/App.tsx`](file:///c:/INTERNSHIP/agentcart-razorpay/frontend/src/App.tsx)

### WHAT HAPPENS IN THE UI?
The user types or speaks a purchase goal (e.g., *"Buy 3 HDMI cables for my office"*). The UI displays a live Server-Sent Events (SSE) execution stream showing each step: Intent $\rightarrow$ Discovery $\rightarrow$ Recommendation $\rightarrow$ Proposal $\rightarrow$ Policy Check $\rightarrow$ Approval $\rightarrow$ Payment $\rightarrow$ Settlement.

### REAL EXAMPLE
User inputs: `"Buy 3 HDMI cables for my office"`.
Agent finds `"Ultra High Speed 4K@60Hz HDMI 2.1 Braided Cable (2M)"` in the database at ₹799/unit. The server computes $3 \times ₹799 = \mathbf{₹2,397}$. Because ₹2,397 $\le$ ₹3,000, it is auto-approved, a Razorpay order is created, payment is settled, and an SHA-256 audit entry is generated.

---

## 2. Complete End-to-End Flow

```
[User Goal (Voice or Text)]
        │
        ▼
[1. Intent Parsing] (Gemini 2.5 Flash / Heuristic Fallback)
        │
        ▼
[2. Catalog Discovery] (MCP Tools query authoritative SQLite DB)
        │
        ▼
[3. Recommendation & Growth] (Proposes best item + compatible add-ons)
        │
        ▼
[4. Order Proposal Formulation] (Calculates verified total from database unit prices)
        │
        ▼
[5. Policy Engine Verification]
        │
        ├── Exceeds Per-Tx Limit (> ₹10,000) or Daily Limit (> ₹25,000) ──► [HARD BLOCK / REJECTED]
        │
        ├── Exceeds Auto-Approve Ceiling (> ₹3,000)? ─────────────────────► [HITL SIGN-OFF GATE]
        │                                                                           │
        │                                                              ┌────────────┴────────────┐
        │                                                              ▼                         ▼
        │                                                       [User Approves]           [User Rejects]
        │                                                              │                         │
        │                                                              ▼                         ▼
        │                                                     [Razorpay Checkout]      [ORDER REJECTED / HALTED]
        │                                                              │               (Zero Payment / No Capture)
        └── Under Auto-Approve Ceiling (<= ₹3,000)? ───────────────────┤
                                                                       ▼
                                                        [6. Razorpay Order Creation]
                                                                       │
                                                                       ▼
                                                        [7. HMAC-SHA256 Signature Verification]
                                                                       │
                                                                       ▼
                                                        [8. Payment Capture & Settlement]
                                                                       │
                                                                       ▼
                                                        [9. Chained SHA-256 Audit Sealed]
                                                                       │
                                                                       ▼
                                                        [10. Order History Populated]
```

### Stage-by-Stage Breakdown:

| Stage | What Happens | Why It Happens | Component Handling It | User Experience |
| :--- | :--- | :--- | :--- | :--- |
| **1. User Goal** | Natural language text or voice captured | Captures intent without rigid forms | React Frontend (`App.tsx`) | Types in textarea or clicks mic |
| **2. Intent Parsing** | Converts text to structured JSON (query, qty, category) | Machine-readable search parameters | `buyer_intent.py` (Gemini / Heuristic) | Sees "Parsing user goal..." |
| **3. Catalog Discovery** | Queries SQLite inventory for matching products | Retrieves real items, stock, and prices | `tools.py` & `catalog.py` | Sees candidate items discovered |
| **4. Recommendation** | Ranks items and finds compatible attachments | Enhances basket value safely | `growth_engine.py` | Sees chosen item + add-on cards |
| **5. Proposal** | Constructs cart items & calculates exact total | Prevents agent price fabrication | `buyer_agent.py` | Sees itemised proposal & total |
| **6. Policy Check** | Verifies limits, velocity, and replay protection | Guarantees deterministic financial safety | `policy_engine.py` | Sees policy check step |
| **7. Approval Path** | Routes to Auto-Approve, HITL Gate, or Hard Block | Applies correct human oversight level | `policy_engine.py` & `App.tsx` | Green ribbon or Yellow approval card |
| **8. Payment** | Creates Razorpay order & triggers checkout | Interacts with payment rails | `razorpay_client.py` | Sees payment authorization step |
| **9. Settlement** | Verifies HMAC-SHA256 signature server-side | Confirms actual payment capture | `razorpay_client.py` & `main.py` | Sees green verified receipt card |
| **10. Audit Ledger** | Appends SHA-256 chained record to database | Immutable forensic auditability | `ledger.py` | Available in Audit Ledger tab |
| **11. Order History** | Stores order in persistent session tracker | Post-purchase tracking & reconciliation | `main.py` & `App.tsx` | Visible in Order History table |

---

## 3. Intent Parsing

### WHAT IS IT?
Intent parsing converts an unstructured string like `"Buy 3 HDMI cables for my office"` into a structured JSON schema:
```json
{
  "query": "HDMI cable",
  "category": "cables",
  "budget": 3000.0,
  "quantity": 3,
  "required_features": ["4k", "braided"]
}
```

### WHY DO WE NEED IT?
Database queries require specific keywords, quantities, and numeric filters. Without intent decomposition, the database cannot filter items accurately.

### HOW DOES IT WORK?
1. **Primary Route (Google Gemini 2.5 Flash):** Calls Google Gemini using structured prompt templates and response schema parsing in [`backend/agent/buyer_intent.py`](file:///c:/INTERNSHIP/agentcart-razorpay/backend/agent/buyer_intent.py).
2. **Deterministic Heuristic Fallback:** If the Gemini API key is missing, expired, rate-limited, or network fails, the system **automatically falls back** to regex and keyword pattern matching. It extracts quantities (`"3"` $\rightarrow 3$), categories (`"cable"` $\rightarrow$ `cables`), and search terms (`"hdmi"` $\rightarrow `"HDMI cable"`).

### DEMO CONTINUITY BENEFIT
The fallback mechanism ensures that evaluation scenarios and live demos continue uninterrupted without throwing unhandled exceptions.

---

## 4. Catalog Discovery

### WHAT IS IT?
The agent uses Model Context Protocol (MCP) tools to query the merchant's live inventory stored in an SQLite database.

### WHY DO WE NEED IT?
The LLM must **NEVER** invent prices or stock. The database is the single authoritative source of truth.

### REAL CATALOG EXAMPLE
* **Product:** `"Ultra High Speed 4K@60Hz HDMI 2.1 Braided Cable (2M)"`
* **Product ID:** `prod_hdmi_cable_4k`
* **Unit Price:** ₹799.00
* **Stock:** 40 units available
* **Quantity Requested:** 3 units
* **Calculated Total:** $3 \times ₹799.00 = \mathbf{₹2,397.00}$

---

## 5. Product Recommendation

### HOW AGENTCART SELECTS PRODUCTS
The `_pick_best_match` function in [`backend/agent/buyer_agent.py`](file:///c:/INTERNSHIP/agentcart-razorpay/backend/agent/buyer_agent.py) evaluates:
1. **Category Match:** Must match requested category (`cables`).
2. **Stock Availability:** Must have stock $> 0$.
3. **Budget Constraint:** Total price ($unit\_price \times quantity$) must be $\le max\_budget$.
4. **Keyword Relevance:** Prioritizes products matching extracted features (`4k`, `braided`).

### STOCKOUT AUTO-RECOVERY
If the top-ranked item has `stock == 0`:
1. The agent catches the stockout and logs an `ERROR_RECOVERED` event.
2. It executes an autonomous search in the same category for an in-stock alternative.
3. The execution trace displays: `"Stockout Detected -> Autonomous Fallback"`.

---

## 6. Order Proposal

### WHAT IS AN ORDER PROPOSAL?
An internal data structure (`OrderProposal`) containing:
* `session_id`: Unique transaction session identifier.
* `items`: Array of `CartItem` objects with authoritative product ID, quantity, and unit price.
* `total_price`: Total calculated strictly on the backend ($quantity \times unit\_price$).
* `merchant_id`: Verified seller identity.

### ZERO-TRUST PRINCIPLE
The backend **never trusts** the total amount submitted by the client or the AI. The `PolicyEngine` re-fetches each product from the SQLite DB and recalculates the total mathematically.

---

## 7. Three Deterministic Spending Policies

```
+-------------------------------------------------------------------------------+
|                             AGENTCART SPENDING TIERS                          |
|                                                                               |
|   [₹0 ----------- Auto-Approve (₹3,000) ----------- Hard Limit (₹10,000) --]  |
|        Autonomous Execution          HITL Cryptographic Sign-Off       BLOCKED|
+-------------------------------------------------------------------------------+
```

### Policy 1: Auto-Approve Ceiling (Default: ₹3,000.00)
* **WHAT:** Pre-authorization threshold for autonomous execution.
* **WHY:** Routine low-value purchases should not interrupt human operators.
* **HOW:** If $total \le ₹3,000$, `VerificationResult.status = "VALID_AUTONOMOUS"`.
* **EXAMPLE:** 3 HDMI cables @ ₹799 = ₹2,397 ($\le ₹3,000$).
* **RESULT:** Pre-authorized autonomously; payment executes without user prompt.

### Policy 2: Per-Transaction Limit (Default: ₹10,000.00)
* **WHAT:** Hard ceiling on any single order.
* **WHY:** Protects against excessive single-order liability.
* **HOW:** If $total > ₹10,000$, `VerificationResult.status = "REJECTED_OVER_BUDGET"`.
* **EXAMPLE:** 13 HDMI cables @ ₹799 = ₹10,387 ($> ₹10,000$).
* **RESULT:** **HARD BLOCK**; pipeline halts immediately; no payment is initiated.

### Policy 3: Daily Spending Limit (Default: ₹25,000.00)
* **WHAT:** Hard ceiling on cumulative 24-hour spending.
* **WHY:** Prevents runaway agent loops from draining corporate budgets across multiple transactions.
* **HOW:** Sums all settled transactions today via `get_daily_spent()`. If $spent\_today + total > ₹25,000$, returns `REJECTED_OVER_DAILY_BUDGET`.
* **EXAMPLE:** Already spent ₹24,000 today; attempting an order for ₹2,397 ($₹24,000 + ₹2,397 = ₹26,397 > ₹25,000$).
* **RESULT:** **HARD BLOCK**; rejected before payment rails.

---

## 8. Autonomous Purchase Walkthrough

* **Natural Language Goal:** `"Buy 3 HDMI cables for my office"`
* **Item:** `"Ultra High Speed 4K@60Hz HDMI 2.1 Braided Cable (2M)"` @ ₹799
* **Quantity:** 3
* **Calculation:** $3 \times ₹799 = \mathbf{₹2,397.00}$
* **Policy Evaluation:** ₹2,397 $\le$ ₹3,000 Auto-Approve Ceiling.
* **Execution Flow:**
  1. Policy Engine verifies total from database.
  2. Generates Razorpay Order `order_mock_...`.
  3. Authorizes and settles payment.
  4. Seals event in SHA-256 audit ledger.
  5. UI displays green receipt card with Order ID, Payment ID, and Verified Amount: **₹2,397**.

---

## 9. Human-in-the-Loop (HITL) Walkthrough

* **Natural Language Goal:** `"Purchase 1 Keychron K2 mechanical keyboard"`
* **Item:** `"Keychron K2 V2 Wireless Mechanical Keyboard (Gateron Brown)"` @ ₹6,499
* **Calculation:** $1 \times ₹6,499 = \mathbf{₹6,499.00}$
* **Policy Evaluation:** ₹6,499 is above ₹3,000 Auto-Approve Ceiling, but within ₹10,000 hard limit.
* **HITL Token:** Backend issues single-use token: `HMAC-SHA256(secret, session_id:amount:digest:idempotency_key:exp)`.
* **UI Display:** Yellow HITL Sign-off Card displaying verified total: **₹6,499**.

### Branch A: Human Approves
1. User clicks **"Approve & Settle Razorpay"**.
2. Frontend calls `POST /api/agent/approve-hitl` with the cryptographic token.
3. Backend verifies HMAC signature and consumes token (anti-replay).
4. Razorpay order created $\rightarrow$ Payment settled $\rightarrow$ Logged as `HITL_APPROVED`.

### Branch B: Human Rejects
1. User clicks **"Reject Proposal"**.
2. Frontend calls `POST /api/agent/reject-hitl`.
3. Pipeline stops immediately.
4. Execution trace displays `"Human Approval Rejected"`.
5. Status ribbon updates to **"Order Rejected (Approval Declined)"**.
6. Audit ledger logs `HITL_REJECTED`. Zero payment API calls, zero financial capture.

---

## 10. Hard Block Walkthrough

* **Natural Language Goal:** `"Buy 13 HDMI cables for my office"`
* **Item:** `"Ultra High Speed 4K@60Hz HDMI 2.1 Braided Cable (2M)"` @ ₹799
* **Quantity:** 13
* **Calculation:** $13 \times ₹799 = \mathbf{₹10,387.00}$
* **Policy Evaluation:** ₹10,387 exceeds ₹10,000 Per-Transaction Limit.
* **Execution Flow:**
  1. Policy Engine detects limit breach.
  2. Returns `status: "REJECTED_OVER_BUDGET"`.
  3. Execution halts immediately at Policy Check step.
  4. Status ribbon displays **"Policy Ceiling Blocked"**.
  5. **No HITL prompt is shown, no payment is initiated, and no settlement occurs.**

### Policy Spending Tier Comparison:

| Feature | Autonomous Pre-Auth | Human-in-the-Loop (HITL) | Hard Policy Block |
| :--- | :--- | :--- | :--- |
| **Amount Range** | $\le$ ₹3,000.00 | ₹3,000.01 to ₹10,000.00 | $>$ ₹10,000.00 or Daily Breach |
| **Human Action** | None (Zero interruption) | Manual Click (Approve / Reject) | None (Server halts pipeline) |
| **Payment Rail** | Created & Settled automatically | Created upon token verification | **Never Called (0 calls)** |
| **Final Status** | `SUCCESS` / `Settled` | `Settled` (if approved) / `REJECTED` | `REJECTED` / `Blocked` |
| **Real Example** | 3 HDMI Cables (₹2,397) | 1 Keychron Keyboard (₹6,499) | 13 HDMI Cables (₹10,387) |

---

## 11. Daily Spending Limit & Cumulative Tracking

### HOW IT WORKS
1. Whenever an order settles (`PAYMENT_CAPTURED` or `PAYMENT_VERIFIED`), the amount is stored in the audit ledger.
2. When a new proposal arrives, [`policy_engine.get_daily_spent()`](file:///c:/INTERNSHIP/agentcart-razorpay/backend/security/policy_engine.py) queries SQLite for all successful payments created during today's calendar date.
3. If $spent\_today + proposed\_total > ₹25,000.00$, the transaction is blocked with:
   `"Order amount (₹X) + today's spending (₹Y) exceeds the daily spending limit of ₹25,000.00"`

### CUMULATIVE EXAMPLE:
* Transaction 1: ₹2,397 (Settled $\rightarrow$ spent today = ₹2,397)
* Transaction 2: ₹6,499 (Settled $\rightarrow$ spent today = ₹8,896)
* Transaction 3: ₹8,995 (Settled $\rightarrow$ spent today = ₹17,891)
* Transaction 4: ₹8,000 ($₹17,891 + ₹8,000 = \mathbf{₹25,891} > ₹25,000$) $\rightarrow$ **HARD BLOCK**.

---

## 12. Razorpay Payment Rails & Demo Mode

### WHAT DOES RAZORPAY DO?
* Generates authoritative Razorpay Orders (`POST /orders`).
* Manages standard Checkout Modal (in live test mode).
* Provides server-side HMAC-SHA256 signature verification.

### DEMO / MOCK vs. PRODUCTION
* **Mock Sandbox Mode (`RAZORPAY_MOCK_MODE=true`):** Used during testing and standard offline demos. Simulates Razorpay order creation (`order_mock_...`) and payment signatures locally without needing external internet access.
* **Live Test Mode (`RAZORPAY_MOCK_MODE=false`):** When official Razorpay test keys (`rzp_test_...`) are provided in `.env`, AgentCart connects to Razorpay's Test API and opens the official Checkout modal.
* **Production Boundary:** AgentCart enforces server-side HMAC signature verification. Client callbacks are never trusted as proof of payment.

---

## 13. Authoritative Verified Amount Display

### THE RULE
The "Verified Amount" displayed in the final receipt card is **never hardcoded**. It is extracted authoritatively from:
1. `step.data.verified_total` (recalculated from SQLite database unit prices)
2. `step.data.order.amount / 100` (Razorpay order amount in rupees)
3. `step.data.settlement.amount` (verified settlement record)

### FINAL RECEIPT DATA FIELDS:
* **Product Name:** `"Ultra High Speed 4K@60Hz HDMI 2.1 Braided Cable (2M)"`
* **Quantity:** 3
* **Unit Price:** ₹799.00
* **Verified Total:** ₹2,397.00
* **Razorpay Order ID:** `order_mock_...`
* **Payment ID:** `pay_mock_...`

---

## 14. Voice Input Integration

### WHAT IS IT?
Allows users to speak shopping goals instead of typing.

### HOW IT WORKS:
1. Uses the browser's built-in **Web Speech API** (`window.SpeechRecognition` / `webkitSpeechRecognition`).
2. Clicking the microphone button changes its state to a pulsing red `"Listening..."` indicator.
3. Spoken audio is transcribed into text in real time.
4. The transcript automatically populates the Natural Language Goal textarea.
5. The user can review, edit, or immediately click **"Execute Autonomous Purchase"**.
6. If microphone permission is denied, a non-intrusive notification appears, and standard typing remains functional.

---

## 15. Cross-Sell & Upsell ("Add to Cart")

### HOW IT WORKS:
* **Recommendation:** The Growth Engine checks category compatibility graphs (e.g., HDMI Cable $\rightarrow$ Anker 7-in-1 USB-C Hub @ ₹2,499).
* **"Add to Cart" Action:**
  1. Adds the accessory to the order proposal.
  2. Recalculates the combined total: $₹2,397 + ₹2,499 = \mathbf{₹4,896.00}$.
  3. Re-runs Policy Engine verification.
  4. Because ₹4,896 $> ₹3,000$, it dynamically triggers the **Human-in-the-Loop (HITL)** gate.
  5. Spending policies cannot be bypassed.
* **"Decline" Action:** Records the preference and keeps the original base order unchanged.

---

## 16. Order History & Tracker

### WHAT IS IT?
A dedicated view in the **Order History** tab that maintains an authoritative record of all purchases.

### TABLE FIELDS:
* **Order ID:** `order_mock_...`
* **Session ID:** `sess_...`
* **Goal Intent:** Natural language query entered by user.
* **Amount:** Authoritative settled amount (₹).
* **Status:** `Settled` (green badge), `Rejected` (rose badge), `Pending Approval` (amber badge).
* **Payment ID:** `pay_mock_...`
* **Timestamp:** Date and time of execution.
* **Audit Trail Link:** Clicking **"View Logs"** opens the Audit Ledger view filtered to that exact session.

---

## 17. Cryptographic SHA-256 Audit Ledger

### WHAT IS IT?
An immutable event log where every step is cryptographically linked using SHA-256 hashing.

### HOW CHAINING WORKS:
* **Event 1 (Goal Intake):** $\text{Hash}_1 = \text{SHA-256}(\text{"GENESIS"} : \text{Event}_1)$
* **Event 2 (Policy Check):** $\text{Hash}_2 = \text{SHA-256}(\text{Hash}_1 : \text{Event}_2)$
* **Event 3 (Payment Settled):** $\text{Hash}_3 = \text{SHA-256}(\text{Hash}_2 : \text{Event}_3)$

### TAMPER EVIDENCE:
If an attacker modifies the amount or details of Event 1 in the SQLite database:
1. The recalculated hash for Event 1 changes.
2. The mismatch invalidates $\text{Hash}_2$, breaking the entire chain downstream.
3. `ledger.verify_chain_integrity()` immediately detects the tampering.

---

## 18. Security Architecture & Invariants

1. **Zero Financial Authority for LLMs:** LLMs cannot set prices, approve payments, or bypass limits.
2. **Deterministic Spending Bounds:** Enforced in pure Python at the policy layer.
3. **HMAC-SHA256 Signed HITL Tokens:** Bound to session, verified total, and cart digest, signed with server secret.
4. **Anti-Replay Protection:** Tokens and idempotency keys are consumed upon first use.
5. **Authoritative Database Math:** Price arithmetic is calculated directly from SQLite records.

---

## 19. Important Files Reference

| File Path | Purpose | Why It Matters |
| :--- | :--- | :--- |
| [`frontend/src/App.tsx`](file:///c:/INTERNSHIP/agentcart-razorpay/frontend/src/App.tsx) | Main React Application | Contains all 6 navigation tabs, voice input, SSE trace, HITL sign-off card, receipt cards, and policy controls. |
| [`backend/main.py`](file:///c:/INTERNSHIP/agentcart-razorpay/backend/main.py) | FastAPI REST & SSE Router | Defines endpoints for agent execution, HITL approve/reject, order history, and policy updates. |
| [`backend/security/policy_engine.py`](file:///c:/INTERNSHIP/agentcart-razorpay/backend/security/policy_engine.py) | Deterministic Policy Engine | Enforces 3 spending limits, checks daily velocity, signs/verifies HMAC tokens, and prevents replay attacks. |
| [`backend/agent/buyer_agent.py`](file:///c:/INTERNSHIP/agentcart-razorpay/backend/agent/buyer_agent.py) | Agentic Loop Orchestrator | Coordinates intent intake, catalog discovery, proposal creation, and payment execution. |
| [`backend/agent/buyer_intent.py`](file:///c:/INTERNSHIP/agentcart-razorpay/backend/agent/buyer_intent.py) | Intent Parser | Gemini LLM structured parsing with deterministic heuristic regex fallback. |
| [`backend/agent/tools.py`](file:///c:/INTERNSHIP/agentcart-razorpay/backend/agent/tools.py) | MCP Catalog Tools | Exposes catalog search and product detail retrieval functions to the agent. |
| [`backend/merchant/catalog.py`](file:///c:/INTERNSHIP/agentcart-razorpay/backend/merchant/catalog.py) | Merchant Inventory DB | Authoritative SQLite database of products with price, stock, specs, and chaos simulators. |
| [`backend/merchant/growth_engine.py`](file:///c:/INTERNSHIP/agentcart-razorpay/backend/merchant/growth_engine.py) | Merchant Growth Engine | Evaluates category compatibility graphs for contextual upsells and cross-sells. |
| [`backend/payments/razorpay_client.py`](file:///c:/INTERNSHIP/agentcart-razorpay/backend/payments/razorpay_client.py) | Razorpay Rails Client | Creates Razorpay orders, verifies HMAC-SHA256 signatures, and provides mock sandbox flow. |
| [`backend/audit/ledger.py`](file:///c:/INTERNSHIP/agentcart-razorpay/backend/audit/ledger.py) | SHA-256 Audit Ledger | Implements tamper-evident cryptographic hash chaining in SQLite. |

---

## 20. API Endpoints

| Endpoint | Method | Purpose | Input Payload | Output Response |
| :--- | :---: | :--- | :--- | :--- |
| `/api/agent/run` | `POST` | Executes purchasing pipeline | `{ "goal": string, "session_id": string, "max_budget": number }` | SSE Stream (`text/event-stream`) |
| `/api/agent/approve-hitl` | `POST` | Submits HITL approval token | `{ "session_id": string, "proposal": object, "verified_total": number, "hitl_token": string }` | `{ "status": "SUCCESS", "order": object, "settlement": object, "verified_total": number }` |
| `/api/agent/reject-hitl` | `POST` | Submits HITL rejection | `{ "session_id": string, "reason": string }` | `{ "status": "REJECTED" }` |
| `/api/policy` | `GET` | Fetches policy bounds & daily spent | None | `{ "max_single_transaction_limit": 10000, "auto_approve_limit": 3000, "daily_spending_limit": 25000, "spent_today": number }` |
| `/api/policy` | `POST` | Updates policy limits | `{ "auto_approve_limit": number, ... }` | Updated Policy Object |
| `/api/orders` | `GET` | Fetches order history | None | `{ "orders": [OrderRecord, ...] }` |
| `/api/growth/interact` | `POST` | Accepts or declines add-ons | `{ "session_id": string, "offer_type": string, "action": "accept"|"reject", "product_id": string, ... }` | `{ "status": "SUCCESS", "total_amount": number, "verification": object }` |
| `/api/audit-logs` | `GET` | Fetches cryptographic logs | Query param: `?session_id=...` | `{ "logs": [AuditLogEntry, ...] }` |

---

## 21. Complete Demo Scenarios

| Scenario | Goal & Input | Calculated Amount | Policy Gate Decision | Expected Outcome |
| :--- | :--- | :---: | :---: | :--- |
| **1. Autonomous Purchase** | `"Buy 3 HDMI cables for my office"` | $3 \times ₹799 = \mathbf{₹2,397}$ | $\le$ ₹3,000 Auto-Approve Ceiling | Settled autonomously on Razorpay rails |
| **2. HITL Approval** | `"Purchase 1 Keychron K2 keyboard"` | $1 \times ₹6,499 = \mathbf{₹6,499}$ | ₹3,001–₹10,000 Range | User clicks **"Approve & Settle"** $\rightarrow$ Settled |
| **3. HITL Rejection** | `"Purchase 1 Keychron K2 keyboard"` | $1 \times ₹6,499 = \mathbf{₹6,499}$ | ₹3,001–₹10,000 Range | User clicks **"Reject Proposal"** $\rightarrow$ Halted immediately |
| **4. Hard Policy Block** | `"Buy 13 HDMI cables for my office"` | $13 \times ₹799 = \mathbf{₹10,387}$ | $>$ ₹10,000 Limit | **HARD BLOCK**, 0 payment calls, 0 settlement |
| **5. Cross-Sell Add to Cart** | Add Anker USB-C Hub to HDMI cables | $₹2,397 + ₹2,499 = \mathbf{₹4,896}$ | $>$ ₹3,000 Ceiling | Recalculates total $\rightarrow$ Triggers HITL $\rightarrow$ Settled |
| **6. Order History & Audit** | Click **Order History** tab | N/A | Authoritative List | Shows all transactions; **"View Logs"** links to SHA-256 ledger |
| **7. Voice Input** | Click Mic icon $\rightarrow$ Say goal | N/A | Speech Recognition | Transcribes into goal box $\rightarrow$ Executes smoothly |

---

## 22. Common "Why" Questions

### WHY A DETERMINISTIC POLICY ENGINE?
Because LLMs are non-deterministic. A payment system requires mathematical certainty and rigid invariant enforcement that cannot be bypassed by prompt injection.

### WHY HUMAN-IN-THE-LOOP (HITL)?
High-value purchases represent financial liability. Requiring human confirmation above ₹3,000 balances autonomous convenience for minor items with human oversight for expensive equipment.

### WHY HARD-BLOCK INSTEAD OF ASKING FOR APPROVAL ON EVERYTHING?
Hard caps (e.g. ₹10,000 single / ₹25,000 daily) establish an absolute risk ceiling. If an agent goes rogue or attempts to buy 1,000 items, the server terminates execution without bothering the user.

### WHY SHA-256 AUDIT CHAINING?
In disputed transactions, merchants and buyers need cryptographic proof of what the agent proposed, what policy verified, and when the user approved it. Chaining prevents log modification after the fact.

---

## 23. Final Demo Video Script (3–5 Minutes)

### SCENE 1 — INTRODUCTION (0:00 – 0:40)
* **Screen:** AgentCart Product View homepage.
* **What to Say:** *"Welcome to AgentCart. AgentCart is an autonomous agentic commerce protocol that allows AI buyer agents to discover products and execute purchases on Razorpay rails while enforcing deterministic financial guardrails. We give the AI zero financial authority: all prices, limits, and approvals are verified directly by our server-side policy engine."*

### SCENE 2 — AUTONOMOUS PURCHASE (0:40 – 1:20)
* **What to Click:** Click **Scenario 1 (4K HDMI Cables)**, then click **Execute Autonomous Purchase**.
* **What Happens:** The agent finds 3 HDMI cables @ ₹799 = ₹2,397. Because ₹2,397 is below our ₹3,000 auto-approve ceiling, it executes autonomously.
* **What to Say:** *"Notice the live execution trace. The agent parses the goal, searches the database, verifies ₹2,397 against our ₹3,000 ceiling, creates a Razorpay order, and settles payment autonomously with an SHA-256 audit entry."*

### SCENE 3 — HUMAN-IN-THE-LOOP REJECTION & APPROVAL (1:20 – 2:20)
* **What to Click:** Click **Scenario 2 (Keychron Keyboard)**, click **Execute**, then click **Reject Proposal**.
* **What Happens:** Item is ₹6,499 ($> ₹3,000$). The server pauses execution and issues an HMAC-SHA256 HITL token. Clicking Reject immediately halts the pipeline with zero financial capture.
* **What to Say:** *"For high-value purchases between ₹3,000 and ₹10,000, AgentCart halts at the HITL gate. When I click Reject, execution stops immediately, zero payment is called, and the rejection is permanently recorded in our audit ledger."*

### SCENE 4 — HARD POLICY BLOCK (2:20 – 3:00)
* **What to Click:** In the goal box, type `"Buy 13 HDMI cables for my office"`, set budget slider to ₹15,000, and click **Execute**.
* **What Happens:** $13 \times ₹799 = ₹10,387$. Exceeds ₹10,000 limit. Policy Engine immediately returns `REJECTED_OVER_BUDGET`.
* **What to Say:** *"Here we test our hard spending ceiling. 13 cables equal ₹10,387, exceeding our ₹10,000 single-transaction limit. The Policy Engine blocks the order immediately at the policy check step. No payment rail is ever touched."*

### SCENE 5 — ORDER HISTORY & AUDIT LEDGER (3:00 – 3:45)
* **What to Click:** Click **Order History** tab in sidebar, show the table, then click **"View Logs"** on any settled order.
* **What to Say:** *"In the Order History tab, every transaction is tracked with its verified amount, Razorpay order ID, and status. Clicking 'View Logs' takes us directly to the Cryptographic Audit Ledger, where every event is sealed in a tamper-evident SHA-256 hash chain."*

---

## 24. Interview Preparation Q&A

### Q1: Why can't we let the LLM handle payment limits directly?
> **Simple Answer:** Because LLMs hallucinate and can be tricked by prompt injection.  
> **Technical Explanation:** LLMs are probabilistic text predictors, not deterministic logic engines. In AgentCart, the LLM has zero financial authority. The Python `PolicyEngine` recalculates cart totals strictly from the authoritative SQLite database.  
> **Example:** If an LLM claims 10 laptops cost ₹500, the Policy Engine recalculates $10 \times ₹60,000 = ₹600,000$ and blocks the transaction immediately.

### Q2: How does the cryptographic HITL token work?
> **Simple Answer:** It is a digital signature generated by the server that proves human approval for that exact cart.  
> **Technical Explanation:** The backend creates an HMAC-SHA256 digest over `session_id`, `verified_total`, `proposal_hash`, and `idempotency_key`, signed with `HITL_SIGNING_SECRET`. The token is single-use and consumed upon verification to prevent replay attacks.  
> **Example:** A token signed for ₹6,499 cannot be used for a ₹10,000 order or reused in a different session.

### Q3: What is the difference between HITL and a Hard Block?
> **Simple Answer:** HITL asks the human for permission; Hard Block stops immediately without asking.  
> **Technical Explanation:** HITL is a conditional gate triggered between ₹3,001 and ₹10,000. Hard Block is an absolute boundary ($> ₹10,000$ or daily limit breach) that terminates execution unconditionally to prevent catastrophic loss.

### Q4: What happens if the Gemini API is offline?
> **Simple Answer:** The system switches to a built-in heuristic parser and continues running.  
> **Technical Explanation:** `buyer_intent.py` catches Gemini API exceptions and falls back to deterministic regex pattern matching, extracting keywords, categories, and quantities so the demo never crashes.

### Q5: How does the SHA-256 Audit Ledger guarantee tamper evidence?
> **Simple Answer:** Modifying any past event breaks the cryptographic chain.  
> **Technical Explanation:** Every entry incorporates $\text{Hash}_{n-1}$ into its own hash payload. Modifying any historical row causes all subsequent hashes to fail validation during `verify_chain_integrity()`.

---

## 25. Verified Testing & Build Status

* **Backend Automated Test Suite:** `python -m pytest evals/ -v` $\rightarrow$ **88/88 passed (100%) in 12.28s**.
* **Frontend Production Build:** `npm run build` $\rightarrow$ **Success (`✓ built in 4.26s`, 0 errors)**.

---

## 26. FINAL PROJECT STATUS

> **Status:** **FEATURE-COMPLETE & VERIFIED FOR FINAL DEMO**  
> All capabilities (Core flow, 3 spending policies, autonomous execution, HITL approve/reject, hard-block invariant, voice input, cross-sell recalculation, order history tracker, Razorpay mock/test mode, and SHA-256 audit ledger) are fully implemented and verified. No further code modifications are required.
