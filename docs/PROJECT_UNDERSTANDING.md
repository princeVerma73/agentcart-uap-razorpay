# AgentCart: Complete Project Understanding & Architectural Study Guide

> **Target Audience:** Developers, Technical Evaluators, Hackathon Judges, and Presenters.  
> **Project Scope:** Autonomous AI Commerce Protocol with Deterministic Spend Policy Guardrails, Razorpay Payment Rails, and Cryptographic SHA-256 Audit Chaining.

---

## 1. Project Overview

### What is AgentCart?
**AgentCart** is an autonomous agentic commerce framework that enables Large Language Model (LLM) buyer agents to discover products, negotiate offers, and execute financial transactions within strict, deterministic policy boundaries on **Razorpay** payment infrastructure.

### What Problem Does It Solve?
AI agents are increasingly capable of making purchase decisions. However, giving an LLM direct, unbounded access to corporate credit cards or payment gateways is dangerous:
1. **Hallucination & Overspending:** An LLM might hallucinate prices, miscalculate quantities, or order unauthorized items.
2. **Prompt Injection & Adversarial Exploits:** Malicious actors or compromised merchant sites could trick the agent into paying arbitrary amounts.
3. **Lack of Auditing:** Financial systems require deterministic, immutable audit trails, whereas LLMs are non-deterministic.
4. **Binary Control Failure:** Traditional systems either require human approval for *every* action (destroying autonomous utility) or give *unrestricted* access (catastrophic financial risk).

### Why Autonomous Commerce Needs Controls
AgentCart introduces **Bounded Autonomy**:
* Low-risk, low-value purchases below an autonomous limit are auto-approved.
* High-value purchases trigger a **Human-in-the-Loop (HITL)** cryptographic approval gate.
* Transactions exceeding hard ceilings are deterministically rejected by the server before reaching payment rails.

```
+-------------------------------------------------------------------------------+
|                             AGENTCART BOUNDS                                 |
|                                                                               |
|   [₹0 ----------- Auto-Approve (₹3,000) ----------- Hard Ceiling (₹10,000) --] |
|        Autonomous Execution          HITL Cryptographic Sign-Off       BLOCKED |
+-------------------------------------------------------------------------------+
```

### Roles of Core System Components
* **AI Buyer Agent:** Interprets human natural language intent, searches merchant catalog tools via the Model Context Protocol (MCP), evaluates product specs, and formulates cart proposals.
* **Deterministic Policy Engine:** Python-based rule engine that validates price integrity against the merchant database, checks velocity/limits, and enforces replay protection without LLM involvement.
* **Human Approval (HITL Gate):** A cryptographic signing mechanism where high-value transactions issue a signed HMAC-SHA256 token requiring human confirmation before a Razorpay order can be created.
* **Razorpay Service:** Manages server-side Razorpay order creation, standard Checkout SDK modal handling, and server-to-server signature verification (`HMAC-SHA256`).
* **Cryptographic Audit Ledger:** An immutable SQLite-backed ledger where every state transition, tool call, policy evaluation, and payment settlement is sequentially hashed and linked with SHA-256 hashes.
* **Universal Agentic Payments (UAP / AP2):** Implements emerging agentic commerce principles: pre-authorized spending mandates, non-repudiable cryptographic intent, and idempotent settlement.

---

### Pitch Explanations

#### 30-Second Explanation
> *"AgentCart is an autonomous commerce layer that lets AI agents purchase products on Razorpay rails while enforcing deterministic spending limits. Small purchases auto-approve, high-value orders require cryptographic human sign-off, and every action is sealed in a SHA-256 chained audit ledger."*

#### 1-Minute Explanation
> *"Giving AI agents payment cards creates extreme financial and prompt-injection risks. AgentCart solves this by placing a deterministic policy engine between the AI buyer agent and Razorpay payment rails. When a user requests a purchase in natural language, the agent searches live MCP merchant inventory and constructs an order. The server-side policy engine verifies prices directly against the database—never trusting the LLM's numbers. Orders under ₹3,000 execute autonomously, orders between ₹3,000 and ₹10,000 trigger a signed Human-in-the-Loop approval gate, and orders exceeding ₹10,000 are blocked. Every event is hashed into an immutable audit trail."*

#### Technical Explanation (For Interviewers & Judges)
> *"AgentCart implements an agentic payment protocol following NPCI UAP and AP2 principles. It separates non-deterministic LLM reasoning (powered by Gemini with heuristic fallback) from deterministic settlement enforcement. The architecture comprises a FastAPI backend, MCP catalog discovery layer, deterministic PolicyEngine with replay protection, a Razorpay checkout integration with server-side HMAC-SHA256 signature verification, and a cryptographically chained SQLite audit ledger. The system also includes an autonomous Merchant Growth Engine for contextual upsells and cross-sells, backed by chaos engineering simulators for stockouts and price surges."*

---

## 2. Project Structure

```
agentcart-razorpay/
│
├── backend/                        # FastAPI Server & Python Core Engine
│   ├── main.py                     # API Routes, SSE streaming, payment verification
│   ├── config.py                   # Pydantic environment configuration
│   ├── requirements.txt            # Python dependencies (fastapi, httpx, uvicorn, etc.)
│   │
│   ├── agent/                      # AI Agent & Intent Decomposition
│   │   ├── buyer_agent.py          # Multi-step Agent execution loop & streaming generator
│   │   ├── buyer_intent.py         # Gemini API structured parser + heuristic fallback
│   │   └── tools.py                # MCP-compliant catalog & policy tools
│   │
│   ├── merchant/                   # Merchant Inventory & Growth Engine
│   │   ├── catalog.py              # CatalogDB, in-memory inventory & chaos tools
│   │   ├── growth_engine.py        # Contextual upsell & cross-sell recommendation engine
│   │   ├── analytics.py            # Merchant GMV, AOV, and recovery analytics
│   │   └── models.py               # Pydantic models for Products, CartItems, Proposals
│   │
│   ├── security/                   # Deterministic Guardrails
│   │   └── policy_engine.py        # Spend ceilings, pre-auth bounds, HITL HMAC tokens
│   │
│   ├── payments/                   # Razorpay Rails
│   │   └── razorpay_client.py      # Razorpay order generation, checkout & webhook verification
│   │
│   └── audit/                      # Cryptographic Chained Ledger
│       ├── ledger.py               # SHA-256 sequential hash-chaining engine
│       ├── models.py               # AuditLog Pydantic schemas
│       └── audit_ledger.db         # SQLite persistent log store
│
├── frontend/                       # React 18 + TypeScript + Vite + TailwindCSS UI
│   ├── src/
│   │   ├── App.tsx                 # Single-page application with category tab views
│   │   ├── index.css               # Typography styles, keyframe animations, scrollbars
│   │   └── main.tsx                # React DOM entry point
│   ├── index.html                  # HTML entry point with Google Fonts (Plus Jakarta Sans)
│   ├── tailwind.config.js          # Custom Razorpay palette & typography tokens
│   ├── package.json                # Frontend npm dependencies
│   └── vite.config.ts              # Vite development & build configuration
│
├── evals/                          # Evaluation Suite & Adversarial Security Tests
│   ├── test_phase1_security_ledger.py
│   ├── test_phase2_gemini_agent.py
│   ├── test_phase3_growth_engine.py
│   ├── test_phase4_razorpay_checkout.py
│   ├── test_phase5_recommendation_integrity.py
│   ├── test_phase6_order_lifecycle.py
│   ├── test_phase7_growth_and_reconciliation.py
│   ├── test_phase8_adversarial_security.py
│   ├── test_agent_scenarios.py
│   ├── run_growth_evaluation.py
│   └── demo_walkthrough.py
│
├── docs/                           # Documentation and guides
│   └── PROJECT_UNDERSTANDING.md    # This comprehensive document
│
├── .env.example                    # Environment variable template
├── readme.md                       # High-level project README
└── SUBMISSION_CHECKLIST.md         # Verification and submission checklist
```

---

## 3. High-Level Architecture

```
                                  USER INTERACTION
                                         │
                    [Natural Language Goal + Budget Allocation]
                                         │
                                         ▼
                            REACT FRONTEND (Vite / TS)
                                         │
                     POST /api/agent/run (SSE Streaming Request)
                                         │
                                         ▼
                                FASTAPI BACKEND
                                         │
                    ┌────────────────────┴────────────────────┐
                    │                                         │
                    ▼                                         ▼
           Gemini Intent Parser                     Heuristic Fallback
         (Structured JSON schema)                (Regex / Keyword Parsing)
                    │                                         │
                    └────────────────────┬────────────────────┘
                                         │
                                [BuyerIntent Object]
                                         │
                                         ▼
                             MCP CATALOG DISCOVERY
                      (Search by specs, budget, stock)
                                         │
                                         ▼
                          GROUNDED RECOMMENDATION ENGINE
                       (+ Upsell / Cross-Sell Growth Engine)
                                         │
                                         ▼
                               ORDER PROPOSAL (DB Verified)
                                         │
                                         ▼
                          DETERMINISTIC POLICY ENGINE
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              │                          │                          │
        Total <= ₹3,000         ₹3,000 < Total <= ₹10,000        Total > ₹10,000
              │                          │                          │
              ▼                          ▼                          ▼
     [Auto-Approve UAP]         [HITL Approval Gate]       [Hard Rejection]
              │                  (HMAC Sign-Off Token)              │
              │                          │                          │
              │                  Human Approved?                    │
              │                 YES /         \ NO                  │
              │                     /             \                 │
              └───────────────►─── /               ▼                ▼
                                  │             ABORTED          HALTED
                                  ▼
                         RAZORPAY PAYMENT RAILS
                       • Create Razorpay Order
                       • Standard Checkout Modal
                       • Server-Side Signature Verification
                                  │
                                  ▼
                        SETTLEMENT & FULFILLMENT
                                  │
                                  ▼
                      CRYPTOGRAPHIC AUDIT LEDGER
                   (SHA-256 Chained Event Record)
```

---

## 4. Frontend Architecture & UI Breakdown

* **Framework:** React 18, TypeScript, Vite 5, TailwindCSS.
* **Component Model:** Clean single-page category-wise tab navigation (`Product`, `Catalog`, `Analytics`, `Policy & Security`, `Audit Ledger`).
* **Design Philosophy:** Fintech aesthetic inspired by Razorpay and modern SaaS landing pages. Light off-white background (`#f8fafc`), dark navy typography (`#0a192f`), and Razorpay primary blue (`#0c83fe` / `#0052cc`).

### Category Views
1. **Product View:**
   * Editorial hero headline: *"Autonomous commerce, built for trust."*
   * Goal input textarea with a quick **Clear** action and auto-focus.
   * User budget allocation slider ($\text{₹1,000}$ to $\text{₹20,000}$).
   * **Execute Autonomous Purchase** primary button.
   * Four one-click evaluation scenario presets (Pre-Auth, HITL Gate, B2B Pantry, Hard Ceiling).
   * **Dedicated Purchase Execution & Settlement View:** Visualizes the 6-stage pipeline (Intent $\to$ Discovery $\to$ Policy Check $\to$ Approval $\to$ Payment $\to$ Settlement), step activity cards, interactive Upsell/Cross-sell cards, and HITL sign-off banner.
2. **Catalog View:**
   * Live MCP catalog table displaying products, unit prices, real-time stock, and merchant names.
   * Chaos engineering controls: `+Surge` (80% price inflation), `Deplete` (simulate stockout), `Simulate Gateway Failure`, and `Reset Store`.
3. **Analytics View:**
   * Merchant Growth Dashboard: Total Settled GMV, Conversion Rate, AOV, Incremental Revenue, Upsell/Cross-sell acceptance rates, HITL Gate ratio, and fail-safe recovery counts.
4. **Policy & Security View:**
   * Real-time policy configuration sliders: Autonomous Pre-Auth Limit ($\text{₹500}$–$\text{₹3,000}$), Hard Spending Ceiling ($\text{₹3,000}$–$\text{₹10,000}$), and Strict Mode toggle (Always Require Human Approval).
5. **Audit Ledger View:**
   * Chronological view of SQLite audit entries with timestamps, event types, human-readable summaries, and immutable SHA-256 cryptographic hashes.

---

## 5. End-to-End Execution Trace ("What Happens When I Click Execute?")

Here is the exact code execution path across the 16 stages:

```
[UI Button Click] 
  ──► handleRunAgent() [App.tsx:391]
  ──► POST /api/agent/run [main.py:126]
  ──► buyer_agent.run_goal_stream() [buyer_agent.py:29]
  ──► buyer_intent.parse_intent() [buyer_intent.py:22]
  ──► tool_search_catalog() [tools.py:10]
  ──► catalog_db.search() [catalog.py:133]
  ──► _pick_best_match() [buyer_agent.py:539]
  ──► growth_engine.get_cross_sell_candidate() [growth_engine.py:67]
  ──► OrderProposal construction [buyer_agent.py:316]
  ──► policy_engine.verify_order_proposal() [policy_engine.py:112]
  ──► Branch: Auto-Approve vs HITL vs Rejection [buyer_agent.py:360]
  ──► razorpay_service.create_order() [razorpay_client.py:93]
  ──► SSE event to Client [App.tsx:300]
  ──► Razorpay Checkout Modal [App.tsx:340]
  ──► POST /api/payments/verify [main.py:268]
  ──► razorpay_service.verify_payment() [razorpay_client.py:221]
  ──► audit_ledger.record() [ledger.py:50]
  ──► UI Step Updated to SUCCESS & Settled [App.tsx:940]
```

### Detailed Breakdown of Every Stage

| Stage | File & Function | Input Data | Operation Performed | Output Data | Next Stage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. UI Click** | `frontend/src/App.tsx`<br>`handleRunAgent()` | `promptGoal`, `maxBudget` | Clears previous steps, generates `session_id`, initiates SSE stream. | SSE HTTP Request | Stage 2 |
| **2. API Dispatch** | `backend/main.py`<br>`run_agent_stream()` | `AgentRunRequest` | Receives JSON body, creates `StreamingResponse` wrapping async generator. | StreamingResponse | Stage 3 |
| **3. Agent Intake** | `backend/agent/buyer_agent.py`<br>`run_goal_stream()` | `session_id`, `goal`, `budget` | Logs `AGENT_INTAKE` in audit ledger, delegates parsing to Gemini. | Session initialized | Stage 4 |
| **4. Intent Parsing** | `backend/agent/buyer_intent.py`<br>`parse_intent()` | Raw text goal string | Calls Gemini REST API with JSON schema; on 400/timeout, calls regex heuristic fallback. | `BuyerIntent` object | Stage 5 |
| **5. Catalog Search** | `backend/agent/tools.py`<br>`tool_search_catalog()` | Query string, category, price cap | Queries in-memory `catalog_db`, returns candidate list matching criteria. | `raw_candidates` list | Stage 6 |
| **6. Spec Matching** | `backend/agent/buyer_agent.py`<br>`_pick_best_match()` | Candidates, intent specs | Relevance scoring based on keywords, category, price, and spec matches. | `primary_match` (`Product`) | Stage 7 |
| **7. Growth Evaluation** | `backend/merchant/growth_engine.py`<br>`get_cross_sell_candidate()` | Base product, budget | Checks reciprocal compatible IDs, stock, and budget constraints for add-on options. | `upsell_cand`, `cross_sell_cand` | Stage 8 |
| **8. Proposal Form** | `backend/agent/buyer_agent.py`<br>Line 316 | Selected `CartItem` objects | Sums DB unit prices $\times$ quantity to construct server-validated `OrderProposal`. | `OrderProposal` object | Stage 9 |
| **9. Policy Verification**| `backend/security/policy_engine.py`<br>`verify_order_proposal()`| `session_id`, `OrderProposal` | Verifies DB prices, enforces spending ceiling, checks velocity & replay attacks. | `VerificationResult` | Stage 10 |
| **10. Policy Branching**| `backend/agent/buyer_agent.py`<br>Lines 360–375 | `VerificationResult.status` | • `VALID` $\to$ Proceed to Razorpay<br>• `HITL_REQUIRED` $\to$ Pause for sign-off<br>• `REJECTED` $\to$ Abort | Status Event | Stage 11 |
| **11. Razorpay Order** | `backend/payments/razorpay_client.py`<br>`create_order()` | Amount, session, idempotency key | Creates official Razorpay order in test/mock mode with receipt ID. | `rzp_order` dict | Stage 12 |
| **12. Client Checkout**| `frontend/src/App.tsx`<br>`openRazorpayCheckout()` | `checkout` options | Loads Razorpay Standard Checkout SDK popup on client browser. | `razorpay_payment_id` | Stage 13 |
| **13. Signature Check**| `backend/payments/razorpay_client.py`<br>`verify_payment()` | Payment ID, order ID, signature | Calculates `hmac.new(secret, order_id + "|" + payment_id, sha256)`. | Verification boolean | Stage 14 |
| **14. Settlement** | `backend/payments/razorpay_client.py`<br>`simulate_payment_settlement()`| Order ID, amount | Records payment capture and marks idempotency key as consumed. | Settlement record | Stage 15 |
| **15. Audit Ledger** | `backend/audit/ledger.py`<br>`record()` | Event type, status, summary, details | Generates SHA-256 hash chained to previous record and persists to SQLite. | `AuditLog` entry | Stage 16 |
| **16. UI Finalize** | `frontend/src/App.tsx`<br>Line 930 | Completed step data | Transitions step badge to `SUCCESS`, renders order receipt, unlocks new purchase. | Final UI State | Completed |

---

## 6. Natural Language Intent Decomposition

### Real Example Walkthrough
**User Input:** `"Buy 2 braided 4K HDMI cables for office setup"` with Budget: $\text{₹3,000}$.

```
User Text: "Buy 2 braided 4K HDMI cables for office setup"
   │
   ▼
[buyer_intent.py: GeminiIntentParser]
   │
   ├── Model: gemini-3.5-flash-lite (REST Endpoint)
   ├── System Prompt: "Extract structured search intent parameters..."
   └── Response Schema: { query, category, budget, quantity, required_features }
   │
   ▼ (Output)
BuyerIntent(
    query="4K HDMI cable",
    category="cables",
    budget=3000.0,
    quantity=2,
    use_case="office setup",
    required_features=["braided", "4k"]
)
```

### Heuristic Fallback Engine
* **Why it exists:** To guarantee **100% zero-dependency local operation** even when `GEMINI_API_KEY` is missing, quota-exhausted, or returns an HTTP 400 error.
* **Extraction Logic (`buyer_agent.py`):**
  * `_extract_quantity()`: Regex `\b(\d+)\s*(units|pcs|pieces|items|cables|mice|chargers|keyboards|packs)?\b`.
  * `_extract_category()`: Keyword matching (`"cable"`/`"hdmi"` $\to$ `"cables"`, `"keyboard"`/`"mouse"` $\to$ `"peripherals"`).
  * `_extract_search_keywords()`: Scans for device identifiers (`"hdmi"`, `"hub"`, `"keychron"`, `"coffee"`, `"charger"`).

---

## 7. MCP Merchant Catalog Architecture

### Data Model & In-Memory Store
Implemented in [`backend/merchant/catalog.py`](file:///c:/INTERNSHIP/agentcart-razorpay/backend/merchant/catalog.py).

```python
class Product(BaseModel):
    id: str                          # e.g., "prod_hdmi_braided_01"
    name: str                        # e.g., "Ultra High Speed HDMI 2.1 Braided Cable (2m)"
    category: str                    # "cables"
    description: str                 # Full catalog specification
    price: float                     # e.g., 799.00 (in INR)
    stock: int                       # Real-time stock count (e.g., 45)
    specs: Dict[str, Any]            # {"resolution": "8K@60Hz, 4K@120Hz", "bandwidth": "48Gbps"}
    rating: float                    # 4.8
    merchant_id: str                 # "merchant_rzp_tech_01"
    merchant_name: str               # "CloudGear Technologies"
    compatible_product_ids: List[str]# ["prod_usb_c_hub_01"] (Used by Growth Engine)
```

### MCP Tool Pattern
In [`backend/agent/tools.py`](file:///c:/INTERNSHIP/agentcart-razorpay/backend/agent/tools.py), the catalog is exposed via structured tool calls (`tool_search_catalog`, `tool_get_product_details`), allowing AI agents to query specifications and pricing without direct database access.

---

## 8. Product Recommendation & Growth Engine

### Relevance Scoring Formula
Implemented in `buyer_agent._score_product_relevance()`:
$$\text{Score} = (\text{Item Type Match} \times 1000) + (\text{Category Match} \times 200) + (\text{Feature Matches} \times 50) + (\text{Use Case Match} \times 30)$$
* **Penalties:**
  * Item type mismatch (e.g., requested "keyboard" but item is "mouse"): $-10,000$.
  * Exceeds user budget cap: $-5,000$.

### Cross-Sell & Upsell Logic ([`backend/merchant/growth_engine.py`](file:///c:/INTERNSHIP/agentcart-razorpay/backend/merchant/growth_engine.py))
1. **Upsell Upgrade:** Discovers in-stock items in the same category with strictly superior specs whose price delta fits the user's budget.
2. **Compatible Cross-Sell:** Scans `product.compatible_product_ids` for bidirectional merchant-verified pairings (e.g., HDMI Cable + USB-C Hub).
3. **Interactive Add-to-Cart:**
   * Clicking **Add to Cart** updates the backend order proposal (`items = [base_product, cross_sell_product]`), recalculates the total, and updates the execution trace.
   * If the combined total exceeds policy thresholds, the deterministic policy engine intercepts the cart and enforces the HITL approval gate or rejection.

---

## 9. Order Proposal Construction

The backend **never trusts numbers generated by the AI agent**. It constructs proposals independently:

$$\text{Total Amount} = \sum (\text{DB Unit Price} \times \text{Quantity}) + \text{Accepted Add-ons}$$

```json
{
  "merchant_id": "merchant_rzp_tech_01",
  "items": [
    {
      "product_id": "prod_hdmi_braided_01",
      "quantity": 2,
      "unit_price": 799.0,
      "name": "Ultra High Speed HDMI 2.1 Braided Cable (2m)"
    },
    {
      "product_id": "prod_usb_c_hub_01",
      "quantity": 1,
      "unit_price": 2499.0,
      "name": "Anker 7-in-1 USB-C Hub"
    }
  ],
  "total_amount": 4097.0,
  "user_goal": "Buy 2 braided 4K HDMI cables for office setup"
}
```

---

## 10. Deterministic Policy & Security Guardrails

Implemented in [`backend/security/policy_engine.py`](file:///c:/INTERNSHIP/agentcart-razorpay/backend/security/policy_engine.py).

### Configured Thresholds
* **Autonomous Pre-Authorization Limit:** $\text{₹3,000}$ (Default). Orders $\le \text{₹3,000}$ execute autonomously.
* **Human-in-the-Loop (HITL) Threshold:** Orders between $\text{₹3,000}$ and $\text{₹10,000}$ pause for cryptographic user sign-off.
* **Hard Single-Transaction Ceiling:** $\text{₹10,000}$ (Default). Any order $> \text{₹10,000}$ is deterministically rejected.
* **Strict Mode:** Optional toggle to require human sign-off on 100% of transactions regardless of amount.

### Replay & Velocity Attack Protection
* Every proposal is assigned an idempotent SHA-256 key:
  $$\text{Idempotency Key} = \text{SHA256}(\text{session\_id} + \text{item\_ids} + \text{quantities} + \text{verified\_total})$$
* Once settled, the key is permanently marked as processed in `policy_engine._processed_keys`, preventing replay attacks.

---

## 11. Human-in-the-Loop (HITL) Approval Lifecycle

```
Order Total: ₹8,000 (Exceeds ₹3,000 Pre-Auth)
   │
   ▼
[PolicyEngine.generate_hitl_token()]
   │
   ├── Creates HMAC-SHA256 Token bound to session_id + verified_total + timestamp
   └── Emits SSE Event: status = "PENDING_APPROVAL"
   │
   ▼
[Frontend Approval Banner Displays]
   │
   ├── User clicks "Approve & Settle Razorpay"
   └── Sends POST /api/agent/approve-hitl with token & proposal
   │
   ▼
[PolicyEngine.verify_hitl_token()]
   │
   ├── Verifies HMAC signature, session match, amount integrity, and expiration (15 mins)
   ├── Consumes token (single-use replay protection)
   └── Creates Razorpay Order -> Settle
```

---

## 12. Payment Rails & Razorpay Integration

Implemented in [`backend/payments/razorpay_client.py`](file:///c:/INTERNSHIP/agentcart-razorpay/backend/payments/razorpay_client.py).

### Modes of Operation
1. **Live Test Mode (`RAZORPAY_MOCK_MODE=false`):**
   * Uses real `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET`.
   * Calls `https://api.razorpay.com/v1/orders`.
   * Pops up the real Razorpay Checkout modal on the browser.
2. **Sandbox / Mock Mode (`RAZORPAY_MOCK_MODE=true`):**
   * Built-in sandbox mode for zero-setup demonstrations.
   * Generates deterministic order IDs (`order_mock_...`) and simulates payment captures.

### Cryptographic Signature Verification
```python
def verify_payment(self, session_id: str, order_id: str, payment_id: str, signature: str) -> Dict[str, Any]:
    expected = hmac.new(
        self.key_secret.encode(),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError("Razorpay signature verification failed")
```

---

## 13. Settlement & Receipt Generation

Settlement marks the financial finality of the transaction:
1. **Order Capture:** Payment is verified via server signature or webhook.
2. **Idempotency Finalization:** Idempotency key is burned.
3. **Cryptographic Receipt:** A verified payload containing Razorpay Order ID, Payment ID, line items, and timestamp is returned to the client and sealed in the audit ledger.

---

## 14. Cryptographic Audit Ledger (SHA-256 Chaining)

Implemented in [`backend/audit/ledger.py`](file:///c:/INTERNSHIP/agentcart-razorpay/backend/audit/ledger.py).

### How Hash Chaining Works
Every event contains the hash of the *immediately preceding event*:

$$\text{Hash}_N = \text{SHA256}(\text{LogID} + \text{SessionID} + \text{Timestamp} + \text{EventType} + \text{Status} + \text{JSON(Details)} + \text{Hash}_{N-1})$$

```
[Event 1: AGENT_INTAKE]   ──► Hash_1 = SHA256(Event_1 + GENESIS)
        │
        ▼
[Event 2: POLICY_CHECK]   ──► Hash_2 = SHA256(Event_2 + Hash_1)
        │
        ▼
[Event 3: PAYMENT_CAPTURED] ──► Hash_3 = SHA256(Event_3 + Hash_2)
```

If an attacker modifies a past price or event in the SQLite database, every subsequent hash in the chain becomes invalid, immediately exposing database tampering.

---

## 15. Database & State Lifecycle

| Storage Layer | Technology | Persistence Scope | Content Stored |
| :--- | :--- | :--- | :--- |
| **Audit Logs** | SQLite (`audit_ledger.db`) | Permanent (Disk) | Immutable SHA-256 chained transaction logs |
| **Merchant Catalog** | In-Memory / CatalogDB | Runtime / Modifiable | Products, live stock counts, pricing |
| **Policy Config** | In-Memory / PolicyEngine | Runtime / Configurable| Pre-auth limits, ceilings, category filters |
| **Processed Keys** | In-Memory Set | Runtime (Session) | Burned idempotency keys for replay protection |
| **Frontend State** | React `useState` | Browser Memory | Current goal, active steps, offer decisions |

### What "Start New Purchase" / "Clear" Does
* **Cleared:** `promptGoal` (`""`), budget allocation (reset to $\text{₹3,000}$), execution trace (`steps = []`), session ID, `pendingHitl`, and `offerDecisions`.
* **Retained:** SQLite Audit Ledger records, Merchant Growth Analytics metrics, Merchant Inventory, and Policy limits.

---

## 16. Merchant Growth Analytics Metrics

Computed dynamically in [`backend/merchant/growth_engine.py`](file:///c:/INTERNSHIP/agentcart-razorpay/backend/merchant/growth_engine.py):

* **Total Settled GMV:** Sum of all successful `PAYMENT_CAPTURED` transactions on Razorpay.
* **Conversion Rate:** $\frac{\text{Settled Purchases}}{\text{Total Sessions}} \times 100$.
* **Average Order Value (AOV):** $\frac{\text{Total Revenue}}{\text{Total Purchases}}$.
* **Incremental Revenue:** Revenue generated exclusively from accepted upsells and cross-sells.
* **Upsell Acceptance Rate:** $\frac{\text{UPSELL\_ACCEPTED}}{\text{UPSELL\_PROPOSED}} \times 100$.
* **Cross-Sell Acceptance Rate:** $\frac{\text{CROSS\_SELL\_ACCEPTED}}{\text{CROSS\_SELL\_PROPOSED}} \times 100$.
* **HITL Gate Ratio:** Percentage of orders requiring human cryptographic sign-off.
* **Stockout Auto-Recoveries:** Number of times the agent autonomously recovered from an out-of-stock primary item by selecting a catalog-proven alternative.

---

## 17. Error Handling & Fail-Safe Matrix

| Trigger Event | Detection Point | Autonomous System Response |
| :--- | :--- | :--- |
| **Gemini API 400 / Timeout** | `buyer_intent.py` | Gracefully switches to regex keyword heuristic parser; transaction proceeds without interruption. |
| **Item Stockout (0 stock)** | `buyer_agent.py:207` | Logs `ERROR_RECOVERED`, queries category for in-stock substitute, and continues order. |
| **Price Surge (+80%)** | `policy_engine.py` | Detects that updated price exceeds pre-auth limit or user budget; triggers HITL gate or rejects order. |
| **Ceiling Exceeded (>₹10k)** | `policy_engine.py` | Hard rejection (`status = "REJECTED"`); halts execution and prevents Razorpay order creation. |
| **Payment Failure / Dismissal** | `main.py:289` | Records cancellation in audit ledger; leaves order marked as failed; records ₹0 revenue. |

---

## 18. Testing & Evaluation Suite

Located in [`evals/`](file:///c:/INTERNSHIP/agentcart-razorpay/evals):

1. **`test_phase1_security_ledger.py`:** Tests SHA-256 hash chaining, tamper detection, and genesis hashing.
2. **`test_phase2_gemini_agent.py`:** Validates intent extraction and heuristic fallback resilience.
3. **`test_phase3_growth_engine.py`:** Tests upsell/cross-sell generation and metric aggregation.
4. **`test_phase4_razorpay_checkout.py`:** Verifies Razorpay order creation and signature verification.
5. **`test_phase8_adversarial_security.py`:** Adversarial suite testing price tampering, replay attacks, and prompt injection attempts.

---

## 19. Complete Step-by-Step Scenario Walkthrough

**Scenario:** User executes *"Buy 2 braided 4K HDMI cables for office setup"* with $\text{₹3,000}$ budget.

1. **Intake:** User clicks **Execute Autonomous Purchase**. Frontend sends POST `/api/agent/run`.
2. **Intent Parsing:** `buyer_intent.py` extracts `category="cables"`, `qty=2`, `query="4K HDMI cable"`.
3. **MCP Search:** `tool_search_catalog` returns `prod_hdmi_braided_01` at $\text{₹799}$ each ($\text{₹1,598}$ total).
4. **Growth Engine:** Proposes compatible add-on `prod_usb_c_hub_01` ($\text{₹2,499}$).
5. **Proposal:** Constructs `OrderProposal` for $2 \times \text{₹799} = \text{₹1,598}$.
6. **Policy Engine:** Verifies $\text{₹1,598} \le \text{₹3,000}$ (Pre-Auth Limit). Status: `VALID`.
7. **Payment:** `razorpay_service` creates Razorpay order `order_rcpt_...`.
8. **Checkout:** Client completes Razorpay checkout modal. Server verifies HMAC-SHA256 signature.
9. **Settlement:** Payment captured. Event recorded with SHA-256 hash.
10. **UI Update:** Step marked as **`SUCCESS`** with verified receipt.

---

## 20. Important File Cheat Sheet

| File Path | Core Responsibility | Key Class / Function | Why It Is Critical |
| :--- | :--- | :--- | :--- |
| `backend/main.py` | API Entry point & routing | `run_agent_stream()`, `verify_razorpay_payment()` | Serves SSE stream and payment verification endpoints. |
| `backend/agent/buyer_agent.py` | Core autonomous agent loop | `BuyerAgent.run_goal_stream()` | Coordinates intent, MCP discovery, proposal, and settlement. |
| `backend/agent/buyer_intent.py` | Intent parsing & fallback | `GeminiIntentParser.parse_intent()` | Converts natural language to structured `BuyerIntent`. |
| `backend/security/policy_engine.py`| Deterministic security rules | `PolicyEngine.verify_order_proposal()` | Enforces spending limits, HITL tokens, and replay prevention. |
| `backend/payments/razorpay_client.py`| Razorpay payment rails | `RazorpayService.create_order()`, `verify_payment()` | Handles order creation, signatures, and settlement. |
| `backend/merchant/growth_engine.py`| Growth & recommendations | `GrowthEngine.interact_offer()` | Manages upsells, cross-sells, and conversion metrics. |
| `backend/audit/ledger.py` | Immutable audit ledger | `AuditLedger.record()` | Computes sequential SHA-256 cryptographic hash chains. |
| `frontend/src/App.tsx` | Single-Page React Application | `handleRunAgent()`, `handleStartNewPurchase()` | Manages UI state, SSE event streaming, and tab views. |

---

## 21. Important Data Structures

```python
# 1. BuyerIntent (backend/agent/buyer_intent.py)
class BuyerIntent(BaseModel):
    query: str
    category: Optional[str]
    budget: Optional[float]
    quantity: int = 1
    required_features: List[str] = []

# 2. OrderProposal (backend/merchant/models.py)
class OrderProposal(BaseModel):
    merchant_id: str
    items: List[CartItem]
    total_amount: float
    user_goal: str

# 3. VerificationResult (backend/security/policy_engine.py)
class VerificationResult(BaseModel):
    is_valid: bool
    status: str            # "VALID", "HITL_REQUIRED", "REJECTED"
    reason: str
    verified_total: float
    idempotency_key: str
    hitl_token: Optional[str]

# 4. AuditLog (backend/audit/models.py)
class AuditLog(BaseModel):
    id: str
    session_id: str
    timestamp: str
    event_type: str
    status: str
    summary: str
    details: Dict[str, Any]
    cryptographic_hash: str
```

---

## 22. Security Design: AI vs. Deterministic Enforcement

```
┌────────────────────────────────────────────────────────┐
│             NON-DETERMINISTIC AI LAYER                 │
│  (LLM Prompt, Intent Parsing, Product Spec Matching)   │
└──────────────────────────┬─────────────────────────────┘
                           │ Suggests Action
                           ▼
┌────────────────────────────────────────────────────────┐
│             DETERMINISTIC BACKEND GATE                 │
│  • Database Price Validation (Ignores AI price claims) │
│  • Hard Coded Mathematical Spend Limits                │
│  • Cryptographic HMAC-SHA256 HITL Sign-Off Tokens      │
│  • SHA-256 Chained Hash Audit Ledger                   │
│  • Idempotency Replay Protection                       │
└──────────────────────────┬─────────────────────────────┘
                           │ Executes Only Validated Orders
                           ▼
┌────────────────────────────────────────────────────────┐
│             RAZORPAY PAYMENT INFRASTRUCTURE            │
└────────────────────────────────────────────────────────┘
```

**Principle:** The AI agent acts as a *shopper*, but the backend policy engine acts as the *treasurer*. An AI agent can never authorize its own spending ceiling.

---

## 23. Live Demonstration Scenarios

### Scenario 1: Autonomous Pre-Authorized Purchase
* **Goal:** *"Buy 2 braided 4K HDMI cables for office setup"* (Budget: $\text{₹3,000}$).
* **Demonstrates:** Zero-click autonomous approval under the $\text{₹3,000}$ threshold.
* **Talking Point:** *"Notice how the total of ₹1,598 was automatically verified against the database and executed autonomously on Razorpay rails without interrupting the user."*

### Scenario 2: High-Value Human-in-the-Loop (HITL) Gate
* **Goal:** *"Purchase 1 Keychron K2 mechanical keyboard"* (Budget: $\text{₹8,000}$).
* **Demonstrates:** The policy engine pauses execution and requests cryptographic sign-off.
* **Talking Point:** *"Because ₹7,499 exceeds the ₹3,000 autonomous threshold, the system halts and issues a signed HITL token. Once I click 'Approve & Settle', it executes the payment."*

### Scenario 3: Hard Spending Ceiling Block
* **Goal:** *"Order 2 Logitech MX Master 3S mice"* (Budget: $\text{₹15,000}$).
* **Demonstrates:** Hard security ceiling rejection ($> \text{₹10,000}$).
* **Talking Point:** *"The order total of ₹15,998 exceeds our hard single-transaction limit of ₹10,000. The deterministic policy gate immediately aborts the order before any payment request is created."*

### Scenario 4: Interactive Cross-Sell Add-to-Cart
* **Action:** In Scenario 1, click **Add to Cart** on the USB-C Hub card ($+\text{₹2,499}$).
* **Demonstrates:** Real-time proposal recalculation ($\text{₹1,598} + \text{₹2,499} = \text{₹4,097}$), which dynamically activates the HITL gate.
* **Talking Point:** *"Adding the add-on updated our verified cart to ₹4,097. Because it crossed ₹3,000, it safely triggered our HITL gate."*

---

## 24. Recommended 3–5 Minute Demo Script

1. **0:00 - 0:45 (Problem):** Introduce the risk of AI agents holding payment cards without deterministic guardrails.
2. **0:45 - 1:30 (Scenario 1 - Autonomous Pre-Auth):** Run the 4K HDMI Cables scenario. Show live streaming steps, price calculation, and Razorpay settlement.
3. **1:30 - 2:30 (Scenario 2 - HITL Gate):** Run the Keychron Keyboard scenario. Explain the HMAC-SHA256 sign-off token. Click **Approve & Settle**.
4. **2:30 - 3:15 (Scenario 3 - Hard Policy Block):** Run the Logitech Mice scenario. Show the immediate red policy rejection.
5. **3:15 - 4:00 (Audit Ledger & Reset):** Navigate to the **Audit Ledger** tab to show the SHA-256 hash chain. Click **Start New Purchase** to demonstrate instant state reset.

---

## 25. Likely Judge & Interview Questions with Answers

1. **Q: Why not let the LLM check the budget itself?**  
   *A: LLMs can hallucinate or be bypassed via prompt injection. Deterministic Python validation guarantees 100% mathematical certainty.*
2. **Q: What is the purpose of the SHA-256 audit ledger?**  
   *A: It provides non-repudiable proof of every agent action and policy check. Modifying past records breaks the sequential hash chain.*
3. **Q: How does the system handle Gemini outages?**  
   *A: It catches API errors and seamlessly switches to the built-in regex heuristic parser without crashing the purchase flow.*
4. **Q: How does HITL prevent replay attacks?**  
   *A: HITL tokens are cryptographically signed with HMAC-SHA256, bound to the session and total amount, and burned immediately upon first use.*
5. **Q: Is Razorpay integration real or simulated?**  
   *A: Both. It features real Razorpay API order generation and Checkout SDK modal handling with server-side HMAC verification, plus a toggleable sandbox mock mode for zero-setup demonstrations.*
6. **Q: What happens if an item goes out of stock during the search?**  
   *A: The agent detects `stock == 0` and autonomously queries the category for an in-stock equivalent, logging an `ERROR_RECOVERED` event.*
7. **Q: How does the Growth Engine calculate metrics?**  
   *A: Directly from SQLite audit ledger events (`PAYMENT_CAPTURED`, `UPSELL_ACCEPTED`), ensuring metrics represent real ledger truth rather than in-memory counters.*
8. **Q: Can the AI agent modify merchant prices?**  
   *A: No. Unit prices are queried directly from the verified database during order construction.*
9. **Q: What is UAP / AP2?**  
   *A: Universal Agentic Payments / Agentic Payment Protocol concepts that formalize pre-authorized spending mandates, non-repudiable intent, and delegated checkout.*
10. **Q: What does clicking "Start New Purchase" reset?**  
    *A: It resets the goal input, steps trace, budget slider, and session variables while preserving persistent audit logs, catalog stock, and analytics.*

---

## 26. Final Mental Model (12-Step Summary)

```
1. User provides natural language goal & budget.
2. Agent parses goal into structured BuyerIntent.
3. Agent queries MCP Catalog for matching products.
4. Spec-matching algorithm ranks candidate items.
5. Growth Engine checks for compatible upgrades/add-ons.
6. Server constructs OrderProposal using database prices.
7. PolicyEngine verifies spending limits & idempotency.
8. Low-value orders (<= ₹3,000) are auto-approved.
9. High-value orders (> ₹3,000) require cryptographic HITL sign-off.
10. Razorpay creates order and verifies HMAC-SHA256 signature.
11. Transaction is settled and receipt generated.
12. Every event is hashed and chained in the SQLite Audit Ledger.
```
