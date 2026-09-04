# AgentCart — 5-Minute Pitch & Live Demo Video Transcript

> **Presenter Profile:** Student Developer / Lead Architect  
> **Project Name:** **AgentCart** (Universal Agentic Payments Protocol on Razorpay Rails)  
> **Target Duration:** Approximately 5 Minutes (0:00 – 5:00)  
> **Tone:** Confident, professional, clear, articulate, and technically credible spoken English.

---

## Demo Recording Checklist

*Before you press record on OBS / Loom, verify the following setup:*

1. **Backend Server Running:**  
   `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload` in terminal (`http://127.0.0.1:8000/docs` is live).
2. **Frontend UI Running:**  
   `npm run dev` in `frontend/` directory. Open `http://localhost:5173` in a clean browser window at 100% zoom (1920x1080 resolution recommended).
3. **Database Clean / Reset:**  
   Click the **Catalog** tab, click **"Reset Store"** to ensure all standard product prices and stock quantities are clean.
4. **Policy Set to Default:**  
   In **Policy & Security** tab, confirm:
   - Auto-Approve Ceiling: **₹3,000**
   - Per-Transaction Limit: **₹10,000**
   - Daily Spending Limit: **₹25,000**
5. **Microphone Tested:**  
   Test your local microphone for both video recording and the in-app Web Speech API mic button.
6. **No Stale Tabs:**  
   Close unused browser tabs and mute system notifications.

---

## Chronological 5-Minute Video Walkthrough

```
+--------------------------------------------------------------------------------------------------+
|                                    5-MINUTE DEMO TIMELINE                                        |
|                                                                                                  |
| [0:00 - 0:30]  SECTION 1: Introduction & Problem Statement                                       |
| [0:30 - 1:30]  SECTION 2: Normal Autonomous Purchase (₹2,397 Pre-Auth)                            |
| [1:30 - 2:30]  SECTION 3: Human-in-the-Loop (HITL) Approval (₹6,499 Sign-Off)                     |
| [2:30 - 3:00]  SECTION 4: Human-in-the-Loop (HITL) Rejection (Halted / 0 Capture)                |
| [3:00 - 3:40]  SECTION 5: Hard Policy Block (> ₹10,000 Breach Blocked)                            |
| [3:40 - 4:30]  SECTION 6: Trust, Order History & Cryptographic SHA-256 Ledger                     |
| [4:30 - 5:00]  SECTION 7: Architecture Summary & Final Pitch Closing                              |
+--------------------------------------------------------------------------------------------------+
```

---

### SECTION 1 — INTRODUCTION (0:00 – 0:30)

#### [ON SCREEN]
- Start on the **Product View** homepage (`http://localhost:5173`).
- Show the clean hero header: *"Autonomous commerce, built for trust."*
- Mouse hovers smoothly over the top right badges: **Razorpay Rails**, **Policy Gate**, and **UAP / AP2**.

#### [SPOKEN DIALOGUE]
> "Hello everyone! My name is Prince, and today I am excited to present **AgentCart** — an autonomous agentic commerce protocol built on **Razorpay rails** with deterministic financial guardrails.
> 
> As AI buyer agents become mainstream, giving language models direct, unrestricted access to credit cards or payment APIs is dangerous. LLMs can hallucinate prices, miscalculate quantities, and fall victim to prompt injection.
> 
> AgentCart solves this with a core architectural principle: **Zero Financial Authority for the AI**. The language model handles reasoning and discovery, but every rupee, limit, and payment settlement is strictly verified by our deterministic Python policy engine."

---

### SECTION 2 — NORMAL AUTONOMOUS PURCHASE (0:30 – 1:30)

#### [ON SCREEN]
- [SHOW] Point the mouse at the **Agent Purchase Intent** card.
- [SHOW] Point out the **Session Pre-Auth: ₹3,000** badge in the upper right of the card.
- [CLICK] Click the **Scenario 1 (4K HDMI Cables)** quick button, OR type `"Buy 3 HDMI cables for my office"` into the goal textarea.
- [SHOW] Show the User Budget Allocation slider set to ₹3,000.
- [CLICK] Click **"Execute Autonomous Purchase"**.
- [SHOW] The page smoothly transitions into the **Purchase Execution & Settlement Trace** screen.
- [POINT OUT] Follow the live streaming steps as they appear:
  1. `Step 1: Goal Intake & Intent Parsing`
  2. `Step 2: MCP Catalog Discovery` (Found *Ultra High Speed 4K@60Hz HDMI 2.1 Braided Cable*)
  3. `Step 3: Recommendation & Growth Evaluation`
  4. `Step 4: Order Proposal Construction` ($3 \times ₹799 = \mathbf{₹2,397}$)
  5. `Step 5: Deterministic Policy Verification` (Status: `VALID_AUTONOMOUS` $\le$ ₹3,000)
  6. `Step 6: Razorpay Order Creation & Settlement` (Status: `SUCCESS`)
- [POINT OUT] Point directly at the green receipt card showing **Verified Amount: ₹2,397**, the Razorpay Order ID (`order_mock_...`), and the Payment ID (`pay_mock_...`).

#### [SPOKEN DIALOGUE]
> "Let's begin with a routine business purchase. 
> 
> I'll enter our natural language goal: *'Buy 3 HDMI cables for my office'*, with a budget of ₹3,000.
> 
> When I click **Execute Autonomous Purchase**, watch the real-time execution trace powered by Server-Sent Events.
> 
> First, our intent parser extracts the product category and quantity. Next, the agent uses Model Context Protocol tools to query the merchant's live SQLite database. It discovers the 4K braided HDMI cable at ₹799 per unit.
> 
> Notice Step 4 and 5: the server recalculates the mathematical total — exactly $3 \times ₹799 = \mathbf{₹2,397}$. Because ₹2,397 is under our **₹3,000 Auto-Approve Ceiling**, the policy engine pre-authorizes the transaction autonomously.
> 
> A Razorpay order is generated, payment is settled, and an SHA-256 audit entry is sealed — completely frictionless for routine low-value supplies."

---

### SECTION 3 — HUMAN-IN-THE-LOOP APPROVAL (1:30 – 2:30)

#### [ON SCREEN]
- [CLICK] Click **"Start New Purchase"** on the bottom toolbar or header.
- [SHOW] Point to **Scenario 2 (Keychron Keyboard)**.
- [CLICK] Click **Scenario 2**, which sets the goal to `"Purchase 1 Keychron K2 mechanical keyboard"` with a budget of ₹8,000.
- [CLICK] Click **"Execute Autonomous Purchase"**.
- [SHOW] Watch the trace execute Steps 1 through 5.
- [SHOW] Execution halts at Step 5. A distinct amber **Human-in-the-Loop Sign-off Gate** card appears with the title:  
  *"Policy Check: Order requires explicit human approval."*
- [POINT OUT] Point out the verified total **₹6,499**, the session ID, and the cryptographic single-use HMAC-SHA256 sign-off token.
- [CLICK] Click the green **"Approve & Settle Razorpay"** button.
- [SHOW] The trace completes with Step 6: `Human Approval Granted & Razorpay Settled`, and the green verified receipt appears for **₹6,499**.

#### [SPOKEN DIALOGUE]
> "Now, what happens when an agent needs to purchase a high-value item like hardware or electronics?
> 
> I'll select Scenario 2: *'Purchase 1 Keychron K2 mechanical keyboard'*.
> 
> The database finds the keyboard at ₹6,499. This amount is higher than our ₹3,000 auto-approve ceiling, but within our ₹10,000 per-transaction limit.
> 
> Notice what happens: the agent does **not** have the authority to complete this purchase alone. Execution halts safely at the **Human-in-the-Loop gate**, and our server generates a single-use, HMAC-SHA256 signed approval token.
> 
> As the human supervisor, I review the verified cart total of **₹6,499**. When I click **'Approve & Settle Razorpay'**, the backend validates the cryptographic signature, consumes the token to prevent replay attacks, creates the Razorpay order, and captures payment.
> 
> This provides the perfect balance: zero-click speed for small items, and strict human control for major expenses."

---

### SECTION 4 — HITL REJECTION (2:30 – 3:00)

#### [ON SCREEN]
- [CLICK] Click **"Start New Purchase"**.
- [CLICK] Click **Scenario 2 (Keychron Keyboard)** again.
- [CLICK] Click **"Execute Autonomous Purchase"**.
- [SHOW] The amber **Human-in-the-Loop Sign-off Gate** card appears again for ₹6,499.
- [CLICK] Click the red **"Reject Proposal"** button.
- [SHOW] Point out that the pipeline terminates immediately.
- [SHOW] The execution trace displays: `Human Approval Rejected` with message: *"Transaction for ₹6,499 was explicitly rejected by human operator. Execution halted immediately with zero financial capture."*
- [SHOW] The top status ribbon shows a rose badge: **"Order Rejected (Approval Declined)"**.

#### [SPOKEN DIALOGUE]
> "Now let's demonstrate the rejection path. 
> 
> Suppose the agent proposes the same ₹6,499 keyboard, but as the manager, I decide we don't need it right now.
> 
> I click **'Reject Proposal'**.
> 
> Instantly, execution terminates. Zero Razorpay payment calls are made, zero funds are captured, and the order status is permanently set to **REJECTED**. The rejection event is recorded directly in our audit trail with full cryptographic provenance."

---

### SECTION 5 — HARD POLICY BLOCK (3:00 – 3:40)

#### [ON SCREEN]
- [CLICK] Click **"Start New Purchase"**.
- [TYPE] In the goal textarea, type: `"Buy 13 HDMI cables for my office"`.
- [SCROLL/SLIDE] Move the budget slider up to **₹15,000**.
- [CLICK] Click **"Execute Autonomous Purchase"**.
- [SHOW] Watch the trace reach Step 4 and Step 5.
- [SHOW] Step 5 shows a red warning: `Deterministic Policy Blocked: Order amount ₹10,387 exceeds per-transaction limit of ₹10,000.00`.
- [SHOW] Top status ribbon displays **"Policy Ceiling Blocked"**.
- [POINT OUT] Explicitly highlight that **NO HITL button is shown**, **NO Razorpay API is called**, and **NO payment is created**.

#### [SPOKEN DIALOGUE]
> "What happens if an agent malfunctions or attempts a runaway purchase?
> 
> Let's test a scenario where the agent tries to order 13 HDMI cables. $13 \times ₹799 = \mathbf{₹10,387}$, which exceeds our **₹10,000 Per-Transaction Limit**.
> 
> I'll set the user budget to ₹15,000 and click Execute.
> 
> Look at Step 5. The policy engine performs a deterministic mathematical check and triggers a **Hard Policy Block**. 
> 
> Unlike the previous scenario, this does **not** ask for human approval. The transaction is rejected unconditionally by the server before any payment rail is touched. 
> 
> AgentCart enforces three immutable spending tiers:
> 1. **Auto-Approve Ceiling** at ₹3,000
> 2. **Per-Transaction Limit** at ₹10,000
> 3. **Daily Spending Limit** at ₹25,000 across all 24-hour transactions."

---

### SECTION 6 — TRUST, AUDIT & ORDER HISTORY (3:40 – 4:30)

#### [ON SCREEN]
- [CLICK] In the left navigation sidebar, click the **Order History** tab.
- [SHOW] Point out the table listing all recent orders:
  - Row 1: 4K HDMI Cables — Amount: **₹2,397** — Status: **Settled** (Green badge) — Razorpay Order & Payment ID.
  - Row 2: Keychron Keyboard — Amount: **₹6,499** — Status: **Settled** (Green badge).
  - Row 3: Keychron Keyboard — Status: **Rejected** (Rose badge).
  - Row 4: 13 HDMI Cables — Status: **Rejected / Blocked** (Rose badge).
- [CLICK] Click the **"View Logs"** button on the ₹2,397 settled order.
- [SHOW] The UI automatically switches to the **Audit Ledger** tab, filtered to that exact session.
- [POINT OUT] Point out the sequential cryptographic events:
  - `GOAL_INTAKE` $\rightarrow$ `CATALOG_SEARCH` $\rightarrow$ `POLICY_CHECK` $\rightarrow$ `PAYMENT_CAPTURED`
- [POINT OUT] Highlight the **SHA-256 hash string** on each log entry and explain hash chaining.
- [CLICK] Click **Policy & Security** tab briefly to show the live daily spending progress bar (e.g. *Spent Today: ₹8,896 / ₹25,000*).

#### [SPOKEN DIALOGUE]
> "Now let's inspect enterprise trust and governance.
> 
> In the **Order History** tab, every transaction is tracked with its authoritative database amount, session ID, Razorpay payment ID, and execution status.
> 
> When I click **'View Logs'** on our settled order, it opens our **Cryptographic Audit Ledger**.
> 
> Every step — from intent parsing to policy check and payment settlement — is chained sequentially using **SHA-256 hashing**. Each event incorporates the cryptographic digest of the previous event. 
> 
> If anyone attempts to alter a transaction amount or timestamp in the database after the fact, the entire cryptographic hash chain breaks, making tampering immediately detectable.
> 
> In the **Policy & Security** view, compliance teams can also inspect our live 24-hour daily spend gauge and adjust risk thresholds dynamically."

---

### SECTION 7 — ARCHITECTURE & CLOSING (4:30 – 5:00)

#### [ON SCREEN]
- [CLICK] Click back to the **Product** view or **Analytics** view.
- [SHOW] Show the smooth, polished UI with live GMV metrics.
- Speak directly and confidently into the camera for the closing statement.

#### [SPOKEN DIALOGUE]
> "To summarize our technical architecture:
> The buyer interacts with our **React frontend**, which streams goals to our **FastAPI backend**. The **Gemini agent** parses intent and queries the merchant catalog via MCP tools. 
> 
> The proposal passes through our **Deterministic Policy Engine**, which enforces limits and issues HMAC-signed tokens for human sign-off when needed. Approved orders settle directly over **Razorpay payment rails** and are immutably sealed in our **SHA-256 Audit Ledger**.
> 
> AgentCart proves that we do not need to choose between AI autonomy and financial safety. By stripping the AI of financial authority and enforcing deterministic guardrails, we make autonomous commerce safe, transparent, and ready for production on Razorpay rails.
> 
> Thank you!"

---

## 5-Minute Master Script (Continuous Spoken Dialogue)

*Use this clean, continuous script for rehearsal and teleprompter read-through:*

> "Hello everyone! My name is Prince, and today I am excited to present **AgentCart** — an autonomous agentic commerce protocol built on **Razorpay rails** with deterministic financial guardrails.
> 
> As AI buyer agents become mainstream, giving language models direct, unrestricted access to credit cards or payment APIs is dangerous. LLMs can hallucinate prices, miscalculate quantities, and fall victim to prompt injection.
> 
> AgentCart solves this with a core architectural principle: **Zero Financial Authority for the AI**. The language model handles reasoning and discovery, but every rupee, limit, and payment settlement is strictly verified by our deterministic Python policy engine.
> 
> Let's begin with a routine business purchase. I'll enter our natural language goal: *'Buy 3 HDMI cables for my office'*, with a budget of ₹3,000.
> 
> When I click Execute Autonomous Purchase, watch the real-time execution trace powered by Server-Sent Events. First, our intent parser extracts the product category and quantity. Next, the agent uses Model Context Protocol tools to query the merchant's live SQLite database. It discovers the 4K braided HDMI cable at ₹799 per unit.
> 
> Notice Step 4 and 5: the server recalculates the mathematical total — exactly $3 \times ₹799 = \mathbf{₹2,397}$. Because ₹2,397 is under our ₹3,000 Auto-Approve Ceiling, the policy engine pre-authorizes the transaction autonomously. A Razorpay order is generated, payment is settled, and an SHA-256 audit entry is sealed — completely frictionless for routine low-value supplies.
> 
> Now, what happens when an agent needs to purchase a high-value item like hardware or electronics? I'll select Scenario 2: *'Purchase 1 Keychron K2 mechanical keyboard'*. The database finds the keyboard at ₹6,499. This amount is higher than our ₹3,000 auto-approve ceiling, but within our ₹10,000 per-transaction limit.
> 
> Notice what happens: the agent does not have the authority to complete this purchase alone. Execution halts safely at the Human-in-the-Loop gate, and our server generates a single-use, HMAC-SHA256 signed approval token.
> 
> As the human supervisor, I review the verified cart total of ₹6,499. When I click 'Approve & Settle Razorpay', the backend validates the cryptographic signature, consumes the token to prevent replay attacks, creates the Razorpay order, and captures payment. This provides the perfect balance: zero-click speed for small items, and strict human control for major expenses.
> 
> Now let's demonstrate the rejection path. Suppose the agent proposes the same ₹6,499 keyboard, but as the manager, I decide we don't need it right now. I click 'Reject Proposal'. Instantly, execution terminates. Zero Razorpay payment calls are made, zero funds are captured, and the order status is permanently set to REJECTED with full audit provenance.
> 
> What happens if an agent malfunctions or attempts a runaway purchase? Let's test a scenario where the agent tries to order 13 HDMI cables. $13 \times ₹799 = \mathbf{₹10,387}$, which exceeds our ₹10,000 Per-Transaction Limit. I'll set the user budget to ₹15,000 and click Execute.
> 
> Look at Step 5. The policy engine performs a deterministic mathematical check and triggers a Hard Policy Block. Unlike the previous scenario, this does not ask for human approval. The transaction is rejected unconditionally by the server before any payment rail is touched. AgentCart enforces three immutable spending tiers: Auto-Approve Ceiling at ₹3,000, Per-Transaction Limit at ₹10,000, and Daily Spending Limit at ₹25,000.
> 
> Now let's inspect enterprise trust and governance. In the Order History tab, every transaction is tracked with its authoritative database amount, session ID, Razorpay payment ID, and execution status. When I click 'View Logs' on our settled order, it opens our Cryptographic Audit Ledger.
> 
> Every step — from intent parsing to policy check and payment settlement — is chained sequentially using SHA-256 hashing. Each event incorporates the cryptographic digest of the previous event. If anyone attempts to alter a transaction amount or timestamp in the database after the fact, the entire cryptographic hash chain breaks, making tampering immediately detectable. In the Policy & Security view, compliance teams can also inspect our live 24-hour daily spend gauge and adjust risk thresholds dynamically.
> 
> To summarize our technical architecture: the buyer interacts with our React frontend, which streams goals to our FastAPI backend. The Gemini agent parses intent and queries the merchant catalog via MCP tools. The proposal passes through our Deterministic Policy Engine, which enforces limits and issues HMAC-signed tokens for human sign-off when needed. Approved orders settle directly over Razorpay payment rails and are immutably sealed in our SHA-256 Audit Ledger.
> 
> AgentCart proves that we do not need to choose between AI autonomy and financial safety. By stripping the AI of financial authority and enforcing deterministic guardrails, we make autonomous commerce safe, transparent, and ready for production on Razorpay rails. Thank you!"

---

## Screen Actions (Chronological UI Execution Guide)

| Timestamp | UI Tab / Screen | Action | Target Element | Expected Visual Result |
| :---: | :---: | :---: | :---: | :---: |
| **0:00** | Product | [SHOW] | Hero Heading & Top Navigation | Clean title and Razorpay Rails / Policy Gate badges |
| **0:30** | Product | [CLICK] | Scenario 1 (4K HDMI Cables) | Goal populates: *"Buy 2 braided 4K HDMI cables..."* or type 3 cables |
| **0:45** | Product | [CLICK] | "Execute Autonomous Purchase" | SSE Trace begins animating Steps 1 to 6 |
| **1:10** | Product | [SHOW] | Green Settlement Card | Shows ₹2,397 verified total and Razorpay Order ID |
| **1:30** | Product | [CLICK] | "Start New Purchase" $\rightarrow$ Scenario 2 | Goal populates: *"Purchase 1 Keychron K2..."* (₹8k budget) |
| **1:45** | Product | [CLICK] | "Execute Autonomous Purchase" | Trace pauses at Step 5 with Yellow HITL Gate card |
| **2:10** | Product | [CLICK] | "Approve & Settle Razorpay" | Yellow card resolves $\rightarrow$ Green settled receipt (₹6,499) |
| **2:30** | Product | [CLICK] | "Start New Purchase" $\rightarrow$ Scenario 2 | Run Keychron again to show rejection |
| **2:40** | Product | [CLICK] | "Reject Proposal" | Pipeline halts $\rightarrow$ Rose badge: *"Order Rejected"* |
| **3:00** | Product | [TYPE] | Goal Textarea | Type: `"Buy 13 HDMI cables for my office"` (Budget: ₹15k) |
| **3:15** | Product | [CLICK] | "Execute Autonomous Purchase" | Trace halts at Step 5 with red *"Policy Ceiling Blocked"* |
| **3:40** | Orders | [CLICK] | "Order History" in Left Nav | Table shows all 4 orders with correct statuses & amounts |
| **4:00** | Orders | [CLICK] | "View Logs" on ₹2,397 Order | Navigates to Audit Ledger filtered to that session |
| **4:15** | Audit | [SHOW] | SHA-256 Hash Chained Cards | Highlights sequential SHA-256 hash digests |
| **4:30** | Policy | [CLICK] | "Policy & Security" Tab | Shows Daily Spending status bar (e.g. ₹8,896 / ₹25k) |
| **4:45** | Product | [CLICK] | "Product" Tab | Clean dashboard view for closing remarks |

---

## Backup Plan & Troubleshooting

*If anything unexpected occurs during a live recording, follow these verified fallback steps:*

| Issue Encountered | Root Cause | Instant Resolution / Backup Action |
| :--- | :--- | :--- |
| **Gemini API Network Timeout / Quota** | External Google API rate limit | **No action needed.** The system automatically switches to the built-in deterministic regex heuristic parser. The trace will display *"Intent parsed using deterministic fallback"* and continue smoothly. |
| **Microphone / Web Speech Permission Error** | Browser permissions blocked | **Click Preset Scenario Buttons.** Clicking Scenario 1, 2, 3, or 4 instantly populates the goal and budget without requiring speech input. |
| **Stale Catalog Prices / Stock** | Chaos test was triggered earlier | Click **Catalog** tab $\rightarrow$ Click **"Reset Store"** button. All items reset to default prices and stock in &lt; 50ms. |
| **Razorpay Live Modal Slow / Blocked** | Internet connectivity issue | Ensure `.env` has `RAZORPAY_MOCK_MODE=true` (or leave default). The sandbox mode simulates complete Razorpay HMAC order creation and payment settlement instantly offline. |
| **Daily Limit Already Reached** | Multiple prior test runs today | Open `backend/security/policy_engine.py` or reset the SQLite database in `backend/` by restarting the server or updating the daily limit slider in the **Policy & Security** tab. |

---

## Key Numbers to Remember

*Memorize these verified numbers for flawless delivery:*

* **₹799.00** — Unit price of *Ultra High Speed 4K@60Hz HDMI 2.1 Braided Cable (2M)*
* **₹2,397.00** — Total for 3 HDMI cables ($3 \times ₹799$) $\rightarrow$ Auto-approved under ceiling.
* **₹6,499.00** — Unit price of *Keychron K2 V2 Mechanical Keyboard* $\rightarrow$ Triggers HITL sign-off gate.
* **₹10,387.00** — Total for 13 HDMI cables ($13 \times ₹799$) $\rightarrow$ Exceeds ₹10,000 hard limit $\rightarrow$ Blocked.
* **₹3,000.00** — **Auto-Approve Ceiling** (default autonomous pre-authorization threshold).
* **₹10,000.00** — **Per-Transaction Limit** (hard ceiling for any single transaction).
* **₹25,000.00** — **Daily Spending Limit** (cumulative 24-hour spending budget).
* **88 / 88** — Automated tests passing in backend test suite (`python -m pytest evals/`).

---

## Questions You May Get After the Demo (Judge Q&A)

### Q1: Why can't we let the LLM handle spending limits directly?
> **Answer:** LLMs are probabilistic text predictors, not deterministic logic engines. They can hallucinate lower prices, miscalculate multiplication, or be manipulated by adversarial prompt injections in product descriptions. In AgentCart, the LLM has **zero financial authority**; all limits and arithmetic are enforced by our Python policy engine using authoritative database records.

### Q2: How does the Human-in-the-Loop (HITL) cryptographic token work?
> **Answer:** When an order exceeds ₹3,000, the server generates a single-use token signed with `HMAC-SHA256` covering the `session_id`, `verified_total`, proposal hash, and idempotency key. When the human approves, the backend verifies the signature and consumes the token. This guarantees that human approval cannot be forged, replayed, or altered for a higher amount.

### Q3: What is the difference between HITL and a Hard Policy Block?
> **Answer:** HITL is a conditional gate triggered between ₹3,001 and ₹10,000 that asks the human for explicit sign-off. A Hard Block occurs when an order exceeds ₹10,000 or the daily budget of ₹25,000; the server immediately terminates the pipeline with zero payment calls, without prompting the human.

### Q4: How does the SHA-256 Audit Ledger prevent tampering?
> **Answer:** Every audit event includes the SHA-256 hash of the previous event: $\text{Hash}_n = \text{SHA-256}(\text{Hash}_{n-1} : \text{Event}_n)$. If a malicious actor edits a past order amount in the database, the hash chain breaks from that point forward, and `verify_chain_integrity()` immediately flags the discrepancy.

### Q5: What happens if the Gemini API goes down during a transaction?
> **Answer:** AgentCart includes a resilient fallback architecture. If the Gemini API key is missing or rate-limited, `buyer_intent.py` catches the error and activates a deterministic regex heuristic parser, ensuring the pipeline completes without crashing.

### Q6: How does AgentCart prevent replay attacks and duplicate charges?
> **Answer:** Every purchase session uses a unique `session_id` and cryptographic `idempotency_key` stored in a persistent idempotency set. If a duplicate request arrives, the Policy Engine detects the existing key and blocks replay execution before creating a Razorpay order.

### Q7: Does AgentCart work with real Razorpay credentials?
> **Answer:** Yes. AgentCart supports dual modes. By setting `RAZORPAY_MOCK_MODE=false` and adding `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` in `.env`, the frontend opens the official Razorpay Checkout modal, and the backend verifies the HMAC-SHA256 payment signature server-side.

### Q8: How does the Merchant Growth Engine protect buyer budgets while offering upsells?
> **Answer:** When an upsell or cross-sell accessory is accepted (e.g. adding a ₹2,499 USB-C hub to HDMI cables), the total is recalculated mathematically ($₹2,397 + ₹2,499 = ₹4,896$). The new total is immediately fed back through the Policy Engine, dynamically triggering the HITL gate if the combined amount exceeds ₹3,000. Spending policies can never be bypassed by recommendations.

### Q9: What payment standards does AgentCart align with?
> **Answer:** AgentCart implements principles from the emerging Universal Agentic Payments (UAP / AP2) specification, specifically bounded agentic pre-authorizations, cryptographic mandate delegations, and dual-rail settlement on Razorpay.

### Q10: How does the system recover from product stockouts?
> **Answer:** If the agent's top-recommended item is out of stock in the merchant database, the orchestrator catches the stockout event, logs an `ERROR_RECOVERED` state, queries the catalog for an available alternative in the same category, and continues the proposal without failing the user session.

---

## One-Minute Architecture Explanation

*If an evaluator asks: "Can you explain your architecture in one minute?", say this:*

> "AgentCart follows a layered, zero-trust architecture for autonomous commerce:
> 
> 1. **Interaction Layer:** The user provides a goal via voice or text in our React frontend, which opens a Server-Sent Events stream with our FastAPI backend.
> 2. **Reasoning Layer:** Google Gemini (or our heuristic fallback) parses the unstructured goal into structured search parameters with zero financial authority.
> 3. **Catalog & Discovery Layer:** MCP tools search the merchant's live SQLite database for verified prices, specs, and stock.
> 4. **Deterministic Policy Layer:** A pure Python engine recalculates cart math, checks the ₹3,000 Auto-Approve Ceiling, ₹10,000 Per-Transaction Limit, and ₹25,000 Daily Limit, issuing HMAC-signed tokens for human sign-off when needed.
> 5. **Settlement Layer:** Razorpay rails handle order creation and HMAC-SHA256 signature verification.
> 6. **Cryptographic Audit Layer:** Every event is sequentially sealed into an immutable SHA-256 hash-chained ledger for forensic auditability."

---

## One-Minute Technical Deep Dive

*Key technical concepts to understand thoroughly:*

* **Bounded Autonomy:** The AI is given autonomy only within safe parameters (search, intent extraction, comparison). It is strictly stripped of the ability to finalize payments or modify monetary bounds.
* **Deterministic Policy Engine:** Pure code rules that execute mathematical comparisons ($Total \le Ceiling$) without probabilistic uncertainty.
* **HMAC-SHA256 HITL Signing:** Digital signatures created with a server secret `HITL_SIGNING_SECRET` over a payload containing `(session_id, verified_total, proposal_digest, idempotency_key, expiry)`.
* **Cryptographic Hash Chaining:** Blockchain-style data structure where row $N$ contains `SHA256(row_{N-1}.hash + row_N.data)`.
* **Idempotency & Replay Protection:** Invariant ensuring that duplicate network submissions cannot trigger secondary Razorpay authorizations.
