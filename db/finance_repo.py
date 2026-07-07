"""
Reads/writes for the `financial_ledger` collection.
Every query filters by org_id for multi-tenant isolation.
"""

import uuid
from datetime import datetime, timezone

from db.connection import get_db
from db.audit_repo import log_action


def add_transaction(
    org_id: str,
    date: datetime,
    amount: float,
    currency: str,
    direction: str,
    niif_category: str,
    subcategory: str,
    description: str = "",
    source_bank: str = "",
    account_code: str = "",
    user: str = "system",
) -> str:
    transaction_id = str(uuid.uuid4())
    get_db()["financial_ledger"].insert_one(
        {
            "org_id": org_id,
            "transaction_id": transaction_id,
            "date": date,
            "amount": amount,
            "currency": currency,
            "direction": direction,
            "niif_category": niif_category,
            "subcategory": subcategory,
            "description": description,
            "source_bank": source_bank,
            "account_code": account_code,
            "created_at": datetime.now(timezone.utc),
        }
    )
    log_action(org_id, "create", "financial_ledger", transaction_id, user=user)
    return transaction_id


def add_transactions_batch(org_id: str, rows: list[dict], user: str = "system") -> int:
    """Insert multiple transactions at once (from bank statement import)."""
    docs = []
    for row in rows:
        tid = str(uuid.uuid4())
        row["org_id"] = org_id
        row["transaction_id"] = tid
        row["created_at"] = datetime.now(timezone.utc)
        docs.append(row)

    if docs:
        get_db()["financial_ledger"].insert_many(docs)
        for doc in docs:
            log_action(org_id, "create", "financial_ledger",
                       doc["transaction_id"], user=user)
    return len(docs)


def list_transactions(
    org_id: str | None,
    limit: int = 100,
    direction: str | None = None,
    niif_category: str | None = None,
) -> list[dict]:
    query: dict = {}
    if org_id:
        query["org_id"] = org_id
    if direction:
        query["direction"] = direction
    if niif_category:
        query["niif_category"] = niif_category
    return list(
        get_db()["financial_ledger"]
        .find(query, {"_id": 0})
        .sort("date", -1)
        .limit(limit)
    )


def get_transactions_in_range(
    org_id: str | None, start: datetime, end: datetime
) -> list[dict]:
    query: dict = {"date": {"$gte": start, "$lte": end}}
    if org_id:
        query["org_id"] = org_id
    return list(get_db()["financial_ledger"].find(query, {"_id": 0}).sort("date", -1))


def get_cash_balance(org_id: str | None) -> float:
    match_stage: dict = {}
    if org_id:
        match_stage["org_id"] = org_id
    pipeline = [
        {"$match": match_stage},
        {
            "$group": {
                "_id": "$direction",
                "total": {"$sum": "$amount"},
            }
        },
    ]
    results = {r["_id"]: r["total"] for r in get_db()["financial_ledger"].aggregate(pipeline)}
    return results.get("Ingreso", 0.0) - results.get("Egreso", 0.0)


def get_niif_summary(org_id: str | None, start: datetime | None = None, end: datetime | None = None) -> dict:
    """Returns net totals per NIIF category: {category: net_amount}."""
    match_stage: dict = {}
    if org_id:
        match_stage["org_id"] = org_id
    if start and end:
        match_stage["date"] = {"$gte": start, "$lte": end}

    pipeline = [
        {"$match": match_stage},
        {
            "$group": {
                "_id": {"category": "$niif_category", "direction": "$direction"},
                "total": {"$sum": "$amount"},
            }
        },
    ]
    raw = list(get_db()["financial_ledger"].aggregate(pipeline))

    summary: dict[str, float] = {}
    for r in raw:
        cat = r["_id"]["category"]
        amount = r["total"]
        sign = 1 if r["_id"]["direction"] == "Ingreso" else -1
        summary[cat] = summary.get(cat, 0.0) + (amount * sign)
    return summary
