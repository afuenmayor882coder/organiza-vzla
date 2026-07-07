"""
pages/7_Usuarios.py — User & Organization management (Admin only).

Only Admins can access this page. Regular users see an access-denied message.

Features:
  • View all users in the organization.
  • Add a new user (admin sets a temporary password).
  • Deactivate a user who has left.
"""

import streamlit as st

from db.auth_repo import create_user, deactivate_user, list_users_by_org, get_org_settings, update_org_settings
from db.accounts_repo import (
    list_accounts,
    add_account,
    deactivate_account,
    account_code_exists,
    seed_default_accounts,
)
from utils.auth import current_org_id, current_user_email, is_admin, reload_org_settings
from utils.constants import USER_ROLES, CURRENCIES
from utils.formatters import format_date
from utils.validators import validate_email, validate_required_text

# ── Admin guard ───────────────────────────────────────────────────────────────
if not is_admin():
    st.error("🔒 Acceso denegado. Esta página es solo para Administradores.")
    st.stop()

org_id = current_org_id()
admin_email = current_user_email() or "system"

st.header("👥 Gestión de Usuarios y Configuración")
st.caption("Administra los miembros y las cuentas contables de tu organización.")

tab_users, tab_accounts, tab_settings = st.tabs(["👥 Usuarios", "📒 Cuentas Contables", "⚙️ Configuración"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — USERS
# ══════════════════════════════════════════════════════════════════════════════
with tab_users:
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

    # ── Add new user ──────────────────────────────────────────────────────────
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

    # ── Deactivate user ───────────────────────────────────────────────────────
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


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CHART OF ACCOUNTS
# ══════════════════════════════════════════════════════════════════════════════
with tab_accounts:
    st.subheader("Plan de Cuentas NIIF")
    st.caption(
        "Estas son las cuentas contables de tu organización. "
        "Se usan en el registro de Flujo de Caja para clasificar cada transacción. "
        "Las cuentas marcadas como 'Predefinida' son el estándar NIIF y no se eliminan."
    )

    accounts = list_accounts(org_id, active_only=False)

    if not accounts:
        st.warning(
            "Esta organización no tiene cuentas contables. "
            "Haz clic en el botón de abajo para inicializar el plan de cuentas NIIF estándar."
        )
        if st.button("🔧 Inicializar Plan de Cuentas NIIF", type="primary"):
            with st.spinner("Creando cuentas…"):
                n = seed_default_accounts(org_id)
            st.success(f"✅ {n} cuentas NIIF creadas exitosamente.")
            st.rerun()
    else:
        active_accounts   = [a for a in accounts if a.get("is_active", True)]
        inactive_accounts = [a for a in accounts if not a.get("is_active", True)]

        TYPE_LABELS = {
            "Activo": "🏦 Activos",
            "Pasivo": "💳 Pasivos",
            "Fondo": "💼 Fondos",
            "Ingreso": "📈 Ingresos",
            "Egreso": "📉 Egresos",
        }

        # Group by type for a cleaner display
        for acct_type, label in TYPE_LABELS.items():
            group = [a for a in active_accounts if a.get("account_type") == acct_type]
            if group:
                with st.expander(f"{label} ({len(group)})", expanded=True):
                    st.dataframe(
                        [
                            {
                                "Código": a.get("account_code", "—"),
                                "Nombre": a.get("account_name", "—"),
                                "Predefinida": "✅" if a.get("is_preset") else "—",
                            }
                            for a in group
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )

        if inactive_accounts:
            with st.expander(f"Cuentas desactivadas ({len(inactive_accounts)})", expanded=False):
                st.dataframe(
                    [
                        {
                            "Código": a.get("account_code", "—"),
                            "Nombre": a.get("account_name", "—"),
                            "Tipo": a.get("account_type", "—"),
                        }
                        for a in inactive_accounts
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

        # ── Add custom account ─────────────────────────────────────────────
        st.divider()
        with st.expander("➕ Agregar cuenta personalizada", expanded=False):
            st.caption(
                "Puedes agregar cuentas específicas de tu organización "
                "además de las predefinidas."
            )
            col_code, col_name = st.columns(2)
            with col_code:
                new_code = st.text_input(
                    "Código *",
                    placeholder="Ej: 5.2.01",
                    help="Usa el formato X.X.XX siguiendo la convención NIIF.",
                )
            with col_name:
                new_acct_name = st.text_input(
                    "Nombre de la cuenta *",
                    placeholder="Ej: Gastos de Capacitación",
                )
            col_type, col_dir = st.columns(2)
            with col_type:
                new_type = st.selectbox(
                    "Tipo *",
                    ["Activo", "Pasivo", "Fondo", "Ingreso", "Egreso"],
                )
            with col_dir:
                new_dir = st.selectbox(
                    "Dirección",
                    ["N/A", "Ingreso", "Egreso"],
                    help="Ingreso si esta cuenta recibe dinero, Egreso si lo gasta.",
                )

            if st.button("✅ Agregar Cuenta", type="primary", use_container_width=True):
                acct_errors = []
                if not new_code.strip():
                    acct_errors.append("El código de cuenta es requerido.")
                if not new_acct_name.strip():
                    acct_errors.append("El nombre de cuenta es requerido.")
                if new_code.strip() and account_code_exists(org_id, new_code.strip()):
                    acct_errors.append(f"Ya existe una cuenta con el código «{new_code.strip()}».")

                if acct_errors:
                    for e in acct_errors:
                        st.error(e)
                else:
                    with st.spinner("Agregando cuenta…"):
                        add_account(org_id, new_code.strip(), new_acct_name.strip(), new_type, new_dir)
                    st.success(f"✅ Cuenta «{new_code.strip()} — {new_acct_name.strip()}» agregada.")
                    st.rerun()

        # ── Deactivate account ─────────────────────────────────────────────
        custom_accounts = [a for a in active_accounts if not a.get("is_preset")]
        if custom_accounts:
            st.divider()
            with st.expander("🚫 Desactivar cuenta personalizada", expanded=False):
                st.caption(
                    "Solo puedes desactivar cuentas que hayas creado tú. "
                    "Las cuentas predefinidas NIIF no pueden desactivarse desde aquí."
                )
                acct_map = {
                    f"{a['account_code']} — {a['account_name']}": a for a in custom_accounts
                }
                to_deact_acct = st.selectbox("Cuenta a desactivar", list(acct_map.keys()))
                if st.button("🚫 Desactivar Cuenta", type="secondary"):
                    doc = acct_map[to_deact_acct]
                    deactivate_account(doc["account_id"], org_id)
                    st.success(f"Cuenta «{doc['account_name']}» desactivada.")
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — ORG SETTINGS
# ══════════════════════════════════════════════════════════════════════════════
with tab_settings:
    st.subheader("Configuración de la Organización")
    st.caption(
        "Personaliza cómo aparece tu organización en la aplicación. "
        "Los cambios de color se aplican inmediatamente al guardar."
    )

    current_settings = get_org_settings(org_id)

    with st.form("org_settings_form"):
        st.markdown("**Identidad**")
        col_dn, col_logo = st.columns(2)
        with col_dn:
            display_name = st.text_input(
                "Nombre para mostrar",
                value=current_settings.get("display_name", ""),
                placeholder="Ej: La Posada de Jesús A.C.",
                help="Nombre que aparece en el encabezado de la app. Si se deja vacío, se usa el nombre del sistema.",
            )
        with col_logo:
            logo_url = st.text_input(
                "URL del logotipo (opcional)",
                value=current_settings.get("logo_url", ""),
                placeholder="https://ejemplo.com/logo.png",
                help="URL pública de la imagen del logo de tu organización.",
            )

        welcome_message = st.text_area(
            "Mensaje de bienvenida (opcional)",
            value=current_settings.get("welcome_message", ""),
            placeholder="Ej: Bienvenidos al sistema de gestión de La Posada de Jesús.",
            height=80,
            help="Este mensaje aparece en la página de inicio (Resumen).",
        )

        st.divider()
        st.markdown("**Colores de la organización**")
        st.caption(
            "Estos colores definen la apariencia de la app para los usuarios de esta organización. "
            "Usa el formato hexadecimal (#RRGGBB)."
        )
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            primary_color = st.color_picker(
                "Color principal (botones, acentos)",
                value=current_settings.get("primary_color", "#0066CC"),
            )
        with col_c2:
            secondary_color = st.color_picker(
                "Color secundario (fondo de paneles)",
                value=current_settings.get("secondary_color", "#E8F0FE"),
            )

        st.divider()
        st.markdown("**Preferencias de operación**")
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            currency_default = st.selectbox(
                "Moneda predeterminada",
                CURRENCIES,
                index=CURRENCIES.index(current_settings.get("currency_default", "USD"))
                if current_settings.get("currency_default", "USD") in CURRENCIES
                else 0,
                help="Moneda que se pre-selecciona en los formularios de Flujo de Caja.",
            )
        with col_p2:
            low_stock_threshold = st.number_input(
                "Umbral de stock bajo (unidades)",
                min_value=1,
                max_value=9999,
                value=int(current_settings.get("low_stock_threshold", 10)),
                help="Cuando el stock de un artículo baja de este número, se muestra una alerta.",
            )
        with col_p3:
            expiration_warning_days = st.number_input(
                "Días de aviso antes de vencimiento",
                min_value=1,
                max_value=365,
                value=int(current_settings.get("expiration_warning_days", 30)),
                help="El dashboard alertará artículos que vencen en este número de días o menos.",
            )

        saved = st.form_submit_button("💾 Guardar Configuración", type="primary", use_container_width=True)

    if saved:
        new_settings = {
            "display_name": display_name.strip(),
            "logo_url": logo_url.strip(),
            "welcome_message": welcome_message.strip(),
            "primary_color": primary_color,
            "secondary_color": secondary_color,
            "currency_default": currency_default,
            "low_stock_threshold": int(low_stock_threshold),
            "expiration_warning_days": int(expiration_warning_days),
        }
        with st.spinner("Guardando configuración…"):
            update_org_settings(org_id, new_settings)
            reload_org_settings()
        st.success("✅ Configuración guardada. Los colores se aplicarán en el próximo clic de navegación.")
        st.rerun()
