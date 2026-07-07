"""
Reads/writes for the `donation_entries` collection (inventory IN).
Every query filters by org_id for multi-tenant isolation.
"""

import uuid
from datetime import datetime, timezone

from db.connection import get_db
from db.audit_repo import log_action


def add_donation(
    org_id: str,
    item_id: str,
    category: str,
    subcategory: str,
    packaging: str,
    quantity: int,
    donor_name: str,
    donor_org: str = "",
    expiration_date: datetime | None = None,
    notes: str = "",
    user: str = "system",
) -> str:
    entry_id = str(uuid.uuid4())
    get_db()["donation_entries"].insert_one(
        {
            "org_id": org_id,
            "entry_id": entry_id,
            "date": datetime.now(timezone.utc),
            "item_id": item_id,
            "category": category,
            "subcategory": subcategory,
            "packaging": packaging,
            "quantity": quantity,
            "expiration_date": expiration_date,
            "donor_name": donor_name,
            "donor_org": donor_org,
            "notes": notes,
        }
    )
    log_action(org_id, "create", "donation_entries", entry_id, user=user)
    return entry_id


def list_donations(
    org_id: str,
    limit: int = 50,
    category: str | None = None,
    donor: str | None = None,
) -> list[dict]:
    query: dict = {"org_id": org_id}
    if category:
        query["category"] = category
    if donor:
        query["donor_name"] = {"$regex": donor, "$options": "i"}
    return list(
        get_db()["donation_entries"]
        .find(query, {"_id": 0})
        .sort("date", -1)
        .limit(limit)
    )


def count_donations_this_month(org_id: str) -> int:
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return get_db()["donation_entries"].count_documents(
        {"org_id": org_id, "date": {"$gte": start_of_month}}
    )


def get_donations_in_range(org_id: str, start: datetime, end: datetime) -> list[dict]:
    return list(
        get_db()["donation_entries"]
        .find({"org_id": org_id, "date": {"$gte": start, "$lte": end}}, {"_id": 0})
        .sort("date", -1)
    )
