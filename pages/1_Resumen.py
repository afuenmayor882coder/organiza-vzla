"""
pages/1_Resumen.py — Home page with summary cards for the current organization.

Shows four key metrics at a glance:
  • Total units in stock
  • Donations received this month
  • Current cash balance
  • Items expiring within 30 days (with a warning table)
"""

from datetime import datetime, timezone

import streamlit as st

from db.donations_repo import count_donations_this_month
from db.finance_repo import get_cash_balance
from db.inventory_repo import get_expiring_items, get_stock
from utils.auth import current_active_org_id, current_org_name, current_user_name
from utils.formatters import format_date

# ── Spanish date helpers ───────────────────────────────────────────────────────
_MESES = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]
_DIAS = [
    "lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo",
]


def _fecha_es(dt: datetime) -> str:
    return f"{_DIAS[dt.weekday()]}, {dt.day} de {_MESES[dt.month]} de {dt.year}"


# ── Header ─────────────────────────────────────────────────────────────────────
org_id = current_active_org_id()
user_name = current_user_name() or "Usuario"
org = current_org_name() or ""
now = datetime.now()

st.markdown(f"# 👋 Bienvenido, {user_name}!")
st.caption(f"🏢 {org}  ·  {_fecha_es(now).capitalize()}")
st.divider()

# ── Load data from MongoDB ─────────────────────────────────────────────────────
try:
    stock_items = get_stock(org_id)
    total_units = sum(
        max(0, item.get("current_stock", 0)) for item in stock_items
    )
    active_item_count = len(
        [i for i in stock_items if i.get("current_stock", 0) > 0]
    )
    donations_this_month = count_donations_this_month(org_id)
    cash_balance = get_cash_balance(org_id)
    expiring = get_expiring_items(org_id, within_days=30)

except Exception as exc:
    st.error(
        "No se pudo conectar con la base de datos. "
        "Recarga la página o contacta al administrador."
    )
    st.caption(f"Detalle técnico: {exc}")
    st.stop()

# ── 4 Summary metric cards ─────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="📦 Unidades en Stock",
        value=f"{total_units:,}",
        help=(
            f"Total de unidades disponibles en inventario. "
            f"({active_item_count} tipo(s) de artículo con stock mayor a cero.)"
        ),
    )

with col2:
    st.metric(
        label="📥 Donaciones este mes",
        value=f"{donations_this_month:,}",
        help="Número de registros de donación ingresados durante el mes actual.",
    )

with col3:
    balance_sign = "+" if cash_balance >= 0 else ""
    st.metric(
        label="💰 Saldo en Caja",
        value=f"{balance_sign}$ {cash_balance:,.2f}",
        help=(
            "Suma total de todos los ingresos menos todos los egresos registrados. "
            "Incluye todas las monedas registradas en el sistema."
        ),
    )

with col4:
    exp_count = len(expiring)
    st.metric(
        label="⏰ Por Vencer (30 días)",
        value=exp_count,
        help=(
            "Artículos en inventario cuya fecha de vencimiento cae "
            "dentro de los próximos 30 días y aún tienen stock disponible."
        ),
    )

st.divider()

# ── Expiration alert section ───────────────────────────────────────────────────
if expiring:
    st.warning(
        f"⚠️  **{exp_count} artículo(s) vencen en los próximos 30 días.** "
        "Planifica su distribución antes de que se venzan."
    )

    sorted_expiring = sorted(
        expiring,
        key=lambda x: x.get("expiration_date") or datetime(9999, 12, 31, tzinfo=timezone.utc),
    )

    with st.expander("📋 Ver lista de artículos por vencer", expanded=True):
        rows = [
            {
                "Artículo": item.get("name", "—"),
                "Categoría": item.get("category", "—"),
                "Stock disponible": item.get("current_stock", 0),
                "Fecha de vencimiento": format_date(item.get("expiration_date")),
            }
            for item in sorted_expiring
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)

else:
    st.success("✅ Ningún artículo vence en los próximos 30 días.")

# ── Empty state ────────────────────────────────────────────────────────────────
if total_units == 0 and donations_this_month == 0 and cash_balance == 0.0:
    st.divider()
    st.info(
        "🚀 **¡Todo listo para empezar!**\n\n"
        "Todavía no hay datos registrados para tu organización. "
        "Usa el menú de la izquierda para:\n\n"
        "- **📥 Donaciones** → registrar los artículos que recibe la organización\n"
        "- **📤 Salidas** → registrar distribuciones a beneficiarios\n"
        "- **💰 Flujo de Caja** → anotar movimientos de dinero"
    )
