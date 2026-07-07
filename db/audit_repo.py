"""
Writes an immutable audit trail entry every time data is created, updated,
or deleted. Called automatically by the other repo modules.
"""

from datetime import datetime, timezone
from db.connection import get_db


def log_action(
    org_id: str,
    action: str,
    collection: str,
    record_id: str,
    user: str = "system",
    changes: dict | None = None,
) -> None:
    get_db()["audit_log"].insert_one(
        {
            "org_id": org_id,
            "timestamp": datetime.now(timezone.utc),
            "action": action,
            "collection": collection,
            "record_id": record_id,
            "user": user,
            "changes": changes or {},
        }
    )
