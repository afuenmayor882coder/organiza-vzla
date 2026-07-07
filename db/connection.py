"""
Single MongoDB connection shared across the entire Streamlit app.
Uses st.cache_resource so the connection is created once and reused.
"""

import streamlit as st
from pymongo import MongoClient
from pymongo.database import Database


@st.cache_resource
def get_client() -> MongoClient:
    return MongoClient(st.secrets["mongo"]["uri"])


def get_db() -> Database:
    return get_client()["organiza_vzla"]
