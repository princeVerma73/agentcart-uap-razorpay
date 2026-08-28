# AgentCart — Agentic Commerce Infrastructure on Razorpay Rails (Track 1)

**Razorpay AI Buildathon 2026 · Track 1: AI Growth & Agentic Commerce**

AgentCart is a safety-first, agentic commerce prototype built on Razorpay Rails. A buyer agent interprets intent, queries a live merchant catalog, surfaces catalog-grounded recommendations (upsells and cross-sells), and executes transactions via Razorpay Test Mode rails. Financial authority is strictly separated from the language model: all price calculation, policy enforcement, spending tier gating, payment verification, and audit logging are deterministic and server-side.

---

## Key Architecture Highlights

- **Intent Extraction (Zero Financial Authority for LLM):** Gemini models extract buyer intent (budget, category, parameters) into structured JSON. The LLM has zero authority to set product prices, approve financial transactions, or declare payment completion.
- **Deterministic Policy Gate (Live DB Price Enforcement & Anti-Hallucination):** The server recalculates cart totals against live merchant database prices before every transaction, completely neutralizing client-side or LLM price hallucination/surges.
- **Tiered Spending Governance:**
  - **≤ ₹3,000:** Autonomous Pre-Authorization (`AUTO_APPROVED`).
  - **₹3,001 – ₹10,000:** Human-in-the-Loop (`HITL_REQUIRED`) requiring explicit user sign-off.
  - **> ₹10,000:** Hard Spending Cap (`REJECTED_EXCEEDS_CAP`).
- **Cryptographic SHA-256 Chained Audit Ledger:** Every critical event (intent parsing, policy decision, pre-auth, checkout, webhook capture) is cryptographically bound using SHA-256 hashes linking back to the previous entry, establishing a tamper-evident audit trail.
- **Razorpay Test Mode Rails & HMAC-SHA256 Webhook Reconciliation:** Direct integration with Razorpay Order & Payment APIs (`rzp_test_*`) and signed webhook payload verification (`RAZORPAY_WEBHOOK_SECRET`) to prevent unpaid status overrides.

---

## System Architecture

```mermaid
flowchart LR
    U[Buyer Goal / React UI] --> I[Gemini Structured Intent\n(Zero Financial Authority)]
    I --> C[Live Merchant Catalog\nSearch & Ranking]
    C --> G[Grounded Growth Engine\n(Upsell / Cross-Sell)]
    G --> P{Deterministic Policy Gate}
    P -->|<= INR 3,000| O[Razorpay Order\n(Auto Pre-Auth)]
    P -->|INR 3,001–10,000| H[HITL Approval Sign-Off]
    H --> O
    P -->|> INR 10,000| R[Reject: Exceeds Hard Cap]
    O --> V[Server-Side Verification\n& HMAC Webhook Reconciliation]
    V --> L[SHA-256 Chained Audit Ledger]
    L --> A[Merchant Analytics Dashboard]
```

---

## Empirical Synthetic Benchmark

The synthetic benchmark (`evals/run_growth_evaluation.py`) evaluates 500 deterministic catalog sessions comparing baseline direct search against AgentCart's intent-driven recommendations. Results are persisted in [`evals/evaluation_results.json`](evals/evaluation_results.json).

| Metric | Baseline Direct Search | AgentCart Intent + Recommendations | Lift / Delta |
|---|---:|---:|---:|
| **Sessions** | 500 | 500 | — |
| **Purchases** | 262 | 280 | **+18 purchases** |
| **Conversion Rate** | 52.4% | **56.0%** | **+3.6% lift** |
| **Average Order Value (AOV)** | ₹3,413.31 | **₹3,737.24** | **+₹323.93 (+9.5%)** |
| **Revenue per Session** | ₹1,788.57 | **₹2,092.85** | **+₹304.28 (+17.0%)** |
| **Upsell Acceptance Rate** | — | **12.50%** | — |
| **Cross-Sell Acceptance Rate** | — | **22.06%** | — |
| **Net Incremental Revenue** | — | **₹152,139.00** | **+₹152,139.00** |

*Note: Benchmark evaluation runs on synthetic catalog sessions for repeatable, deterministic measurement; it does not trigger live revenue movement.*

---

## Live Demo Scenarios & Test Safety Invariants

AgentCart includes 5 interactive demo flows available via the React frontend and the terminal walkthrough script (`evals/demo_walkthrough.py`):

1. **Autonomous Purchase (≤ ₹3,000):**
   - *Flow:* User requests a product within ₹3,000 (e.g., mechanical keyboard at ₹2,499).
   - *Invariant:* Policy engine validates live price, verifies stock, and auto-pre-authorizes Razorpay order creation (`AUTO_APPROVED`).
2. **Human-in-the-Loop Approval (₹3,001–₹10,000):**
   - *Flow:* User selects a premium item (e.g., Keychron K2 at ₹6,499).
   - *Invariant:* Policy engine enforces `HITL_REQUIRED`. Order is created only after explicit user approval, generating a Razorpay Checkout link.
3. **Stockout Auto-Recovery:**
   - *Flow:* Requested product is out of stock in the merchant database.
   - *Invariant:* Agent catches stockout, records an `ERROR_RECOVERED` event in audit log, automatically searches for an in-stock category alternative, and presents it to the buyer.
4. **Price-Surge Rejection & Anti-Hallucination:**
   - *Flow:* Client or LLM attempts to pass a modified/discounted item price.
   - *Invariant:* Policy gate overrides client payload by recalculating total directly against live database prices. Unapproved price changes are rejected (`REJECTED_PRICE_MISMATCH`).
5. **Payment Gateway Failure / Rejection:**
   - *Flow:* Razorpay payment signature verification fails or Checkout is cancelled.
   - *Invariant:* System records terminal failure state, rejects revenue capture, and blocks ledger balance updates. No false success states occur.

### Complete Safety Invariants Summary
- **Zero Financial Authority for LLMs:** Gemini extracts structured intent only; server enforces pricing, policy, and payments.
- **Live Catalog Enforcement:** Server recalculates cart totals against live database records.
- **Bounded Spending Tiers:** Auto ≤ ₹3,000; HITL ₹3,001–₹10,000; Hard Stop > ₹10,000.
- **Replay Protection:** Idempotency keys prevent double ordering or duplicate settlement.
- **Authenticated Settlement:** Webhooks require HMAC-SHA256 signature verification over raw bytes (`RAZORPAY_WEBHOOK_SECRET`).
- **Tamper-Evident Ledger:** Cryptographic SHA-256 hash chaining guarantees audit trail integrity.

---

## Local Run Instructions

### Prerequisites
- Python 3.10+
- Node.js 18+

### 1. Backend Setup & Run

```bash
# Copy sample environment configuration
cp .env.example backend/.env

# Install backend dependencies
cd backend
python -m pip install -r requirements.txt

# Start FastAPI backend server
python main.py
```
The API server will run at `http://localhost:8000` (OpenAPI Swagger documentation at `http://localhost:8000/docs`).

### 2. Frontend Setup & Run

In a separate terminal window:

```bash
cd frontend
npm install
npm run dev
```
The Vite React application will run at `http://localhost:5173`.

---

## Verification & Submissions Suite

Run the full evaluation and test suite locally:

```bash
# 1. Run all unit & safety invariant tests (66 tests)
python -m pytest evals/ -v

# 2. Run terminal interactive demo walkthrough
python evals/demo_walkthrough.py

# 3. Run synthetic 500-session growth evaluator
python evals/run_growth_evaluation.py --sessions 500

# 4. Validate frontend production build
cd frontend && npm run build
```

---

## Secret Audit & Configuration

Never commit sensitive API keys or secrets. Copy `.env.example` to `backend/.env` for local configuration.

```env
GEMINI_API_KEY=your_gemini_api_key_here
RAZORPAY_KEY_ID=rzp_test_your_key_id
RAZORPAY_KEY_SECRET=your_test_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
RAZORPAY_MODE=test
RAZORPAY_MOCK_MODE=true
```

- **Mock Mode (`RAZORPAY_MOCK_MODE=true`):** Uses built-in Razorpay sandbox flow for standalone testing without real credentials.
- **Test Mode (`RAZORPAY_MOCK_MODE=false`):** Integrates with live Razorpay Test Mode dashboard credentials. Webhook endpoint strictly validates `RAZORPAY_WEBHOOK_SECRET` via HMAC-SHA256 signature checking.
