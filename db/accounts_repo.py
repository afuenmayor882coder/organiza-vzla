"""
Reads/writes for the `chart_of_accounts` collection.

Every organization gets a preset of NIIF accounts when created (seeded via
seed_default_accounts). Admins can add custom accounts or deactivate existing
ones, but the preset accounts remain tied to the org.
"""

import uuid
from datetime import datetime, timezone

from db.connection import get_db
from utils.constants import NIIF_CHART_OF_ACCOUNTS


def seed_default_accounts(org_id: str) -> int:
    """
    Insert the default NIIF chart of accounts for an organization.
    Skips accounts that already exist (idempotent).
    Returns the number of accounts created.
    """
    db = get_db()
    created = 0
    for acct in NIIF_CHART_OF_ACCOUNTS:
        exists = db["chart_of_accounts"].find_one({
            "org_id": org_id,
            "account_code": acct["code"],
        })
        if not exists:
            db["chart_of_accounts"].insert_one({
                "account_id":   str(uuid.uuid4()),
                "org_id":       org_id,
                "account_code": acct["code"],
                "account_name": acct["name"],
                "account_type": acct["account_type"],
                "direction":    acct["direction"],
                "is_preset":    True,
                "is_active":    True,
                "created_at":   datetime.now(timezone.utc),
            })
            created += 1
    return created


def list_accounts(org_id: str, active_only: bool = True) -> list[dict]:
    """Return all accounts for an org, sorted by account_code."""
    query: dict = {"org_id": org_id}
    if active_only:
        query["is_active"] = True
    return list(
        get_db()["chart_of_accounts"]
        .find(query, {"_id": 0})
        .sort("account_code", 1)
    )


def get_account_display_options(org_id: str) -> list[str]:
    """
    Return a list of formatted strings for use in Streamlit dropdowns.
    Format: "1.1.02 — Banco Principal"
    """
    accounts = list_accounts(org_id, active_only=True)
    return [f"{a['account_code']} — {a['account_name']}" for a in accounts]


def add_account(
    org_id: str,
    account_code: str,
    account_name: str,
    account_type: str,
    direction: str = "N/A",
) -> str:
    """Create a custom account for an org. Returns the new account_id."""
    account_id = str(uuid.uuid4())
    get_db()["chart_of_accounts"].insert_one({
        "account_id":   account_id,
        "org_id":       org_id,
        "account_code": account_code.strip(),
        "account_name": account_name.strip(),
        "account_type": account_type,
        "direction":    direction,
        "is_preset":    False,
        "is_active":    True,
        "created_at":   datetime.now(timezone.utc),
    })
    return account_id


def deactivate_account(account_id: str, org_id: str) -> None:
    """Deactivate an account so it no longer appears in dropdowns."""
    get_db()["chart_of_accounts"].update_one(
        {"account_id": account_id, "org_id": org_id},
        {"$set": {"is_active": False, "deactivated_at": datetime.now(timezone.utc)}},
    )


def account_code_exists(org_id: str, account_code: str) -> bool:
    return bool(
        get_db()["chart_of_accounts"].find_one({
            "org_id": org_id,
            "account_code": account_code.strip(),
        })
    )
