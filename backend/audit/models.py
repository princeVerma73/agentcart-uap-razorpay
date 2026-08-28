from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class AuditLogEntry(BaseModel):
    id: str
    session_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_type: str  # e.g., 'AGENT_THOUGHT', 'TOOL_CALL', 'POLICY_CHECK', 'HITL_REQUIRED', 'PAYMENT_EXECUTED', 'ERROR_RECOVERED'
    status: str      # 'SUCCESS', 'WARNING', 'REJECTED', 'PENDING_APPROVAL'
    summary: str
    details: Dict[str, Any] = Field(default_factory=dict)
    previous_hash: Optional[str] = "GENESIS"
    cryptographic_hash: Optional[str] = None

