"""
Single MongoDB connection shared across the entire Streamlit app.
Uses st.cache_resource so the connection is created once and reused.

Environment modes (set via [app] mode in secrets.toml):
  production  →  database "organiza_vzla"      (real data, default)
  test        →  database "organiza_vzla_test" (safe sandbox)
"""

import streamlit as st
from pymongo import MongoClient
from pymongo.database import Database


@st.cache_resource
def get_client() -> MongoClient:
    return MongoClient(st.secrets["mongo"]["uri"])


def get_app_mode() -> str:
    """Return 'test' or 'production' based on secrets.toml [app] mode."""
    return st.secrets.get("app", {}).get("mode", "production")


def get_db_name() -> str:
    return "organiza_vzla_test" if get_app_mode() == "test" else "organiza_vzla"


def get_db() -> Database:
    return get_client()[get_db_name()]


def is_test_mode() -> bool:
    return get_app_mode() == "test"
