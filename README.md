# AgentCart --- Agentic Commerce Infrastructure on Razorpay Rails (Track 1)

**Razorpay AI Buildathon 2026 · Track 1: AI Growth & Agentic Commerce**

AgentCart is a safety-first, agentic commerce prototype built on
Razorpay Rails. A buyer agent interprets intent, queries a live merchant
catalog, surfaces catalog-grounded recommendations (upsells and
cross-sells), and executes transactions via Razorpay Test Mode rails.
Financial authority is strictly separated from the language model: all
price calculation, policy enforcement, spending tier gating, payment
verification, and audit logging are deterministic and server-side.

------------------------------------------------------------------------

## Key Architecture Highlights

-   **Intent Extraction (Zero Financial Authority for LLM):** Gemini
    models extract buyer intent (budget, category, parameters) into
    structured JSON. The LLM has zero authority to set product prices,
    approve financial transactions, or declare payment completion.
-   **Deterministic Policy Gate:** The server recalculates cart totals
    against live merchant database prices before every transaction,
    preventing client-side or LLM price manipulation.
-   **Tiered Spending Governance:** ≤ ₹3,000 = autonomous
    pre-authorization; ₹3,001--₹10,000 = HITL approval; \> ₹10,000 =
    hard rejection.
-   **Cryptographic SHA-256 Chained Audit Ledger:** Critical events are
    cryptographically linked to the previous ledger entry, creating a
    tamper-evident audit trail.
-   **Razorpay Test Mode Rails & HMAC-SHA256 Webhook Reconciliation:**
    Razorpay orders/payments are verified server-side and webhook
    signatures are authenticated.

------------------------------------------------------------------------

## System Architecture

``` mermaid
flowchart LR
    U["Buyer Goal / React UI"] --> I["Gemini Structured Intent<br/>(Zero Financial Authority)"]
    I --> C["Live Merchant Catalog<br/>Search & Ranking"]
    C --> G["Grounded Growth Engine<br/>(Upsell / Cross-Sell)"]
    G --> P{"Deterministic Policy Gate"}
    P -->|"<= INR 3,000"| O["Razorpay Order<br/>(Auto Pre-Auth)"]
    P -->|"INR 3,001–10,000"| H["HITL Approval Sign-Off"]
    H --> O
    P -->|"> INR 10,000"| R["Reject: Exceeds Hard Cap"]
    O --> V["Server-Side Verification<br/>& HMAC Webhook Reconciliation"]
    V --> L["SHA-256 Chained Audit Ledger"]
    L --> A["Merchant Analytics Dashboard"]
```

------------------------------------------------------------------------

## Empirical Synthetic Benchmark

The synthetic benchmark (`evals/run_growth_evaluation.py`) evaluates 500
deterministic catalog sessions comparing baseline direct search against
AgentCart's intent-driven recommendations.

  ------------------------------------------------------------------------
  Metric             Baseline Direct AgentCart Intent +       Lift / Delta
                              Search    Recommendations 
  --------------- ------------------ ------------------ ------------------
  **Sessions**                   500                500                ---

  **Purchases**                  262                280  **+18 purchases**

  **Conversion                 52.4%          **56.0%**     **+3.6% lift**
  Rate**                                                

  **Average Order          ₹3,413.31      **₹3,737.24**         **+₹323.93
  Value (AOV)**                                                  (+9.5%)**

  **Revenue per            ₹1,788.57      **₹2,092.85**         **+₹304.28
  Session**                                                     (+17.0%)**

  **Upsell                       ---         **12.50%**                ---
  Acceptance                                            
  Rate**                                                

  **Cross-Sell                   ---         **22.06%**                ---
  Acceptance                                            
  Rate**                                                

  **Net                          ---    **₹152,139.00**   **+₹152,139.00**
  Incremental                                           
  Revenue**                                             
  ------------------------------------------------------------------------

*Benchmark results are synthetic and deterministic; the evaluator does
not trigger live revenue movement.*

------------------------------------------------------------------------

## Live Demo Scenarios & Test Safety Invariants

1.  **Autonomous Purchase (≤ ₹3,000):** Live price and stock are
    validated before auto-pre-authorization.
2.  **Human-in-the-Loop Approval (₹3,001--₹10,000):** `HITL_REQUIRED`
    blocks order creation until explicit user approval.
3.  **Stockout Auto-Recovery:** An unavailable item triggers an audited
    search for an in-stock category alternative.
4.  **Price-Surge Rejection:** The policy gate ignores client/LLM price
    changes and recalculates against live database prices.
5.  **Payment Gateway Failure:** Failed signature verification or
    cancellation produces a terminal failure state with no false
    success.

### Complete Safety Invariants

-   **Zero Financial Authority for LLMs:** Gemini extracts intent only;
    the server controls pricing, policy, and payments.
-   **Live Catalog Enforcement:** Cart totals are recalculated from live
    database records.
-   **Bounded Spending Tiers:** Auto ≤ ₹3,000; HITL ₹3,001--₹10,000;
    Hard Stop \> ₹10,000.
-   **Replay Protection:** Idempotency keys prevent duplicate
    ordering/settlement.
-   **Authenticated Settlement:** Webhooks require HMAC-SHA256
    verification.
-   **Tamper-Evident Ledger:** SHA-256 event chaining protects audit
    history integrity.

------------------------------------------------------------------------

## Local Run Instructions

### Prerequisites

-   Python 3.10+
-   Node.js 18+

### Backend

``` bash
cp .env.example backend/.env
cd backend
python -m pip install -r requirements.txt
python main.py
```

API: `http://localhost:8000`\
Swagger: `http://localhost:8000/docs`

### Frontend

In a separate terminal:

``` bash
cd frontend
npm install
npm run dev
```

Vite app: `http://localhost:5173`

------------------------------------------------------------------------

## Verification & Submission Suite

``` bash
# 1. Run all unit & safety invariant tests
python -m pytest evals/ -v

# 2. Run terminal demo walkthrough
python evals/demo_walkthrough.py

# 3. Run synthetic 500-session growth evaluator
python evals/run_growth_evaluation.py --sessions 500

# 4. Validate frontend production build
cd frontend && npm run build
```

**Verified status:** 66/66 tests passed and the demo walkthrough
completed with valid audit-chain verification.

------------------------------------------------------------------------

## Secret Audit & Configuration

Never commit sensitive API keys or secrets. Copy `.env.example` to
`backend/.env` for local configuration.

``` env
GEMINI_API_KEY=your_gemini_api_key_here
RAZORPAY_KEY_ID=rzp_test_your_key_id
RAZORPAY_KEY_SECRET=your_test_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
RAZORPAY_MODE=test
RAZORPAY_MOCK_MODE=true
```

-   **Mock Mode:** `RAZORPAY_MOCK_MODE=true` uses the built-in
    sandbox/mock flow for standalone testing.
-   **Test Mode:** `RAZORPAY_MOCK_MODE=false` uses Razorpay Test Mode
    credentials and validates webhook signatures with HMAC-SHA256.
