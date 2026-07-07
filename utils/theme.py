"""
utils/theme.py — Dynamic per-organization CSS theming.

Reads the org's stored colors from session state and injects a <style> block
that overrides Streamlit's CSS variables, so each org can have its own brand
colors without restarting the app.

How it works:
  - Streamlit sets CSS custom properties on :root (--primary-color, etc.)
  - We override them with a <style> tag injected via st.markdown
  - Because it runs on every page render, the theme always reflects the
    org's latest saved colors

Usage:
  In app.py, call apply_org_theme() right after the auth gate passes.
"""

import streamlit as st


def _lighten(hex_color: str, amount: float = 0.88) -> str:
    """
    Return a very light tint of hex_color by blending it toward white.
    amount = 0.88 means 88% white + 12% the original color (subtle background).
    """
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return "#F0F4FF"
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    r2 = int(r + (255 - r) * amount)
    g2 = int(g + (255 - g) * amount)
    b2 = int(b + (255 - b) * amount)
    return f"#{r2:02X}{g2:02X}{b2:02X}"


def apply_org_theme() -> None:
    """
    Inject CSS overrides based on the logged-in org's brand colors.
    Call this in app.py after the auth gate, so it runs on every page.

    Master users viewing "all orgs" (active_org_id = None) keep the
    default blue/white theme with no CSS override applied.
    """
    role = st.session_state.get("user_role", "")
    active_org = st.session_state.get("active_org_id")

    # Master with no specific org selected → stay with default blue, no override
    if role == "Master" and active_org is None:
        return

    settings = st.session_state.get("org_settings") or {}
    primary   = settings.get("primary_color", "#0066CC")
    secondary = settings.get("secondary_color", "") or _lighten(primary)

    # Validate hex format; fall back to default blue if malformed
    def _valid(c: str) -> bool:
        c = c.lstrip("#")
        return len(c) == 6 and all(ch in "0123456789ABCDEFabcdef" for ch in c)

    if not _valid(primary):
        primary = "#0066CC"
    if not _valid(secondary):
        secondary = _lighten(primary)

    css = f"""
<style>
/* ── Organiza Vzla dynamic org theme ─────────────────────────────────── */
:root {{
    --primary-color:             {primary} !important;
    --secondary-background-color:{secondary} !important;
}}

/* Primary buttons */
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {{
    background-color: {primary} !important;
    border-color:     {primary} !important;
    color: #ffffff !important;
}}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover {{
    filter: brightness(1.12);
}}

/* Links and accents */
a, .stMarkdown a {{
    color: {primary} !important;
}}

/* Sidebar active link / selected page highlight */
[data-testid="stSidebarNav"] li [aria-current="page"] {{
    background-color: {secondary} !important;
    border-left: 3px solid {primary} !important;
}}

/* Tab underline */
[data-baseweb="tab"][aria-selected="true"] {{
    border-bottom-color: {primary} !important;
    color: {primary} !important;
}}

/* st.metric delta color accent */
[data-testid="stMetricDelta"] svg {{
    fill: {primary} !important;
}}
</style>
"""
    st.markdown(css, unsafe_allow_html=True)


def get_role_badge_color(role: str, settings: dict | None = None) -> str:
    """
    Return the badge background color for a given role.
    Uses the org's primary_color for Admin instead of hardcoded blue.
    """
    if role == "Admin":
        primary = (settings or {}).get("primary_color", "#0066CC")
        return primary if primary else "#0066CC"
    return "#555555"
