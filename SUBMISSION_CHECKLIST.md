# Submission Checklist — AgentCart

**Razorpay AI Buildathon 2026**
**Track 1: AI Growth & Agentic Commerce**

---

## 1. Track Fit & Submission Information

- **Project Name:** AgentCart — Agentic Commerce Infrastructure on Razorpay Rails
- **Target Track:** Track 1 — AI Growth & Agentic Commerce
- **Architecture Paradigm:** Autonomous Buyer Agent + Grounded Growth Engine + Deterministic Policy Gate + Razorpay Payment Rails + Cryptographic Audit Ledger
- **Primary LLM:** Gemini (Structured Intent Parsing with Zero Financial Authority)
- **Payment Provider:** Razorpay Test Mode Rails & Mock Sandbox Flow

---

## 2. Verification & Test Status

- **Unit & Security Test Suite:** `88/88 PASSED` (100% pass rate)
  - End-to-End Agent Scenarios: 7/7 PASSED
  - Phase 1 Security & Ledger Integrity: 10/10 PASSED
  - Phase 2 Gemini Intent & Policy: 11/11 PASSED
  - Phase 3 Growth Engine & Recommendations: 18/18 PASSED
  - Phase 4 Razorpay Checkout Integration: 2/2 PASSED
  - Phase 5 Recommendation & Catalog Integrity: 6/6 PASSED
  - Phase 6 Order Lifecycle & Terminal States: 7/7 PASSED
  - Phase 7 Growth Evaluation & Webhook Reconciliation: 4/4 PASSED
  - Phase 8 Adversarial Security & Attack Invariants: 20/20 PASSED
- **Terminal Demo Walkthrough:** Verified (`evals/demo_walkthrough.py`)
- **Synthetic Growth Evaluator:** Verified 500-session benchmark (`evals/run_growth_evaluation.py`)
- **Frontend Production Build:** Verified (`npm run build`) with zero TypeScript/bundling errors

---

## 3. Empirical Benchmark Summary (`evals/evaluation_results.json`)

| Metric | Baseline | AgentCart | Impact / Lift |
|---|---:|---:|---:|
| **Sessions Evaluated** | 500 | 500 | Shared synthetic evaluation |
| **Purchases Completed** | 260 | 260 | Shared buyer propensity baseline |
| **Conversion Rate** | 52.0% (95% CI ±4.38%) | **52.0%** (95% CI ±4.38%) | Fair baseline comparison |
| **Average Order Value (AOV)** | ₹3,737.49 (95% CI ±367.89) | **₹3,801.31** (95% CI ±370.39) | **+₹63.82 (+1.71%)** |
| **Revenue per Session** | ₹1,943.49 | **₹1,976.68** | **+₹33.19 (+1.71%)** |
| **Upsell Acceptance** | — | **22.22%** | Grounded same-category upgrade |
| **Cross-Sell Acceptance** | — | **11.48%** | Grounded compatible attachment |
| **Attribution: Base Product Revenue** | ₹971,747.00 | **₹971,747.00** | 100% catalog-grounded base |
| **Attribution: Upsell Incremental** | — | **₹8,000.00** | Upgrade price delta |
| **Attribution: Cross-Sell Incremental** | — | **₹8,593.00** | Compatible attachment value |
| **Net Incremental Revenue** | — | **₹16,593.00** | Measured lift over baseline |

---

## 4. Evaluator Quick-Start Command Reference

### Environment Preparation
```bash
# Copy example environment configuration
cp .env.example backend/.env
```

### Run Tests & Verification Commands
```bash
# 1. Run complete pytest suite (88/88 tests)
python -m pytest evals/ -v

# 2. Run terminal demo walkthrough (5 Scenarios: Autonomous, HITL, Stockout, Price Surge, Failure)
python evals/demo_walkthrough.py

# 3. Run synthetic 500-session evaluator
python evals/run_growth_evaluation.py --sessions 500

# 4. Run frontend production build
cd frontend && npm run build
```

### Run Local Backend & Frontend Application
```bash
# Terminal 1: Backend API (http://localhost:8000)
cd backend
python -m pip install -r requirements.txt
python main.py

# Terminal 2: Frontend Web App (http://localhost:5173)
cd frontend
npm install
npm run dev
```

---

## 5. Security Audit & Secret Hygiene

- [x] **Zero Hardcoded Secrets:** No live Razorpay keys or Gemini secrets committed to Git repository.
- [x] **Environment Template Verified:** `.env.example` provided with safe placeholder variables (`HITL_SIGNING_SECRET`, `AGENTCART_DEMO_MODE`, etc.).
- [x] **Mandatory Cryptographic HITL Signing:** HMAC-SHA256 token bound to session, order/cart items, verified amount, and expiration with single-use replay protection.
- [x] **Webhook Security:** HMAC-SHA256 signature verification over exact raw payload body (`RAZORPAY_WEBHOOK_SECRET`).
- [x] **Idempotency & Replay Protection:** Persistent SQLite-backed idempotency records preventing duplicate ordering/settlement.
- [x] **Immutable Policy Gate:** LLM output treats prices as zero-authority suggestions; all prices recalculated from live merchant DB with server-enforced hard bounds (≤ ₹3,000 auto, ≤ ₹10,000 max).
- [x] **Cryptographic Audit Ledger:** Tamper-evident SHA-256 event chaining links every ledger record to prevent modification or deletion.
- [x] **Demo Mode Guard:** `AGENTCART_DEMO_MODE=false` disables simulation and destructive endpoints in production.

---

## 6. Demonstrated Safety & Failure Scenarios

1. **Autonomous Pre-Auth (≤ ₹3,000):** Auto-creates Razorpay order within pre-approved limit.
2. **HITL Approval (> ₹3,000 to ₹10,000):** Enforces cryptographic token sign-off prior to payment order generation with single-use consumption.
3. **Hard Ceiling Rejection (> ₹10,000):** Strictly rejects purchases exceeding max spending threshold.
4. **Stockout Recovery (`ERROR_RECOVERED`):** Intercepts unavailable items and queries category alternatives automatically.
5. **Price-Surge Rejection:** Intercepts client-side price modifications and enforces live DB pricing.
6. **Gateway Rejection / Failure:** Ensures failed or unverified checkout sessions remain uncaptured with zero false revenue attribution.
