import os
import sys
import tempfile
import sqlite3
import pytest
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from main import app
from config import settings
from audit.ledger import AuditLedger, audit_ledger
from audit.models import AuditLogEntry
from security.policy_engine import PolicyEngine, PolicyConfig, PersistentIdempotencySet
from merchant.models import OrderProposal, CartItem
from merchant.catalog import catalog_db

@pytest.fixture(autouse=True)
def reset_system_state():
    catalog_db.reset_catalog()
    audit_ledger.clear()
    policy_engine = PolicyEngine(PolicyConfig(
        max_single_transaction_limit=10000.0,
        auto_approve_limit=3000.0,
        require_human_approval_always=False,
        idempotency_window_seconds=300
    ))
    policy_engine.processed_idempotency_keys.clear()

def test_previous_hash_chain_integrity():
    """Test 1: Verify that every recorded log entry links to the previous entry's SHA-256 hash."""
    db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db").name
    try:
        ledger = AuditLedger(db_path=db_file)
        
        e1 = ledger.record("sess_1", "TEST_EVENT", "SUCCESS", "Summary 1", {"data": "1"})
        e2 = ledger.record("sess_1", "TEST_EVENT", "SUCCESS", "Summary 2", {"data": "2"})
        e3 = ledger.record("sess_1", "TEST_EVENT", "SUCCESS", "Summary 3", {"data": "3"})

        assert e1.previous_hash == "GENESIS"
        assert e2.previous_hash == e1.cryptographic_hash
        assert e3.previous_hash == e2.cryptographic_hash

        is_valid, failed_id, msg = ledger.verify_chain_integrity()
        assert is_valid is True
        assert failed_id is None
    finally:
        if os.path.exists(db_file):
            os.remove(db_file)

def test_detection_of_modified_audit_records():
    """Test 2: Verify that tampering with any record or summary in SQLite breaks chain integrity."""
    db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db").name
    try:
        ledger = AuditLedger(db_path=db_file)
        e1 = ledger.record("sess_tamper", "TEST", "SUCCESS", "Original Summary 1", {})
        e2 = ledger.record("sess_tamper", "TEST", "SUCCESS", "Original Summary 2", {})

        is_valid, _, _ = ledger.verify_chain_integrity()
        assert is_valid is True

        # Tamper with summary of e1 in memory cache
        ledger._memory_cache[0].summary = "TAMPERED Summary 1"
        is_valid_tampered, failed_id, msg = ledger.verify_chain_integrity()
        
        assert is_valid_tampered is False
        assert failed_id == e1.id
        assert "Cryptographic mismatch" in msg or "Broken chain" in msg
    finally:
        if os.path.exists(db_file):
            os.remove(db_file)

def test_audit_db_hydration_after_restart():
    """Test 3: Verify that initializing a new AuditLedger instance loads all historical logs from SQLite."""
    db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db").name
    try:
        ledger1 = AuditLedger(db_path=db_file)
        ledger1.record("sess_restart", "START", "SUCCESS", "Started process", {"step": 1})
        ledger1.record("sess_restart", "FINISH", "SUCCESS", "Finished process", {"step": 2})

        # Simulate backend restart with a new instance using the same DB file
        ledger2 = AuditLedger(db_path=db_file)
        assert len(ledger2._memory_cache) == 2
        assert ledger2._memory_cache[0].summary == "Started process"
        assert ledger2._memory_cache[1].summary == "Finished process"

        # Chain integrity check on rehydrated instance
        is_valid, _, _ = ledger2.verify_chain_integrity()
        assert is_valid is True
    finally:
        if os.path.exists(db_file):
            os.remove(db_file)

def test_persistent_idempotency():
    """Test 4: Verify that processed idempotency keys persist in SQLite across PolicyEngine re-instantiations."""
    db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db").name
    try:
        idempotency_set1 = PersistentIdempotencySet(db_path=db_file, window_seconds=300)
        idempotency_set1.add_key("key_abc_123", session_id="sess_idemp")

        # Create second instance simulating backend restart
        idempotency_set2 = PersistentIdempotencySet(db_path=db_file, window_seconds=300)
        assert idempotency_set2.is_processed("key_abc_123") is True
    finally:
        if os.path.exists(db_file):
            os.remove(db_file)

def test_legitimate_transaction_after_idempotency_window():
    """Test 5: Verify that identical transactions are allowed if performed after the time window expires."""
    db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db").name
    try:
        policy = PolicyEngine(PolicyConfig(idempotency_window_seconds=100))
        proposal = OrderProposal(
            merchant_id="merchant_rzp_tech_01",
            items=[CartItem(product_id="prod_hdmi_cable_4k", quantity=1, unit_price=799.0, name="HDMI Cable")],
            total_amount=799.0,
            user_goal="Buy 1 cable"
        )
        
        t0 = 100000.0
        res1 = policy.verify_order_proposal("sess_window", proposal, timestamp_override=t0)
        assert res1.is_valid is True
        policy.mark_key_processed(res1.idempotency_key, "sess_window", timestamp_override=t0)

        # Attempt identical request within window -> should be blocked
        res2 = policy.verify_order_proposal("sess_window", proposal, timestamp_override=t0 + 50)
        assert res2.is_valid is False
        assert res2.status == "REJECTED_DUPLICATE"

        # Attempt identical request AFTER window (t0 + 200 > 100s window) -> should be ALLOWED
        res3 = policy.verify_order_proposal("sess_window", proposal, timestamp_override=t0 + 200)
        assert res3.is_valid is True
        assert res3.status == "AUTO_APPROVED"
    finally:
        if os.path.exists(db_file):
            os.remove(db_file)

def test_replay_protection():
    """Test 6: Verify duplicate submissions within the active window are rejected."""
    policy = PolicyEngine(PolicyConfig(idempotency_window_seconds=300))
    proposal = OrderProposal(
        merchant_id="merchant_rzp_tech_01",
        items=[CartItem(product_id="prod_hdmi_cable_4k", quantity=1, unit_price=799.0, name="HDMI Cable")],
        total_amount=799.0,
        user_goal="Buy cable"
    )
    
    t0 = 50000.0
    res1 = policy.verify_order_proposal("sess_replay", proposal, timestamp_override=t0)
    assert res1.is_valid is True
    policy.mark_key_processed(res1.idempotency_key, "sess_replay", timestamp_override=t0)

    res2 = policy.verify_order_proposal("sess_replay", proposal, timestamp_override=t0 + 10)
    assert res2.is_valid is False
    assert res2.status == "REJECTED_DUPLICATE"

def test_cors_behavior():
    """Test 7: Verify CORS response headers for configured origins vs unauthorized origins."""
    client = TestClient(app)

    # Allowed origin
    res_allowed = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert res_allowed.status_code == 200
    assert res_allowed.headers.get("access-control-allow-origin") == "http://localhost:3000"

    # Disallowed origin
    res_disallowed = client.get("/health", headers={"Origin": "http://malicious-attacker.com"})
    assert res_disallowed.headers.get("access-control-allow-origin") is None or res_disallowed.headers.get("access-control-allow-origin") != "http://malicious-attacker.com"

def test_hitl_validation():
    """Test 8: Verify server-side validation of HITL sign-off requests (proposal, total, and HMAC token)."""
    client = TestClient(app)
    session_id = "sess_hitl_test"

    proposal_dict = {
        "merchant_id": "merchant_rzp_tech_01",
        "items": [{"product_id": "prod_mech_keyboard_k2", "quantity": 1, "unit_price": 6499.0, "name": "Mechanical Keyboard"}],
        "total_amount": 6499.0,
        "user_goal": "Buy mechanical keyboard"
    }

    # 1. Attempt approval with fake / tampered total amount -> REJECTED
    res_fake_total = client.post("/api/agent/approve-hitl", json={
        "session_id": session_id,
        "proposal": proposal_dict,
        "verified_total": 1.0
    })
    assert res_fake_total.status_code == 400
    assert "mismatch" in res_fake_total.json()["detail"].lower()

    # 2. Attempt approval with invalid token -> REJECTED
    res_fake_token = client.post("/api/agent/approve-hitl", json={
        "session_id": session_id,
        "proposal": proposal_dict,
        "verified_total": 6499.0,
        "hitl_token": "fake_invalid_token_123"
    })
    assert res_fake_token.status_code == 403
    assert "invalid hitl" in res_fake_token.json()["detail"].lower()

    # 3. Valid sign-off with accurate verified total -> SUCCESS
    res_valid = client.post("/api/agent/approve-hitl", json={
        "session_id": session_id,
        "proposal": proposal_dict,
        "verified_total": 6499.0
    })
    assert res_valid.status_code == 200
    assert res_valid.json()["status"] == "SUCCESS"
    assert res_valid.json()["order"]["id"].startswith("order_")
