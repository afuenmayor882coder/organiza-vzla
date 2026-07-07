"""
Reads/writes for the `stakeholders` collection.
Every query filters by org_id for multi-tenant isolation.
"""

import uuid
from datetime import datetime, timezone

from db.connection import get_db
from db.audit_repo import log_action


def add_stakeholder(
    org_id: str,
    name: str,
    contact: str = "",
    stakeholder_type: str = "Donante",
    user: str = "system",
) -> str:
    partner_id = str(uuid.uuid4())
    get_db()["stakeholders"].insert_one(
        {
            "org_id": org_id,
            "partner_id": partner_id,
            "name": name,
            "contact": contact,
            "type": stakeholder_type,
            "created_at": datetime.now(timezone.utc),
        }
    )
    log_action(org_id, "create", "stakeholders", partner_id, user=user)
    return partner_id


def list_stakeholders(org_id: str, stakeholder_type: str | None = None) -> list[dict]:
    query: dict = {"org_id": org_id}
    if stakeholder_type:
        query["type"] = stakeholder_type
    return list(get_db()["stakeholders"].find(query, {"_id": 0}))


def update_stakeholder(org_id: str, partner_id: str, updates: dict, user: str = "system") -> None:
    get_db()["stakeholders"].update_one(
        {"org_id": org_id, "partner_id": partner_id},
        {"$set": updates},
    )
    log_action(org_id, "update", "stakeholders", partner_id, user=user, changes=updates)
