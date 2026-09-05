# AgentCart — 5-Minute Pitch & Live Demo Recording Script

> **Presenter / Speaker:** Prince  
> **Project:** **AgentCart** (Autonomous Commerce Protocol on Razorpay Rails)  
> **Target Duration:** Exactly 5 Minutes (0:00 – 5:00)  
> **Format:** Screen Recording + Voiceover (No webcam/face camera needed)  
> **Tone:** Confident, natural, professional, conversational, and articulate.

---

## Chronological Overview

| Timestamp | Section | Visual Focus | Action / Demo |
| :--- | :--- | :--- | :--- |
| **0:00 – 0:30** | **Introduction** | Product View Homepage | Problem Statement & Zero Financial Authority Principle |
| **0:30 – 1:20** | **Demo 1: Autonomous Purchase** | Intent Form $\rightarrow$ Live Execution Trace | Buy 2 HDMI Cables ($\mathbf{₹1,598} < \text{₹3,000}$) $\rightarrow$ Auto-Settled |
| **1:20 – 2:15** | **Demo 2: Human-in-the-Loop** | Intent Form $\rightarrow$ HITL Gate Screen | Buy 10 HDMI Cables ($\mathbf{₹7,990}$) $\rightarrow$ Human Approves & Settles |
| **2:15 – 2:45** | **Demo 3: Human Rejection** | Re-run High-Value Goal $\rightarrow$ HITL Gate | Buy 10 HDMI Cables $\rightarrow$ Click **"Reject Proposal"** $\rightarrow$ Halted |
| **2:45 – 3:25** | **Demo 4: Hard Policy Block** | Intent Form $\rightarrow$ Hard Block Trace | Buy 13 HDMI Cables ($\mathbf{₹10,387} > \text{₹10,000}$) $\rightarrow$ Server Hard Block |
| **3:25 – 4:05** | **Order History & Audit Ledger** | Order History Tab $\rightarrow$ Audit Ledger Tab | Trace orders, sessions, and SHA-256 cryptographic chain |
| **4:05 – 4:35** | **Architecture Walkthrough** | Architecture Diagram / Document | Trace request lifecycle from User to Razorpay to Audit DB |
| **4:35 – 5:00** | **Closing & Summary** | Final Product Screen | Trust, Guardrails & Razorpay Rails |

---

## 5-Minute Spoken Script with Mouse Directions

---

### [0:00 – 0:30] SECTION 1: INTRODUCTION

#### 🖱️ MOUSE & SCREEN ACTIONS:
1. Open browser in full screen on `http://localhost:5173`.
2. Start on the **Product** tab.
3. Smoothly hover your mouse over the top banner heading: *"Autonomous commerce, built for trust."*
4. Move your mouse to the top-right badges: **Razorpay Rails**, **Policy Gate**, and **UAP / AP2**.

#### 🎙️ SPOKEN LINES:
> "Hello everyone, my name is Prince, and today I am excited to present **AgentCart** — an autonomous commerce protocol built on **Razorpay rails** with deterministic financial guardrails.
> 
> As autonomous AI buyer agents become mainstream, giving language models direct, unrestricted access to credit cards or payment APIs is dangerous. Language models can hallucinate prices, miscalculate quantities, or fall victim to prompt injection.
> 
> AgentCart solves this with a core architectural principle: **Zero Financial Authority for the AI**. The language model handles reasoning and discovery, but every single rupee, spending limit, and payment settlement is strictly verified by our deterministic backend policy engine."

---

### [0:30 – 1:20] SECTION 2: DEMO 1 — AUTONOMOUS PURCHASE

#### 🖱️ MOUSE & SCREEN ACTIONS:
1. Hover your mouse over the **Agent Purchase Intent** card.
2. Point at the **Session Pre-Auth: ₹3,000** badge in the upper-right corner of the card.
3. In the **Natural Language Goal** text box, make sure it says:  
   `"Buy 2 braided 4K HDMI cables for office setup"`  
   *(Or click the Scenario 1 quick button).*
4. Point at the **User Budget Allocation** slider set at **₹3,000**.
5. Click the blue button: **"Execute Autonomous Purchase"**.
6. The screen smoothly transitions to the **Execution Activity Trace**.
7. As the steps stream in real-time, move your mouse down along the steps:
   - Point at `Step 1: Goal Intake & Intent Parsing`
   - Point at `Step 2: MCP Catalog Discovery` (discovering the 4K HDMI Cable at ₹799)
   - Point at `Step 4: Order Proposal Construction` (2 units × ₹799 = ₹1,598)
   - Point at `Step 5: Deterministic Policy Verification` (Status: `VALID_AUTONOMOUS`)
   - Point at `Step 6: Razorpay Order Creation & Settlement` (Status: `SUCCESS`)
8. Point at the green settlement receipt card showing **Verified Total: ₹1,598** and the Razorpay Payment ID.

#### 🎙️ SPOKEN LINES:
> "Let's see our first scenario: a routine, low-value business purchase.
> 
> Here, our goal is: *'Buy 2 braided 4K HDMI cables for office setup'*, with a budget of ₹3,000.
> 
> When I click **Execute Autonomous Purchase**, watch the real-time execution trace powered by Server-Sent Events.
> 
> First, our intent parser extracts the structured intent. Next, the agent uses Model Context Protocol tools to query the merchant's live SQLite catalog, locating the braided HDMI cable at ₹799 per unit.
> 
> In Step 4 and 5, the backend deterministic policy engine recalculates the exact total: **2 cables at ₹799 equals ₹1,598**.
> 
> Because ₹1,598 is well below our **₹3,000 Auto-Approve Ceiling**, the policy engine pre-authorizes the purchase autonomously.
> 
> A Razorpay order is instantly created, payment is settled, and an immutable audit record is sealed — completely frictionless for routine low-value supplies."

---

### [1:20 – 2:15] SECTION 3: DEMO 2 — HUMAN-IN-THE-LOOP (HITL) APPROVAL

#### 🖱️ MOUSE & SCREEN ACTIONS:
1. Click the top-right button **"Launch Purchase"** (or top left "Product" tab) to return to the intent form.
2. In the **Natural Language Goal** box, type:  
   `"Buy 10 braided 4K HDMI cables for office setup"`
3. Move the **User Budget Allocation** slider to **₹9,500**.
4. Click **"Execute Autonomous Purchase"**.
5. Follow the execution steps as they stream.
6. When Step 5 runs, the amber **Human-in-the-Loop Sign-off Required** card appears at the top.
7. Move your mouse to point at:
   - The badge: **"High-Value Threshold Gate"**
   - The verified amount: **"₹7,990"**
   - The merchant name: **"CloudGear Technologies"**
8. Point at the green button: **"Approve & Settle Razorpay"** and click it.
9. Watch the settlement succeed and the green receipt appear for ₹7,990.

#### 🎙️ SPOKEN LINES:
> "Now let's scale this up to a higher-value purchase.
> 
> I'll enter: *'Buy 10 braided 4K HDMI cables for office setup'*, and adjust our budget to ₹9,500.
> 
> When I execute, the agent finds the same product, but now the math is: **10 cables at ₹799 equals ₹7,990**.
> 
> Notice what happens: ₹7,990 is above our ₹3,000 autonomous ceiling, but within our ₹10,000 transaction ceiling.
> 
> The deterministic policy engine immediately halts autonomous execution and generates a single-use, HMAC-SHA256 signed sign-off token.
> 
> **The AI cannot approve this transaction by itself.** It requires explicit human authorization.
> 
> As the business owner, I can review the verified merchant, the exact items, and the total. When I click **Approve & Settle Razorpay**, the server cryptographically verifies and consumes the token, creating and settling the Razorpay payment securely."

---

### [2:15 – 2:45] SECTION 4: DEMO 3 — HUMAN REJECTION

#### 🖱️ MOUSE & SCREEN ACTIONS:
1. Click **"Launch Purchase"** to return to the intent form.
2. Enter the same high-value goal: `"Buy 10 braided 4K HDMI cables for office setup"`, with budget at **₹9,500**.
3. Click **"Execute Autonomous Purchase"**.
4. When the amber **Human-in-the-Loop Sign-off Required** card appears for ₹7,990, hover over the red button: **"Reject Proposal"**.
5. Click **"Reject Proposal"**.
6. Point at the updated step status showing `REJECTED` and the message: *"Human user rejected transaction sign-off"*.

#### 🎙️ SPOKEN LINES:
> "Now, what happens if the human rejects the purchase proposal? Let's run that same high-value scenario again.
> 
> The system pauses at the HITL gate. This time, I'll click **Reject Proposal**.
> 
> Immediately, the execution is halted. The HMAC token is invalidated, zero funds are captured, no Razorpay charge is made, and the explicit rejection is permanently logged to our audit trail."

---

### [2:45 – 3:25] SECTION 5: DEMO 4 — HARD POLICY BLOCK

#### 🖱️ MOUSE & SCREEN ACTIONS:
1. Click **"Launch Purchase"** to return to the intent form.
2. In the **Natural Language Goal** box, type:  
   `"Buy 13 HDMI cables for my office"`
3. Move the **User Budget Allocation** slider to **₹15,000**.
4. Click **"Execute Autonomous Purchase"**.
5. Watch the trace stream:
   - In Step 4: Cart total is calculated as $13 \times ₹799 = \mathbf{₹10,387}$.
   - In Step 5: The card turns red with status `REJECTED` / `FAILED`.
6. Point your mouse directly at the red error text:  
   *"Order total ₹10,387.00 exceeds maximum single transaction limit of ₹10,000.00"*.

#### 🎙️ SPOKEN LINES:
> "Next, let's test our hard security perimeter.
> 
> I will instruct the agent: *'Buy 13 HDMI cables for my office'*, and set the budget to ₹15,000.
> 
> Even though the buyer provided a ₹15,000 budget, our backend enforces an immutable **₹10,000 Per-Transaction Limit**.
> 
> The policy engine calculates: **13 cables at ₹799 equals ₹10,387**.
> 
> Because ₹10,387 exceeds ₹10,000, the server triggers a **Hard Policy Block**.
> 
> Here is the critical difference between HITL and a Hard Block:
> - Between ₹3,000 and ₹10,000, a human can choose to sign off.
> - But above ₹10,000, the server rejects the transaction outright. There is no autonomous approval, no human override button, and no Razorpay order is ever created. The system is completely tamper-proof against runaway agent loops."

---

### [3:25 – 4:05] SECTION 6: ORDER HISTORY & CRYPTOGRAPHIC AUDIT LEDGER

#### 🖱️ MOUSE & SCREEN ACTIONS:
1. Move your mouse to the left navigation bar and click **Order History** (clock icon).
2. Point your mouse at the rows in the table:
   - The settled ₹1,598 autonomous order (Status: **Settled** in green)
   - The approved ₹7,990 order (Status: **Settled**)
   - The rejected and blocked attempts (Status: **Rejected** in red)
   - Point out the Session IDs, Order IDs, and Razorpay Payment IDs.
3. Now, click on the left navigation bar: **Audit Ledger** (document icon).
4. Scroll down slowly through the audit log entries.
5. Point at:
   - The event types: `AGENT_INTAKE`, `POLICY_CHECK`, `HITL_APPROVED`, `PAYMENT_CAPTURED`, `POLICY_CHECK (REJECTED)`.
   - The **Cryptographic Hash (SHA-256)** displayed on each entry.
   - Point out the hash chain linkage.

#### 🎙️ SPOKEN LINES:
> "Let's inspect our governance and tracking layers.
> 
> In the **Order History** tab, we see an authoritative record of every transaction attempt — from our settled ₹1,598 autonomous purchase, to our approved ₹7,990 order, to our rejected and blocked sessions, complete with timestamps and Razorpay IDs.
> 
> Next, in the **Audit Ledger** tab, AgentCart maintains a tamper-evident, SHA-256 chained cryptographic log.
> 
> Every single event — goal intake, price verification, HITL decisions, and payment settlements — is cryptographically hashed and linked to the previous entry.
> 
> If any record in this ledger is tampered with or modified, the hash chain breaks immediately, guaranteeing non-repudiable auditability for financial compliance."

---

### [4:05 – 4:35] SECTION 7: ARCHITECTURE & SECURITY BOUNDARY

#### 🖱️ MOUSE & SCREEN ACTIONS:
1. Switch to the tab displaying the **Architecture Specification** (`docs/ARCHITECTURE.md` rendered preview or open `docs/architecture.mmd`).
2. Move your mouse along the diagram flow as you speak:
   - Point at **User & React Frontend**
   - Move to **FastAPI Backend Gateway**
   - Move to **Gemini Intent Layer & Buyer Agent**
   - Move to **MCP Tools & Live Merchant Catalog**
   - Move to **Deterministic Policy Engine** (highlight the 3 tiers: Autonomous $\le$ ₹3,000, HITL ₹3,001–₹10,000, Hard Block > ₹10,000)
   - Move to **Razorpay Payment Rails & Settlement**
   - Move to **SHA-256 Audit Ledger**.

#### 🎙️ SPOKEN LINES:
> "Let's review the architectural flow that makes this possible.
> 
> 1. The user inputs their goal via text or speech in our **React frontend**.
> 2. The request reaches our **FastAPI backend**, which streams execution events via Server-Sent Events.
> 3. The **Gemini Intent Layer** extracts structured parameters, and the **Buyer Agent** uses **MCP tools** to query live product data from the merchant's authoritative SQLite database.
> 4. Once an order proposal is constructed, it enters our **Deterministic Policy Engine**.
> 5. The policy engine recalculates prices mathematically from database truth and routes the transaction:
>    - Under ₹3,000: **Autonomous Pre-Auth**
>    - ₹3,001 to ₹10,000: **HMAC-SHA256 Signed HITL Gate**
>    - Over ₹10,000: **Hard Policy Block**
> 6. Validated orders are executed through **Razorpay Payment Rails**, and every state transition is sealed into the **SHA-256 Cryptographic Audit Ledger**.
> 
> **The AI handles reasoning and discovery, while the deterministic backend controls financial authorization.**"

---

### [4:35 – 5:00] SECTION 8: CLOSING

#### 🖱️ MOUSE & SCREEN ACTIONS:
1. Switch back to the clean **Product** view on `http://localhost:5173`.
2. Move mouse smoothly to center screen over the tagline.
3. Keep the mouse still for the final statement.

#### 🎙️ SPOKEN LINES:
> "To conclude: AgentCart bridges the gap between autonomous AI efficiency and bulletproof enterprise financial security.
> 
> By combining AI-driven catalog discovery, strict deterministic spending guardrails, cryptographic human-in-the-loop oversight, and native Razorpay payment rails, we make autonomous commerce safe, transparent, and scalable.
> 
> **AgentCart is autonomous commerce, built for trust.**
> 
> Thank you."

---

## Final Recording Checklist

*Before starting your screen and voice recording, make sure:*

- [ ] **Browser Full Screen:** Maximize browser window (`F11` or full screen mode at 100% zoom, 1920×1080).
- [ ] **No Face Camera Required:** Video is screen recording + clear microphone voiceover only.
- [ ] **Mouse Pointer Visible:** Ensure screen recorder (OBS / Loom) has cursor capture enabled.
- [ ] **Pointer Discipline:** Keep mouse pointer steady and near the exact UI element, button, or step being discussed.
- [ ] **Pacing:** Pause for 1–2 seconds after major actions (e.g. after clicking Execute, after HITL card appears, after settlement receipt loads).
- [ ] **No Source Code Screen:** Do not open VS Code or source files during the recording; keep the view on the UI and the clean architecture diagram.
- [ ] **No Terminal on Screen:** Keep terminal minimized in the background.
- [ ] **Architecture Section:** Open `docs/ARCHITECTURE.md` or the visual Mermaid diagram during the architecture section at [4:05].
- [ ] **Verified Amounts:** Use the exact verified amounts from the application:
  - Demo 1: 2 cables × ₹799 = **₹1,598** ($\le$ ₹3,000)
  - Demo 2: 10 cables × ₹799 = **₹7,990** (HITL ₹3,001–₹10,000)
  - Demo 3: Rejection of **₹7,990** proposal
  - Demo 4: 13 cables × ₹799 = **₹10,387** ($>$ ₹10,000 Hard Block)
- [ ] **Factual Claims:** Only discuss features fully implemented and verified in the codebase.
- [ ] **Timing:** Keep total video duration within 4:45 – 5:05 minutes.
