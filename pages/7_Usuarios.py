"""
pages/7_Usuarios.py — User & Organization management (Admin only).

Only Admins can access this page. Regular users see an access-denied message.

Features:
  • View all users in the organization.
  • Add a new user (admin sets a temporary password).
  • Deactivate a user who has left.
"""

import streamlit as st

from db.auth_repo import create_user, deactivate_user, list_users_by_org
from utils.auth import current_org_id, current_user_email, is_admin
from utils.constants import USER_ROLES
from utils.formatters import format_date
from utils.validators import validate_email, validate_required_text

# ── Admin guard ───────────────────────────────────────────────────────────────
if not is_admin():
    st.error("🔒 Acceso denegado. Esta página es solo para Administradores.")
    st.stop()

org_id = current_org_id()
admin_email = current_user_email() or "system"

st.header("👥 Gestión de Usuarios")
st.caption("Administra los miembros de tu organización.")

# ── Current users table ───────────────────────────────────────────────────────
st.subheader("Usuarios de la Organización")

users = list_users_by_org(org_id)
active_users = [u for u in users if u.get("is_active", True)]
inactive_users = [u for u in users if not u.get("is_active", True)]

if active_users:
    st.dataframe(
        [
            {
                "Nombre": u.get("name", "—"),
                "Correo": u.get("email", "—"),
                "Rol": u.get("role", "—"),
                "Registrado": format_date(u.get("created_at")),
            }
            for u in active_users
        ],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No hay usuarios activos. Agrega el primero usando el formulario de abajo.")

if inactive_users:
    with st.expander(f"Ver usuarios desactivados ({len(inactive_users)})"):
        st.dataframe(
            [
                {
                    "Nombre": u.get("name", "—"),
                    "Correo": u.get("email", "—"),
                    "Rol": u.get("role", "—"),
                }
                for u in inactive_users
            ],
            use_container_width=True,
            hide_index=True,
        )

# ── Add new user ──────────────────────────────────────────────────────────────
st.divider()
with st.expander("➕ Agregar nuevo usuario", expanded=False):
    st.subheader("Nuevo Usuario")
    st.caption(
        "El nuevo usuario recibirá una contraseña temporal. "
        "Pídele que la cambie en su primer inicio de sesión."
    )

    new_name = st.text_input("Nombre completo *", placeholder="Ej: María García")
    new_email = st.text_input(
        "Correo electrónico *",
        placeholder="usuario@ejemplo.com",
    )
    new_role = st.selectbox("Rol *", USER_ROLES)
    new_pass = st.text_input(
        "Contraseña temporal *",
        type="password",
        help="Mínimo 8 caracteres. El usuario debe cambiarla después.",
    )
    confirm_pass = st.text_input("Confirmar contraseña *", type="password")

    if st.button("✅ Crear Usuario", type="primary", use_container_width=True):
        errors = []
        err = validate_required_text(new_name, "Nombre completo")
        if err:
            errors.append(err)
        err = validate_email(new_email)
        if err:
            errors.append(err)
        if not new_pass or len(new_pass) < 8:
            errors.append("La contraseña debe tener al menos 8 caracteres.")
        if new_pass != confirm_pass:
            errors.append("Las contraseñas no coinciden.")

        existing = next(
            (u for u in users if u.get("email", "").lower() == new_email.lower().strip()),
            None,
        )
        if existing:
            errors.append(
                f"Ya existe un usuario con el correo «{new_email.strip()}»."
            )

        if errors:
            for err in errors:
                st.error(err)
        else:
            with st.spinner("Creando usuario…"):
                create_user(
                    email=new_email.strip(),
                    password=new_pass,
                    name=new_name.strip(),
                    org_id=org_id,
                    role=new_role,
                    created_by=admin_email,
                )
            st.success(
                f"✅ Usuario **{new_name.strip()}** creado con el rol **{new_role}**. "
                "Comparte la contraseña temporal de forma segura."
            )
            st.rerun()

# ── Deactivate user ───────────────────────────────────────────────────────────
deactivatable = [u for u in active_users if u.get("email") != admin_email]
if deactivatable:
    st.divider()
    with st.expander("🚫 Desactivar usuario"):
        st.caption(
            "Desactivar un usuario le impide iniciar sesión. "
            "Sus registros históricos NO se eliminan."
        )
        deact_map = {
            f"{u['name']} ({u['email']})": u for u in deactivatable
        }
        to_deact = st.selectbox("Selecciona el usuario a desactivar", list(deact_map.keys()))

        if st.button("🚫 Desactivar Usuario", type="secondary"):
            doc = deact_map[to_deact]
            with st.spinner("Desactivando…"):
                deactivate_user(doc["user_id"], org_id, deactivated_by=admin_email)
            st.success(f"«{doc['name']}» ha sido desactivado.")
            st.rerun()
