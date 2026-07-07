"""
Reads/writes for `item_catalog` and `inventory_master` collections.
Every query filters by org_id for multi-tenant isolation.
"""

import uuid
from datetime import datetime, timezone

from db.connection import get_db
from db.audit_repo import log_action


# ---------------------------------------------------------------------------
# Item Catalog
# ---------------------------------------------------------------------------

def add_catalog_item(
    org_id: str,
    name: str,
    category: str,
    subcategory: str,
    default_packaging: str,
    tracks_expiration: bool,
    user: str = "system",
) -> str:
    item_id = str(uuid.uuid4())
    get_db()["item_catalog"].insert_one(
        {
            "org_id": org_id,
            "item_id": item_id,
            "name": name,
            "category": category,
            "subcategory": subcategory,
            "default_packaging": default_packaging,
            "tracks_expiration": tracks_expiration,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
        }
    )
    log_action(org_id, "create", "item_catalog", item_id, user=user)
    return item_id


def list_catalog_items(org_id: str, active_only: bool = True) -> list[dict]:
    query: dict = {"org_id": org_id}
    if active_only:
        query["is_active"] = True
    return list(get_db()["item_catalog"].find(query, {"_id": 0}))


def get_catalog_item(org_id: str, item_id: str) -> dict | None:
    return get_db()["item_catalog"].find_one(
        {"org_id": org_id, "item_id": item_id}, {"_id": 0}
    )


def update_catalog_item(org_id: str, item_id: str, updates: dict, user: str = "system") -> None:
    get_db()["item_catalog"].update_one(
        {"org_id": org_id, "item_id": item_id},
        {"$set": updates},
    )
    log_action(org_id, "update", "item_catalog", item_id, user=user, changes=updates)


def deactivate_catalog_item(org_id: str, item_id: str, user: str = "system") -> None:
    update_catalog_item(org_id, item_id, {"is_active": False}, user=user)


# ---------------------------------------------------------------------------
# Inventory Master (current stock levels)
# ---------------------------------------------------------------------------

def upsert_stock(
    org_id: str,
    item_id: str,
    name: str,
    category: str,
    subcategory: str,
    packaging: str,
    quantity_delta: int,
    expiration_date: datetime | None = None,
    user: str = "system",
) -> None:
    """Add to stock if exists, create if not. quantity_delta can be negative for exits."""
    col = get_db()["inventory_master"]
    existing = col.find_one({"org_id": org_id, "item_id": item_id})

    if existing:
        col.update_one(
            {"org_id": org_id, "item_id": item_id},
            {"$inc": {"current_stock": quantity_delta}},
        )
        log_action(org_id, "update", "inventory_master", item_id, user=user,
                   changes={"current_stock_delta": quantity_delta})
    else:
        col.insert_one(
            {
                "org_id": org_id,
                "item_id": item_id,
                "name": name,
                "category": category,
                "subcategory": subcategory,
                "packaging": packaging,
                "current_stock": quantity_delta,
                "expiration_date": expiration_date,
                "created_at": datetime.now(timezone.utc),
            }
        )
        log_action(org_id, "create", "inventory_master", item_id, user=user)


def get_stock(org_id: str) -> list[dict]:
    return list(
        get_db()["inventory_master"]
        .find({"org_id": org_id}, {"_id": 0})
        .sort("current_stock", 1)
    )


def get_stock_for_item(org_id: str, item_id: str) -> int:
    doc = get_db()["inventory_master"].find_one(
        {"org_id": org_id, "item_id": item_id}, {"current_stock": 1}
    )
    return doc["current_stock"] if doc else 0


def get_expiring_items(org_id: str, within_days: int = 30) -> list[dict]:
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) + timedelta(days=within_days)
    return list(
        get_db()["inventory_master"].find(
            {
                "org_id": org_id,
                "expiration_date": {"$ne": None, "$lte": cutoff},
                "current_stock": {"$gt": 0},
            },
            {"_id": 0},
        )
    )


def get_low_stock_items(org_id: str, threshold: int = 10) -> list[dict]:
    return list(
        get_db()["inventory_master"].find(
            {"org_id": org_id, "current_stock": {"$lte": threshold, "$gt": 0}},
            {"_id": 0},
        )
    )


def get_zero_stock_items(org_id: str) -> list[dict]:
    return list(
        get_db()["inventory_master"].find(
            {"org_id": org_id, "current_stock": {"$lte": 0}},
            {"_id": 0},
        )
    )
