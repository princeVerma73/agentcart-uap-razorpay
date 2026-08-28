import hashlib
import json
import sqlite3
import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
from .models import AuditLogEntry

DB_PATH = os.path.join(os.path.dirname(__file__), "audit_ledger.db")

class AuditLedger:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._memory_cache: List[AuditLogEntry] = []
        self._init_db()
        self._hydrate_from_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                timestamp TEXT,
                event_type TEXT,
                status TEXT,
                summary TEXT,
                details TEXT,
                previous_hash TEXT DEFAULT 'GENESIS',
                cryptographic_hash TEXT
            )
        """)
        conn.commit()

        # Check if previous_hash column exists for schema migration
        cursor.execute("PRAGMA table_info(audit_logs)")
        columns = [column[1] for column in cursor.fetchall()]
        if "previous_hash" not in columns:
            cursor.execute("ALTER TABLE audit_logs ADD COLUMN previous_hash TEXT DEFAULT 'GENESIS'")
            conn.commit()

        conn.close()

    def _hydrate_from_db(self):
        self._memory_cache.clear()
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, session_id, timestamp, event_type, status, summary, details, previous_hash, cryptographic_hash
                FROM audit_logs
                ORDER BY rowid ASC
            """)
            rows = cursor.fetchall()
            conn.close()

            for row in rows:
                id_, session_id, ts, event_type, status, summary, details_raw, prev_hash, crypto_hash = row
                try:
                    details = json.loads(details_raw) if details_raw else {}
                except Exception:
                    details = {}

                entry = AuditLogEntry(
                    id=id_,
                    session_id=session_id,
                    timestamp=ts,
                    event_type=event_type,
                    status=status,
                    summary=summary,
                    details=details,
                    previous_hash=prev_hash or "GENESIS",
                    cryptographic_hash=crypto_hash
                )
                self._memory_cache.append(entry)
        except Exception as e:
            print(f"Error hydrating audit ledger from DB: {e}")

    def record(self, session_id: str, event_type: str, status: str, summary: str, details: Dict[str, Any]) -> AuditLogEntry:
        log_id = str(uuid.uuid4())
        ts = datetime.now(timezone.utc).isoformat()
        
        # Calculate tamper-evident hash chaining using previous entry's hash
        last_hash = self._memory_cache[-1].cryptographic_hash if self._memory_cache else "GENESIS"
        payload_to_hash = f"{last_hash}:{log_id}:{session_id}:{ts}:{event_type}:{status}:{summary}:{json.dumps(details, sort_keys=True)}"
        crypto_hash = hashlib.sha256(payload_to_hash.encode()).hexdigest()
        
        entry = AuditLogEntry(
            id=log_id,
            session_id=session_id,
            timestamp=ts,
            event_type=event_type,
            status=status,
            summary=summary,
            details=details,
            previous_hash=last_hash,
            cryptographic_hash=crypto_hash
        )
        
        self._memory_cache.append(entry)
        
        # Persist to SQLite
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_logs (id, session_id, timestamp, event_type, status, summary, details, previous_hash, cryptographic_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (entry.id, entry.session_id, entry.timestamp, entry.event_type, entry.status, entry.summary, json.dumps(entry.details), entry.previous_hash, entry.cryptographic_hash))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error persisting audit log: {e}")
            
        return entry

    def verify_chain_integrity(self) -> tuple[bool, Optional[str], str]:
        """
        Verify the tamper-evident SHA-256 hash chain across all recorded audit entries.
        Returns: (is_valid: bool, failed_entry_id: Optional[str], message: str)
        """
        if not self._memory_cache:
            return True, None, "Ledger is empty"

        expected_prev_hash = "GENESIS"

        for idx, entry in enumerate(self._memory_cache):
            if entry.previous_hash != expected_prev_hash:
                return False, entry.id, f"Broken chain link at index {idx} (ID: {entry.id}). Expected previous_hash {expected_prev_hash}, got {entry.previous_hash}"

            payload_to_hash = f"{entry.previous_hash}:{entry.id}:{entry.session_id}:{entry.timestamp}:{entry.event_type}:{entry.status}:{entry.summary}:{json.dumps(entry.details, sort_keys=True)}"
            recalculated_hash = hashlib.sha256(payload_to_hash.encode()).hexdigest()

            if entry.cryptographic_hash != recalculated_hash:
                return False, entry.id, f"Cryptographic mismatch at index {idx} (ID: {entry.id}). Recorded: {entry.cryptographic_hash}, Recalculated: {recalculated_hash}"

            expected_prev_hash = entry.cryptographic_hash

        return True, None, "Tamper-evident chain verification succeeded"

    def get_logs_by_session(self, session_id: str) -> List[AuditLogEntry]:
        return [entry for entry in self._memory_cache if entry.session_id == session_id]

    def get_all_logs(self, limit: int = 50) -> List[AuditLogEntry]:
        return self._memory_cache[-limit:][::-1]

    def clear(self):
        self._memory_cache.clear()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM audit_logs")
        conn.commit()
        conn.close()

audit_ledger = AuditLedger()

