# AgentCart: Complete Project Understanding & Architectural Study Guide

> **Target Audience:** Presenters, Hackathon Evaluators, Interviewers, and Developers.  
> **Project Scope:** Autonomous AI Commerce Protocol with Deterministic Spend Policy Guardrails, Razorpay Rails Integration, and SHA-256 Chained Cryptographic Audit Ledger.

---

## 1. Project Overview

### What is AgentCart?
**AgentCart** is an autonomous agentic commerce protocol and execution engine. It allows AI buyer agents (such as Google Gemini with heuristic fallbacks) to understand natural language shopping goals, discover merchant products via Model Context Protocol (MCP) catalog tools, and execute payments within **hard, deterministic financial guardrails** on **Razorpay rails**.

### What Problem Does It Solve?
As autonomous AI agents represent an increasing share of e-commerce traffic, giving an LLM direct access to credit cards or financial authority creates severe vulnerabilities:
1. **Price Hallucination:** An LLM might hallucinate that an expensive laptop costs ₹500 and attempt to purchase it.
2. **Prompt Injection & Adversarial Manipulation:** A malicious website or adversarial input could trick the AI agent into sending funds to an attacker.
3. **Unbounded Spending Spree:** Without velocity limits, a runaway loop could drain merchant or corporate funds.
4. **Lack of Cryptographic Accountability:** Financial accounting requires non-repudiable, tamper-evident audit trails.

### Why Autonomous Commerce Needs Bounded Autonomy
AgentCart solves this by establishing **Zero Financial Authority for the LLM**:
* **Autonomous Pre-Authorization (Auto-Approve Ceiling):** Low-value purchases within pre-approved thresholds (e.g., $\le$ ₹3,000) execute autonomously without interrupting the user.
* **Human-in-the-Loop Gate (HITL):** High-value purchases (e.g., ₹3,001 to ₹10,000) require explicit, cryptographically signed approval from the human operator before order creation.
* **Hard Policy Ceilings (Per-Transaction & Daily Limits):** Any purchase exceeding the per-transaction limit or cumulative daily budget is deterministically rejected by the server before reaching Razorpay rails.

---

## 2. Core Idea

AgentCart bridges natural language AI reasoning with deterministic financial execution:

| Step | Component | Responsibility | Financial Authority |
| :--- | :--- | :--- | :---: |
| **1. Intent Understanding** | Gemini LLM / Heuristic Parser | Extracts keywords, category, quantity, budget | **None (0%)** |
| **2. Catalog Discovery** | MCP Catalog Tool & SQLite DB | Searches inventory and specifications | **None (0%)** |
| **3. Recommendation & Growth** | Merchant Growth Engine | Evaluates compatible upsells and cross-sells | **None (0%)** |
| **4. Policy Gate Check** | Server Deterministic PolicyEngine | Recalculates total from authoritative DB, enforces limits | **100% Truth** |
| **5. Human-in-the-Loop** | Cryptographic HMAC-SHA256 Token | Secures human sign-off on high-value orders | **User Mandate** |
| **6. Razorpay Rails** | Razorpay Service (Test/Mock Mode) | Creates order, collects payment, verifies signatures | **Payment Rail** |
| **7. Tamper-Evident Ledger** | Cryptographic Audit Ledger | Records chained SHA-256 hash history of every event | **Immutable Proof** |

---

## 3. Complete End-to-End Flow

```
[Buyer Goal (Voice or Text)]
        │
        ▼
[1. Goal Intake & Parsing] (Gemini 2.5 Flash / Deterministic Fallback)
        │
        ▼
[2. MCP Merchant Catalog Search] (Fetches authoritative items from SQLite)
        │
        ▼
[3. Grounded Recommendation & Growth] (Proposes item + contextual upsell / cross-sell)
        │
        ▼
[4. Order Proposal Formulation] (Calculates verified totals from database)
        │
        ▼
[5. Deterministic Policy Gate Check]
        │
        ├── Exceeds Per-Tx Limit or Daily Limit? ────────► [REJECTED & HALTED]
        │
        ├── Exceeds Auto-Approve Ceiling? ──────────────► [HITL SIGN-OFF GATE]
        │                                                         │
        │                                           ┌─────────────┴─────────────┐
        │                                           ▼                           ▼
        │                                    [User Approves]             [User Rejects]
        │                                           │                           │
        │                                           ▼                           ▼
        │                                [Razorpay Checkout]         [ORDER REJECTED / HALTED]
        │                                           │
        └── Under Auto-Approve Ceiling? ────────────┤
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
```

---

## 4. Frontend Architecture

* **Framework:** React 18 with Vite, TypeScript, and Tailwind CSS.
* **Key Components & Layout in `frontend/src/App.tsx`:**
  - **Persistent Header:** Brand banner, Razorpay status badge, Policy Gate indicator, and "Launch Purchase" CTA.
  - **Sidebar Navigation:** 6 tabs (`Product`, `Order History`, `Catalog`, `Analytics`, `Policy & Security`, `Audit Ledger`).
  - **Natural Language Goal Box:** Textarea with inline Web Speech API **Voice Input** microphone button, budget slider, and quick evaluation scenarios.
  - **Execution & Settlement Trace:** Live Server-Sent Events (SSE) stream showing each pipeline step in real time.
  - **HITL Sign-Off Card:** Displays when approval is required, featuring clear "Approve & Settle Razorpay" and "Reject Proposal" buttons.
  - **Growth Engine Cards:** Interactive upsell upgrade and cross-sell "Add to Cart" / "Decline" offers.
  - **Order History View:** Searchable/filterable list of all past transactions, statuses, timestamps, amounts, and audit trail links.
  - **Policy & Security Panel:** Interactive controls for Auto-Approve Ceiling, Per-Transaction Limit, and Daily Spending Limit with live gauge.
* **Communication with Backend:** HTTP JSON requests for CRUD/policy/growth and `fetch()` SSE streaming (`text/event-stream`) for live agent execution.

---

## 5. Backend Architecture

* **Framework:** FastAPI (Python 3.10+) with Uvicorn ASGI server and Pydantic schema validation.
* **Directory Structure & Roles:**
  - `backend/main.py`: REST endpoints, SSE agent stream, webhooks, and order lifecycle management.
  - `backend/agent/`: Buyer agent orchestrator (`buyer_agent.py`), Gemini intent parser with fallback (`buyer_intent.py`), and MCP tools (`tools.py`).
  - `backend/security/policy_engine.py`: Server-side deterministic policy validation, daily spending tracker, HMAC token signing/verification, and idempotency cache.
  - `backend/merchant/`: SQLite catalog management (`catalog.py`), growth engine (`growth_engine.py`), and analytics aggregator (`analytics.py`).
  - `backend/payments/razorpay_client.py`: Razorpay order creation, Checkout modal options, HMAC-SHA256 signature verification, and mock sandbox simulation.
  - `backend/audit/`: SHA-256 chained tamper-evident audit ledger (`ledger.py`) backed by SQLite.

---

## 6. Agent / Intent Understanding

1. **Natural Language Intake:** The user enters a shopping goal via typing or voice (e.g., *"Buy 2 braided 4K HDMI cables for office setup"*).
2. **Gemini Intent Decomposition:** Calls Google Gemini (`gemini-2.5-flash` or configured model) to produce a structured JSON schema:
   - `query`: Primary search term (`"braided 4K HDMI cable"`)
   - `category`: Target catalog category (`"cables"`)
   - `budget`: Parsed ceiling (`3000.0`)
   - `quantity`: Desired units (`2`)
   - `required_features`: Extracted key features (`["4k", "braided"]`)
3. **Deterministic Heuristic Fallback:** If the Gemini API is unavailable or offline, the agent automatically switches to regex/keyword heuristics without throwing an unhandled exception or halting the pipeline.

---

## 7. Catalog & Product Discovery

* **Authoritative Catalog:** Stored in an SQLite database containing real products across categories (`accessories`, `cables`, `peripherals`, `pantry`) with verified unit prices, stock counts, and technical specs.
* **Discovery via MCP Tools:** The agent invokes `tool_search_catalog(query, category, max_price)` to find matching candidates.
* **Zero Trust on LLM Prices:** The agent is NEVER permitted to set or state unit prices; prices are strictly retrieved from the database.
* **Chaos Engineering & Resilience:**
  - **Stockout Auto-Recovery:** If the top item has 0 stock, the agent intercepts the stockout, logs an `ERROR_RECOVERED` event, and automatically recommends an in-stock alternative in the same category.
  - **Price Surge Rejection:** If price surges before checkout, the policy engine recalculates the new verified total and prevents unauthorized capture.

---

## 8. Policy & Security

The backend policy engine enforces three strict spending controls:

1. **Per-Transaction Limit (Max Allowed Single Order):**
   - Hard cap (e.g., ₹10,000.00). Any order whose verified total exceeds this limit is immediately blocked (`REJECTED_OVER_BUDGET`).
2. **Auto-Approve Ceiling (Autonomous Mandate):**
   - Pre-authorized ceiling (e.g., ₹3,000.00). Orders $\le$ this amount are pre-authorized autonomously.
   - Orders exceeding this ceiling trigger Human-in-the-Loop approval (`HITL_REQUIRED`).
3. **Daily Spending Limit:**
   - Tracks cumulative successful spending for the current calendar day across all settled transactions.
   - If a new order would cause total daily spend to exceed the daily limit (e.g., ₹25,000.00), the transaction is blocked (`REJECTED_OVER_DAILY_BUDGET`).
4. **Replay & Idempotency Protection:**
   - Generates an SHA-256 digest over `session_id`, `merchant_id`, `total_amount`, and items. Duplicate orders within a sliding window are rejected (`REJECTED_DUPLICATE`).

---

## 9. Human-in-the-Loop (HITL)

### Trigger Condition
When an order's verified database total is above the `auto_approve_limit` and within the `max_single_transaction_limit`.

### Cryptographic Sign-Off Token
The server issues a single-use token: `HMAC-SHA256(HITL_SIGNING_SECRET, session_id:amount:digest:idempotency_key:exp)`

### Approve Path
1. Human clicks **"Approve & Settle Razorpay"**.
2. Frontend submits token to `/api/agent/approve-hitl`.
3. Backend verifies HMAC signature, checks expiration, and consumes token in `used_hitl_tokens` (preventing replay).
4. Razorpay order is created and settled.

### Reject Path
1. Human clicks **"Reject Proposal"**.
2. Frontend immediately halts the purchase pipeline, clears pending status, and sends POST `/api/agent/reject-hitl`.
3. An execution trace step is appended: `title: "Human Approval Rejected", status: "REJECTED"`.
4. Audit ledger logs `HITL_REJECTED`.
5. Status ribbon updates to **"Order Rejected (Approval Declined)"**.
6. No payment API is called, and no money is captured.

---

## 10. Cross-Sell & Upsell ("Add to Cart")

* **Contextual Suggestions:** Powered by the Merchant Growth Engine using category compatibility graphs (e.g., Keyboard $\rightarrow$ Wrist Rest / Mouse).
* **"Add to Cart" Action:**
  - Adds attachment to cart proposal.
  - Recalculates total from authoritative database prices.
  - Re-evaluates policy engine: if the updated total crosses the auto-approve ceiling, HITL is dynamically triggered.
* **"Decline" Action:**
  - Records offer decline in growth analytics.
  - Preserves original base order unchanged.

---

## 11. Razorpay Integration

* **Live Test Mode:** When `RAZORPAY_KEY_ID` / `KEY_SECRET` are provided and `RAZORPAY_MOCK_MODE=false`, the app opens the official Razorpay Checkout modal for test cards/UPI.
* **Mock Sandbox Mode:** When `RAZORPAY_MOCK_MODE=true` (or keys absent), AgentCart simulates order creation and settlement with HMAC signatures, allowing 100% deterministic local testing and CI verification.
* **Server-Side Verification:** Client responses are NEVER trusted as proof of payment. Payment is only marked `PAID` after verifying Razorpay HMAC signatures or webhooks on raw payload bytes.

---

## 12. Cryptographic Audit Ledger

* **SHA-256 Chaining:** Every log entry contains `previous_hash` and `cryptographic_hash`.
* **Formula:** $\text{Hash}_n = \text{SHA-256}(\text{Hash}_{n-1} : \text{id} : \text{session\_id} : \text{timestamp} : \text{event\_type} : \text{status} : \text{summary} : \text{details\_json})$
* **Tamper Evidence:** Modifying, inserting, or deleting any historical entry breaks the hash chain, immediately detected by `verify_chain_integrity()`.

---

## 13. Order History / Tracker

* Accessible via the **Order History** tab.
* Displays a clean table of all sessions and orders:
  - **Order ID & Session ID**
  - **Natural Language Goal**
  - **Verified Amount (₹)**
  - **Status:** `Settled` (green), `Rejected` (rose), `Pending Approval` (amber), `Created` (slate).
  - **Payment ID**
  - **Timestamp**
  - **View Logs Button:** Instantly filters the SHA-256 audit ledger to inspect the exact cryptographic event stream for that order.

---

## 14. Voice Input

* Implemented directly in the Natural Language Goal card using the browser **Web Speech API** (`window.SpeechRecognition` / `webkitSpeechRecognition`).
* **Flow:**
  1. User clicks the microphone button.
  2. Button pulses red with `"Listening..."`.
  3. Spoken audio is transcribed into English text and inserted into the goal textarea.
  4. User can review, edit, or execute the autonomous purchase.
  5. If unsupported or microphone access is denied, a non-intrusive warning appears and standard typing continues uninterrupted.

---

## 15. Important Files Reference

| File Path | Purpose | When Used |
| :--- | :--- | :--- |
| `backend/main.py` | FastAPI application, REST endpoints, SSE stream, webhook handler | During every client request & webhook |
| `backend/security/policy_engine.py` | Deterministic spend verification, daily limit check, HITL HMAC signing | Before any order proposal is approved |
| `backend/agent/buyer_agent.py` | Agentic loop orchestrating intake, search, recommendation, and execution | During autonomous purchase execution |
| `backend/agent/buyer_intent.py` | Gemini LLM structured intent parser and heuristic fallback | During Goal Intake phase (Step 1) |
| `backend/merchant/catalog.py` | Authoritative SQLite catalog database and chaos simulation | During catalog discovery and price checks |
| `backend/merchant/growth_engine.py` | Catalog-grounded upsell and cross-sell recommendation engine | Formulating recommendations & add-ons |
| `backend/payments/razorpay_client.py` | Razorpay Orders API client, signature verification, and mock sandbox | Order creation, checkout, settlement |
| `backend/audit/ledger.py` | Tamper-evident SHA-256 chained audit ledger in SQLite | Every event, transition, and state change |
| `frontend/src/App.tsx` | Main React UI containing all 6 navigation views and purchase pipeline | User-facing dashboard and interactive UI |

---

## 16. API & Data Flow Summary

| Endpoint | Method | Payload / Params | Response |
| :--- | :---: | :--- | :--- |
| `/api/agent/run` | `POST` | `{ goal, session_id, max_budget }` | SSE stream (`text/event-stream`) |
| `/api/agent/approve-hitl` | `POST` | `{ session_id, proposal, verified_total, hitl_token }` | Order & settlement confirmation |
| `/api/agent/reject-hitl` | `POST` | `{ session_id, reason }` | `{ status: "REJECTED" }` |
| `/api/policy` | `GET` | None | `{ max_single_transaction_limit, auto_approve_limit, daily_spending_limit, spent_today }` |
| `/api/policy` | `POST` | Updated policy config object | Updated policy config |
| `/api/orders` | `GET` | None | `{ orders: [OrderRecord, ...] }` |
| `/api/growth/interact` | `POST` | `{ session_id, offer_type, action, product_id, ... }` | Growth interaction result & recalculated total |
| `/api/audit-logs` | `GET` | `?session_id=...` | `{ logs: [AuditLogEntry, ...] }` |

---

## 17. State Management

Key state variables in `frontend/src/App.tsx`:
* `promptGoal` (string): Natural language user shopping intent.
* `maxBudget` (number): User-selected maximum spending budget.
* `steps` (AgentStep[]): Real-time array of execution steps rendered in the live trace.
* `pendingHitl` (object | null): Stores pending HITL proposal, verified total, and cryptographic token.
* `isListening` (boolean): Indicates whether browser voice recognition is currently capturing audio.
* `offerDecisions` (Record): Maps upsell/cross-sell item IDs to `accepted` or `declined` states.
* `orders` (OrderRecord[]): Cached list of orders displayed in the Order History view.

---

## 18. Error & Failure Cases

1. **Product Not Found:** Agent searches catalog; if no matching criteria exist within budget, gracefully yields `No Matching Products Found` and halts.
2. **Per-Transaction Limit Exceeded:** Order amount $> ₹10,000 \rightarrow$ Policy Engine blocks with `REJECTED_OVER_BUDGET`.
3. **Daily Spending Limit Exceeded:** Cumulative spending today $+ \text{order} > \text{daily limit} \rightarrow$ Policy Engine blocks with `REJECTED_OVER_DAILY_BUDGET`.
4. **HITL Rejection:** User clicks Reject $\rightarrow$ Pipeline halts immediately, logged as `HITL_REJECTED`, zero capture.
5. **Gateway Payment Failure:** Simulated or real Razorpay failure transitions order to `FAILED`/`CANCELLED` without false settlement.
6. **Replayed Request:** Replaying duplicate payload inside time window is rejected by `PersistentIdempotencySet`.

---

## 19. Demo Scenarios

| Scenario | Goal & Input | Expected Flow |
| :--- | :--- | :--- |
| **A. Autonomous Purchase** | *"Buy 2 braided 4K HDMI cables"* (Budget: ₹3,000) | Intent $\rightarrow$ Discovery (2 cables @ ₹799 = ₹1,598) $\rightarrow$ Auto-Approved under ₹3,000 $\rightarrow$ Razorpay settled autonomously. |
| **B. HITL Approval** | *"Purchase 1 Keychron K2 mechanical keyboard"* (Budget: ₹8,000) | Discovery (Keyboard @ ₹6,499) $\rightarrow$ Exceeds ₹3,000 $\rightarrow$ HITL gate $\rightarrow$ Click **"Approve & Settle"** $\rightarrow$ Settled. |
| **C. HITL Rejection** | *"Purchase 1 Keychron K2 mechanical keyboard"* (Budget: ₹8,000) | Discovery $\rightarrow$ HITL gate $\rightarrow$ Click **"Reject Proposal"** $\rightarrow$ Pipeline halts immediately with red badge, zero payment. |
| **D. Transaction Limit Block** | *"Order 2 Logitech MX Master 3S mice"* (Budget: ₹15,000) | Total ₹15,998 $\rightarrow$ Policy Engine detects $> ₹10,000$ limit $\rightarrow$ Blocked with `Policy Ceiling Blocked`. |
| **E. Cross-Sell Add to Cart** | *"Buy 2 braided 4K HDMI cables"* $\rightarrow$ Cross-sell appears $\rightarrow$ Click **"Add to Cart"** | Add-on attached $\rightarrow$ Total recalculated from DB $\rightarrow$ Policy re-verified $\rightarrow$ Settled. |
| **F. Voice Input** | Click Mic icon $\rightarrow$ Say *"Restock coffee beans"* | Spoken text populates textarea $\rightarrow$ Click **"Execute Autonomous Purchase"** $\rightarrow$ Runs smoothly. |

---

## 20. Demo Walkthrough Script

### Step 1: Product View & Autonomous Purchase
* **What to Click:** Click **Scenario 1 (4K HDMI Cables)**, then click **Execute Autonomous Purchase**.
* **What Happens Technically:** Gemini parses intent, queries SQLite catalog, sees ₹1,598 total $\le$ ₹3,000 auto-approve ceiling, generates Razorpay order, settles payment, and records SHA-256 chained audit logs.
* **What to Say:** *"Here you see the autonomous execution pipeline. Because the verified total of ₹1,598 is within our ₹3,000 pre-authorization limit, AgentCart securely executes the transaction without requiring human intervention."*

### Step 2: Human-in-the-Loop Rejection & Approval
* **What to Click:** Click **Scenario 2 (Keychron Keyboard)**, click **Execute**, then click **Reject Proposal**.
* **What Happens Technically:** Item is ₹6,499 ($> ₹3,000$). The server generates an HMAC-SHA256 HITL token. Clicking Reject immediately stops the pipeline, logs `HITL_REJECTED`, and verifies zero financial capture.
* **What to Say:** *"For high-value purchases between ₹3,000 and ₹10,000, AgentCart halts execution at the HITL cryptographic gate. If the operator rejects the proposal, execution stops instantly with zero financial capture."*

### Step 3: Spending Policies & Order History
* **What to Click:** Navigate to **Policy & Security**, show the 3 policy sliders and the live daily spending meter. Then navigate to **Order History** to inspect recorded transactions.
* **What to Say:** *"All policy bounds—per-transaction, auto-approve ceiling, and daily cumulative limit—are enforced server-side. In the Order History tab, every transaction is tracked with its verified amount, Razorpay status, and cryptographic audit link."*

---

## 21. Key Interview Questions & Answers

### Q1: Why can't we let the LLM handle payment limits directly?
> **Answer:** LLMs are probabilistic and vulnerable to prompt injection, hallucinations, and format manipulation. In AgentCart, the LLM has **Zero Financial Authority**. The server-side Python `PolicyEngine` recalculates cart totals strictly from the authoritative SQLite database and enforces spending rules deterministically.

### Q2: How does the cryptographic HITL token work?
> **Answer:** When an order requires human approval, the backend issues a signed token: `HMAC-SHA256(secret, session_id : amount : digest : idempotency_key : exp)`. The token is cryptographically bound to the exact session, verified amount, and cart items, and is consumed upon first use to prevent replay attacks.

### Q3: How does the SHA-256 Audit Ledger guarantee tamper evidence?
> **Answer:** Each log entry incorporates the hash of the preceding entry ($\text{Hash}_{n-1}$) into its own SHA-256 payload. If an attacker modifies or deletes any historical record in the SQLite database, the hash chain breaks, which is immediately flagged by `verify_chain_integrity()`.

### Q4: What is the difference between Test Mode and Mock Mode in Razorpay?
> **Answer:** When real API test keys (`rzp_test_...`) are provided, AgentCart interacts with Razorpay's live Test Mode API and opens the standard Razorpay Checkout modal. When mock mode is enabled (`RAZORPAY_MOCK_MODE=true`), the server simulates order creation and HMAC signatures locally, allowing offline development and automated CI testing.
