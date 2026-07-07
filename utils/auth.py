"""
Authentication wrapper that manages login state via st.session_state.
Uses bcrypt password verification from db.auth_repo.
"""

import streamlit as st
from db.auth_repo import get_user_by_email, verify_password


def _init_session() -> None:
    defaults = {
        "authenticated": False,
        "user_email": None,
        "user_name": None,
        "user_role": None,
        "org_id": None,
        "user_id": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def login(email: str, password: str) -> bool:
    """Attempt to log in. Returns True on success."""
    _init_session()
    user = get_user_by_email(email)
    if user and verify_password(password, user["password_hash"]):
        st.session_state["authenticated"] = True
        st.session_state["user_email"] = user["email"]
        st.session_state["user_name"] = user["name"]
        st.session_state["user_role"] = user["role"]
        st.session_state["org_id"] = user["org_id"]
        st.session_state["user_id"] = user["user_id"]
        return True
    return False


def logout() -> None:
    for key in ["authenticated", "user_email", "user_name", "user_role", "org_id", "user_id"]:
        st.session_state[key] = None
    st.session_state["authenticated"] = False


def require_auth() -> bool:
    """Returns True if the user is authenticated. Pages should call this at the top."""
    _init_session()
    return st.session_state.get("authenticated", False)


def is_admin() -> bool:
    return st.session_state.get("user_role") == "Admin"


def current_org_id() -> str | None:
    return st.session_state.get("org_id")


def current_user_email() -> str | None:
    return st.session_state.get("user_email")


def current_user_name() -> str | None:
    return st.session_state.get("user_name")
