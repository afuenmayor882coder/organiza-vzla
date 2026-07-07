"""
app.py — Entry point and authentication gatekeeper for Organiza Vzla.

Authentication flow:
  - Not logged in → login form is shown; the sidebar and all other pages
    are hidden so anonymous users cannot bypass the gate.
  - Logged in     → role-based navigation is built.  Admin users see the
    Usuarios page; regular users do not.
"""

import streamlit as st
from utils.auth import (
    login,
    logout,
    require_auth,
    is_admin,
    current_user_name,
    current_org_name,
    current_org_settings,
)
from db.connection import is_test_mode
from utils.theme import apply_org_theme, get_role_badge_color

st.set_page_config(
    page_title="Organiza Vzla",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Hide the entire sidebar (and any auto-generated nav links) while the login
# form is displayed, so anonymous users see nothing but the login card.
_HIDE_SIDEBAR_CSS = """
<style>
section[data-testid="stSidebar"]   { display: none; }
[data-testid="stSidebarNav"]        { display: none; }
</style>
"""


# ── Login page ────────────────────────────────────────────────────────────────

def _show_login_page() -> None:
    """Render the centered login card and block the rest of the app."""
    st.markdown(_HIDE_SIDEBAR_CSS, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown(
            """
            <div style="text-align:center; padding: 2.5rem 0 1.5rem 0;">
                <span style="font-size:4.5rem;">📦</span>
                <h1 style="color:#0066CC; margin: 0.25rem 0 0 0;">Organiza Vzla</h1>
                <p style="color:#666; margin-top:0.3rem; font-size:1.05rem;">
                    Gestión de inventario para organizaciones
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("login_form", clear_on_submit=False):
            email = st.text_input(
                "Correo electrónico",
                placeholder="usuario@ejemplo.com",
                help="El correo con el que fuiste registrado en la plataforma.",
            )
            password = st.text_input(
                "Contraseña",
                type="password",
                placeholder="••••••••",
            )
            submitted = st.form_submit_button(
                "Iniciar Sesión",
                use_container_width=True,
                type="primary",
            )

        if submitted:
            if not email.strip() or not password:
                st.error("Por favor ingresa tu correo y contraseña.")
            elif login(email.strip(), password):
                st.rerun()
            else:
                st.error(
                    "Correo o contraseña incorrectos. "
                    "Verifica tus datos e intenta de nuevo."
                )

    st.stop()


# ── Auth gate ─────────────────────────────────────────────────────────────────

if not require_auth():
    _show_login_page()

# ── Test mode banner (shown on every page when using the test database) ────────

if is_test_mode():
    st.warning(
        "⚠️ **MODO DE PRUEBA** — Estás usando la base de datos de prueba "
        "(`organiza_vzla_test`). Los datos aquí **no afectan** la base de datos "
        "de producción. Para volver al modo real, cambia `mode = \"production\"` "
        "en `.streamlit/secrets.toml`.",
        icon="🧪",
    )

# Apply organization brand colors on every page render
apply_org_theme()


# ── Sidebar (rendered on every page once authenticated) ───────────────────────

with st.sidebar:
    st.markdown("### 📦 Organiza Vzla")
    st.divider()

    user_name = current_user_name() or "Usuario"
    org = current_org_name() or ""
    role = st.session_state.get("user_role", "")

    st.markdown(f"👤 **{user_name}**")
    if org:
        st.caption(f"🏢 {org}")
    if role:
        badge_color = get_role_badge_color(role, current_org_settings())
        st.markdown(
            f'<span style="background:{badge_color};color:#fff;padding:2px 10px;'
            f'border-radius:12px;font-size:0.78rem;font-weight:600;">{role}</span>',
            unsafe_allow_html=True,
        )

    st.divider()

    if st.button("Cerrar Sesión", use_container_width=True):
        logout()
        st.rerun()


# ── Role-based navigation ─────────────────────────────────────────────────────

_pages = [
    st.Page("pages/1_Resumen.py",             title="Resumen",          icon="🏠"),
    st.Page("pages/2_Registro_Donaciones.py", title="Donaciones",       icon="📥"),
    st.Page("pages/3_Salida_Inventario.py",   title="Salidas",          icon="📤"),
    st.Page("pages/4_Flujo_de_Caja.py",       title="Flujo de Caja",    icon="💰"),
    st.Page("pages/5_Panel_de_Control.py",    title="Panel de Control", icon="📊"),
    st.Page("pages/6_Catalogo_Articulos.py",  title="Catálogo",         icon="📋"),
]

if is_admin():
    _pages.append(
        st.Page("pages/7_Usuarios.py", title="Usuarios", icon="👥")
    )

pg = st.navigation(_pages)
pg.run()
