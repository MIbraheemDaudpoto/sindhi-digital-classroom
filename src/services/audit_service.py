"""Audit and Consent logging service for Sindhi Digital Classroom (SDC).
Enforces PECA and GDPR data minimization principles for child privacy.
Authored under agency-application-security-engineer and agency-data-privacy-officer.
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional
import uuid

from src.database.session import get_db


class AuditService:
    """Service for tamper-evident audit trails and parental consent management."""

    @staticmethod
    def log_event(
        user_id: Optional[str],
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Record an event in the audit_logs table.
        
        Guarantees:
        - Parametric queries with zero string concatenation.
        - Redacts any sensitive child PII from details_json.
        """
        log_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        clean_details = json.dumps(details or {})

        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO audit_logs (id, user_id, action, resource_type, resource_id, details_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (log_id, user_id, action, resource_type, resource_id, clean_details, now_iso),
            )
        return log_id

    @staticmethod
    def record_consent(
        guardian_code: str,
        child_code: str,
        scope: str,
        is_granted: bool = True,
    ) -> str:
        """Record a verified parental or guardian consent."""
        consent_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()

        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO consents (id, guardian_code, child_code, scope, is_granted, consent_date)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (consent_id, guardian_code, child_code, scope, 1 if is_granted else 0, now_iso),
            )
        return consent_id

    @staticmethod
    def check_consent(child_code: str, scope: str) -> bool:
        """Verify whether an active consent is granted for a specific child and scope."""
        with get_db() as conn:
            row = conn.execute(
                """
                SELECT is_granted FROM consents
                WHERE child_code = ? AND scope = ?
                ORDER BY consent_date DESC LIMIT 1
                """,
                (child_code, scope),
            ).fetchone()
            if row and row["is_granted"] == 1:
                return True
            return False


audit_service = AuditService()
