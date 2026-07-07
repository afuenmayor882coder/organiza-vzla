"""
Reads/writes for the `inventory_exits` collection (inventory OUT).
Every query filters by org_id for multi-tenant isolation.
"""

import uuid
from datetime import datetime, timezone

from db.connection import get_db
from db.audit_repo import log_action


def add_exit(
    org_id: str,
    item_id: str,
    category: str,
    subcategory: str,
    packaging: str,
    quantity: int,
    recipient_name: str,
    recipient_org: str = "",
    reason: str = "",
    notes: str = "",
    user: str = "system",
) -> str:
    exit_id = str(uuid.uuid4())
    get_db()["inventory_exits"].insert_one(
        {
            "org_id": org_id,
            "exit_id": exit_id,
            "date": datetime.now(timezone.utc),
            "item_id": item_id,
            "category": category,
            "subcategory": subcategory,
            "packaging": packaging,
            "quantity": quantity,
            "recipient_name": recipient_name,
            "recipient_org": recipient_org,
            "reason": reason,
            "notes": notes,
        }
    )
    log_action(org_id, "create", "inventory_exits", exit_id, user=user)
    return exit_id


def list_exits(
    org_id: str | None,
    limit: int = 50,
    category: str | None = None,
    recipient: str | None = None,
) -> list[dict]:
    query: dict = {}
    if org_id:
        query["org_id"] = org_id
    if category:
        query["category"] = category
    if recipient:
        query["recipient_name"] = {"$regex": recipient, "$options": "i"}
    return list(
        get_db()["inventory_exits"]
        .find(query, {"_id": 0})
        .sort("date", -1)
        .limit(limit)
    )


def get_exits_in_range(org_id: str, start: datetime, end: datetime) -> list[dict]:
    return list(
        get_db()["inventory_exits"]
        .find({"org_id": org_id, "date": {"$gte": start, "$lte": end}}, {"_id": 0})
        .sort("date", -1)
    )
