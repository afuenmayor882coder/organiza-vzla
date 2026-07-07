"""
Reads/writes for the `organizations` and `users` collections.
"""

import uuid
from datetime import datetime, timezone

import bcrypt

from db.connection import get_db
from db.audit_repo import log_action


# ---------------------------------------------------------------------------
# Organizations
# ---------------------------------------------------------------------------

_DEFAULT_SETTINGS = {
    "display_name": "",
    "logo_url": "",
    "primary_color": "#0066CC",
    "secondary_color": "#E8F0FE",
    "welcome_message": "",
    "currency_default": "USD",
    "low_stock_threshold": 10,
    "expiration_warning_days": 30,
}


def create_organization(name: str) -> str:
    org_id = str(uuid.uuid4())
    get_db()["organizations"].insert_one(
        {
            "org_id": org_id,
            "name": name,
            "created_at": datetime.now(timezone.utc),
            "settings": _DEFAULT_SETTINGS.copy(),
        }
    )
    return org_id


def get_organization(org_id: str) -> dict | None:
    return get_db()["organizations"].find_one({"org_id": org_id}, {"_id": 0})


def get_org_settings(org_id: str) -> dict:
    """Return the org's settings dict, filling in defaults for missing keys."""
    org = get_db()["organizations"].find_one({"org_id": org_id}, {"_id": 0, "settings": 1})
    stored = (org or {}).get("settings", {})
    # Merge stored values over defaults so missing keys get a fallback
    result = _DEFAULT_SETTINGS.copy()
    result.update(stored)
    return result


def update_org_settings(org_id: str, settings: dict) -> None:
    """Persist updated settings fields to the organization document."""
    get_db()["organizations"].update_one(
        {"org_id": org_id},
        {"$set": {"settings": settings, "settings_updated_at": datetime.now(timezone.utc)}},
    )


def list_organizations() -> list[dict]:
    return list(get_db()["organizations"].find({}, {"_id": 0}))


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_user(
    email: str,
    password: str,
    name: str,
    org_id: str,
    role: str = "Usuario",
    created_by: str = "system",
) -> str:
    user_id = str(uuid.uuid4())
    get_db()["users"].insert_one(
        {
            "user_id": user_id,
            "email": email.lower().strip(),
            "password_hash": _hash_password(password),
            "name": name,
            "org_id": org_id,
            "role": role,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
        }
    )
    log_action(org_id, "create", "users", user_id, user=created_by)
    return user_id


def get_user_by_email(email: str) -> dict | None:
    return get_db()["users"].find_one(
        {"email": email.lower().strip(), "is_active": True}, {"_id": 0}
    )


def list_users_by_org(org_id: str) -> list[dict]:
    return list(
        get_db()["users"].find(
            {"org_id": org_id}, {"_id": 0, "password_hash": 0}
        )
    )


def deactivate_user(user_id: str, org_id: str, deactivated_by: str = "system") -> None:
    get_db()["users"].update_one(
        {"user_id": user_id, "org_id": org_id},
        {"$set": {"is_active": False}},
    )
    log_action(org_id, "update", "users", user_id, user=deactivated_by,
               changes={"is_active": {"old": True, "new": False}})


def update_user_password(user_id: str, new_password: str) -> None:
    get_db()["users"].update_one(
        {"user_id": user_id},
        {"$set": {"password_hash": _hash_password(new_password)}},
    )
