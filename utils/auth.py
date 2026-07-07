"""
Authentication wrapper that manages login state via st.session_state.
Uses bcrypt password verification from db.auth_repo.
"""

import streamlit as st
from db.auth_repo import get_user_by_email, verify_password, get_organization, get_org_settings


def _init_session() -> None:
    defaults = {
        "authenticated": False,
        "user_email": None,
        "user_name": None,
        "user_role": None,
        "org_id": None,
        "org_name": None,
        "user_id": None,
        "org_settings": {},
        # active_org_id: the org whose data is currently shown.
        # For regular users: always equals org_id.
        # For Master: None = all orgs, or a specific org_id.
        "active_org_id": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def login(email: str, password: str) -> bool:
    """Attempt to log in. Returns True on success."""
    _init_session()
    user = get_user_by_email(email)
    if user and verify_password(password, user["password_hash"]):
        org = get_organization(user["org_id"])
        settings = get_org_settings(user["org_id"])
        is_master_role = user["role"] == "Master"
        st.session_state["authenticated"] = True
        st.session_state["user_email"] = user["email"]
        st.session_state["user_name"] = user["name"]
        st.session_state["user_role"] = user["role"]
        st.session_state["org_id"] = user["org_id"]
        st.session_state["org_name"] = org["name"] if org else user["org_id"]
        st.session_state["user_id"] = user["user_id"]
        st.session_state["org_settings"] = settings
        # Master starts with all-orgs view; regular users are locked to their org
        st.session_state["active_org_id"] = None if is_master_role else user["org_id"]
        return True
    return False


def logout() -> None:
    for key in [
        "authenticated", "user_email", "user_name", "user_role",
        "org_id", "org_name", "user_id", "org_settings", "active_org_id",
    ]:
        st.session_state[key] = None
    st.session_state["authenticated"] = False


def require_auth() -> bool:
    """Returns True if the user is authenticated. Pages should call this at the top."""
    _init_session()
    return st.session_state.get("authenticated", False)


def is_admin() -> bool:
    return st.session_state.get("user_role") in ("Admin", "Master")


def is_master() -> bool:
    return st.session_state.get("user_role") == "Master"


def current_org_id() -> str | None:
    """The user's own org_id (never changes after login)."""
    return st.session_state.get("org_id")


def current_active_org_id() -> str | None:
    """
    The org currently being viewed/operated on.
    For regular users: always their own org_id.
    For Master: None (all orgs) or a specific org_id chosen via the org switcher.
    Pass this to all DB queries.
    """
    return st.session_state.get("active_org_id")


def set_active_org_id(org_id: str | None, org_settings: dict | None = None) -> None:
    """Switch the active org (Master only). Pass org_settings to update theming."""
    st.session_state["active_org_id"] = org_id
    if org_settings is not None:
        st.session_state["org_settings"] = org_settings
    elif org_id is None:
        # All-orgs view: reset to default blue theme
        st.session_state["org_settings"] = {}


def current_org_name() -> str | None:
    return st.session_state.get("org_name")


def current_user_email() -> str | None:
    return st.session_state.get("user_email")


def current_user_name() -> str | None:
    return st.session_state.get("user_name")


def current_org_settings() -> dict:
    """Return the current org's settings dict (loaded at login)."""
    return st.session_state.get("org_settings") or {}


def reload_org_settings() -> None:
    """Re-fetch org settings from DB and refresh session state (call after saving settings)."""
    org_id = current_org_id()
    if org_id:
        from db.auth_repo import get_org_settings as _get
        st.session_state["org_settings"] = _get(org_id)
