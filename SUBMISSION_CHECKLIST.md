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

- **Unit & Security Test Suite:** `66/66 PASSED` (100% pass rate)
  - Phase 1 Security & Ledger Integrity: 7/7 PASSED
  - Phase 2 Gemini Intent & Policy: 11/11 PASSED
  - Phase 3 Growth Engine & Recommendations: 18/18 PASSED
  - Phase 4 Razorpay Checkout Integration: 2/2 PASSED
  - Phase 5 Recommendation & Catalog Integrity: 6/6 PASSED
  - Phase 6 Order Lifecycle & Terminal States: 7/7 PASSED
  - Phase 7 Growth Evaluation & Webhook Reconciliation: 4/4 PASSED
  - End-to-End Agent Scenarios: 7/7 PASSED
- **Terminal Demo Walkthrough:** Verified (`evals/demo_walkthrough.py`)
- **Synthetic Growth Evaluator:** Verified 500-session benchmark (`evals/run_growth_evaluation.py`)

---

## 3. Empirical Benchmark Summary (`evals/evaluation_results.json`)

| Metric | Baseline | AgentCart | Impact / Lift |
|---|---:|---:|---:|
| **Sessions Evaluated** | 500 | 500 | Benchmark standard |
| **Purchases Completed** | 262 | 280 | **+18 orders** |
| **Conversion Rate** | 52.4% | **56.0%** | **+3.6% conversion lift** |
| **Average Order Value (AOV)** | ₹3,413.31 | **₹3,737.24** | **+₹323.93 (+9.5%)** |
| **Revenue per Session** | ₹1,788.57 | **₹2,092.85** | **+₹304.28 (+17.0%)** |
| **Upsell Acceptance** | — | **12.50%** | Grounded same-category upgrade |
| **Cross-Sell Acceptance** | — | **22.06%** | Grounded compatible attachment |
| **Net Incremental Revenue** | — | **₹152,139.00** | Measured lift over baseline |

---

## 4. Evaluator Quick-Start Command Reference

### Environment Preparation
```bash
# Copy example environment configuration
cp .env.example backend/.env
```

### Run Tests & Verification Commands
```bash
# 1. Run complete pytest suite (66/66 tests)
python -m pytest evals/ -v

# 2. Run terminal demo walkthrough (Autonomous, HITL, Stockout Recovery)
python evals/demo_walkthrough.py

# 3. Run synthetic 500-session evaluator
python evals/run_growth_evaluation.py --sessions 500
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
- [x] **Environment Template Verified:** `.env.example` provided with safe placeholder variables.
- [x] **Webhook Security:** HMAC-SHA256 signature verification over exact raw payload body (`RAZORPAY_WEBHOOK_SECRET`).
- [x] **Idempotency & Replay Protection:** Replay-prevention window and unique request idempotency keys enforced.
- [x] **Policy Gate Hard Rules:** LLM output treats prices as zero-authority suggestions; all prices recalculated from merchant DB.
- [x] **Cryptographic Audit Ledger:** Cryptographic SHA-256 chain links every ledger record to prevent record tampering.

---

## 6. Demonstrated Safety & Failure Scenarios

1. **Autonomous Pre-Auth (≤ ₹3,000):** Auto-creates Razorpay order within pre-approved limit.
2. **HITL Approval (> ₹3,000 to ₹10,000):** Enforces explicit human confirmation prior to payment link generation.
3. **Hard Ceiling Rejection (> ₹10,000):** Strictly rejects purchases exceeding max spending threshold.
4. **Stockout Recovery (`ERROR_RECOVERED`):** Intercepts unavailable items and queries category alternatives automatically.
5. **Price-Surge Rejection:** Intercepts client-side price modifications and enforces live DB pricing.
6. **Gateway Rejection / Failure:** Ensures failed or unverified checkout sessions remain uncaptured with zero false revenue attribution.
