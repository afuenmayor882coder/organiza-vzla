"""
pages/5_Panel_de_Control.py — Dashboard & Overview.

Sections:
  1. Alertas        — expiring, zero-stock, and low-stock warnings.
  2. Inventario     — charts and stock table for donation inventory.
  3. Flujo de Caja  — NIIF cash flow statement + charts.
  4. Resumen        — top donors and top recipients.
"""

from datetime import datetime, timezone

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from db.donations_repo import list_donations
from db.exits_repo import list_exits
from db.finance_repo import get_cash_balance, get_niif_summary, list_transactions
from db.inventory_repo import (
    get_expiring_items,
    get_low_stock_items,
    get_stock,
    get_zero_stock_items,
)
from utils.auth import current_org_id, current_org_name
from utils.constants import NIIF_CATEGORIES
from utils.formatters import format_currency, format_date

org_id = current_org_id()
org = current_org_name() or ""

st.header("📊 Panel de Control")
st.caption(f"Vista general del estado de {org}.")

# ── Time period selector ──────────────────────────────────────────────────────
period_label = st.radio(
    "Período de visualización",
    ["Este mes", "Últimos 3 meses", "Este año", "Todo"],
    horizontal=True,
)

now = datetime.now(timezone.utc)
if period_label == "Este mes":
    start_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
elif period_label == "Últimos 3 meses":
    month = now.month - 3
    year = now.year + (month - 1) // 12
    month = ((month - 1) % 12) + 1
    start_dt = now.replace(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0)
elif period_label == "Este año":
    start_dt = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
else:
    start_dt = datetime(2000, 1, 1, tzinfo=timezone.utc)

# ── Load data ─────────────────────────────────────────────────────────────────
try:
    stock_items = get_stock(org_id)
    expiring = get_expiring_items(org_id, within_days=30)
    zero_stock = get_zero_stock_items(org_id)
    low_stock = get_low_stock_items(org_id, threshold=10)
    donations = list_donations(org_id, limit=2000)
    exits = list_exits(org_id, limit=2000)
    transactions = list_transactions(org_id, limit=2000)
    cash_balance = get_cash_balance(org_id)
    niif_summary = get_niif_summary(org_id, start=start_dt, end=now)
except Exception as exc:
    st.error(f"Error cargando datos: {exc}")
    st.stop()

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 1 — ALERTAS
# ═══════════════════════════════════════════════════════════════════════════════
st.divider()
st.subheader("🔔 Alertas")

alert_count = len(expiring) + len(zero_stock) + len(low_stock)
if alert_count == 0:
    st.success("✅ Sin alertas activas. Todo está bajo control.")
else:
    if expiring:
        st.warning(
            f"⏰ **{len(expiring)} artículo(s) vencen en los próximos 30 días.** "
            "Planifica su distribución."
        )
        with st.expander("Ver artículos por vencer"):
            st.dataframe(
                [
                    {
                        "Artículo": i.get("name", "—"),
                        "Categoría": i.get("category", "—"),
                        "Stock": i.get("current_stock", 0),
                        "Vence": format_date(i.get("expiration_date")),
                    }
                    for i in sorted(
                        expiring,
                        key=lambda x: x.get("expiration_date") or datetime(9999, 12, 31, tzinfo=timezone.utc),
                    )
                ],
                use_container_width=True,
                hide_index=True,
            )

    if zero_stock:
        st.error(
            f"🔴 **{len(zero_stock)} artículo(s) sin stock.** "
            "Considera registrar nuevas donaciones."
        )
        with st.expander("Ver artículos sin stock"):
            st.dataframe(
                [{"Artículo": i.get("name", "—"), "Categoría": i.get("category", "—")}
                 for i in zero_stock],
                use_container_width=True,
                hide_index=True,
            )

    if low_stock:
        low_not_zero = [i for i in low_stock if i.get("current_stock", 0) > 0]
        if low_not_zero:
            st.warning(
                f"🟡 **{len(low_not_zero)} artículo(s) con stock bajo** (≤ 10 unidades)."
            )

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 2 — INVENTARIO
# ═══════════════════════════════════════════════════════════════════════════════
st.divider()
st.subheader("📦 Inventario de Donaciones")

# ── Stock table ───────────────────────────────────────────────────────────────
active_stock = [i for i in stock_items if i.get("current_stock", 0) > 0]
if active_stock:
    col_t, col_pie = st.columns([3, 2])

    with col_t:
        st.markdown("**Stock actual por artículo** (orden: menor primero)")
        st.dataframe(
            [
                {
                    "Artículo": i.get("name", "—"),
                    "Categoría": i.get("category", "—"),
                    "Stock": i.get("current_stock", 0),
                    "Empaque": i.get("packaging", "—"),
                    "Vence": format_date(i.get("expiration_date")),
                }
                for i in active_stock
            ],
            use_container_width=True,
            hide_index=True,
            height=300,
        )

    with col_pie:
        cat_totals = {}
        for i in active_stock:
            cat = i.get("category", "Otros")
            cat_totals[cat] = cat_totals.get(cat, 0) + i.get("current_stock", 0)

        fig_pie = px.pie(
            values=list(cat_totals.values()),
            names=list(cat_totals.keys()),
            title="Stock por Categoría",
            hole=0.35,
        )
        fig_pie.update_layout(margin=dict(t=40, b=0, l=0, r=0), height=300)
        st.plotly_chart(fig_pie, use_container_width=True)

else:
    st.info("Aún no hay artículos en inventario. Registra donaciones primero.")

# ── Donations IN vs Exits OUT bar chart ──────────────────────────────────────
if donations or exits:
    don_rows = [
        {"mes": pd.to_datetime(d["date"]).strftime("%Y-%m"), "qty": d.get("quantity", 0), "tipo": "Donación"}
        for d in donations if d.get("date")
    ]
    exit_rows = [
        {"mes": pd.to_datetime(e["date"]).strftime("%Y-%m"), "qty": e.get("quantity", 0), "tipo": "Salida"}
        for e in exits if e.get("date")
    ]
    all_rows = don_rows + exit_rows

    if all_rows:
        df_mov = pd.DataFrame(all_rows)
        df_agg = df_mov.groupby(["mes", "tipo"])["qty"].sum().reset_index()
        fig_bar = px.bar(
            df_agg,
            x="mes",
            y="qty",
            color="tipo",
            barmode="group",
            title="Donaciones vs Salidas por Mes",
            labels={"mes": "Mes", "qty": "Unidades", "tipo": ""},
            color_discrete_map={"Donación": "#0066CC", "Salida": "#E63946"},
        )
        fig_bar.update_layout(margin=dict(t=40, b=0), height=320)
        st.plotly_chart(fig_bar, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 3 — FLUJO DE CAJA NIIF
# ═══════════════════════════════════════════════════════════════════════════════
st.divider()
st.subheader("💰 Flujo de Caja NIIF")

col_bal_d, col_bar_d = st.columns([1, 3])
with col_bal_d:
    sign = "+" if cash_balance >= 0 else ""
    st.metric("Saldo Total", f"{sign}$ {cash_balance:,.2f}")

# NIIF Statement
niif_display = [
    {"Actividades de Operacion": "Operación"},
    {"Actividades de Inversion": "Inversión"},
    {"Actividades de Financiamiento": "Financiamiento"},
]

st.markdown("**Estado de Flujo de Efectivo (NIIF)**")
total_net = 0.0
niif_rows = []
for cat_key, cat_label in [
    ("Actividades de Operacion", "Actividades de Operación"),
    ("Actividades de Inversion", "Actividades de Inversión"),
    ("Actividades de Financiamiento", "Actividades de Financiamiento"),
]:
    net = niif_summary.get(cat_key, 0.0)
    total_net += net
    sign_str = "+" if net >= 0 else ""
    niif_rows.append({"Sección": cat_label, "Flujo Neto": f"{sign_str}$ {net:,.2f}"})

niif_rows.append({"Sección": "🔵 Variación Neta del Efectivo", "Flujo Neto": f"$ {total_net:,.2f}"})
st.dataframe(pd.DataFrame(niif_rows), use_container_width=True, hide_index=True)

# Cash flow bar chart
if transactions:
    tx_rows = [
        {
            "mes": pd.to_datetime(t["date"]).strftime("%Y-%m"),
            "monto": t.get("amount", 0),
            "tipo": t.get("direction", "Egreso"),
        }
        for t in transactions if t.get("date")
    ]
    if tx_rows:
        df_tx = pd.DataFrame(tx_rows)
        df_tx_agg = df_tx.groupby(["mes", "tipo"])["monto"].sum().reset_index()
        fig_cash = px.bar(
            df_tx_agg,
            x="mes",
            y="monto",
            color="tipo",
            barmode="group",
            title="Ingresos vs Egresos por Mes",
            labels={"mes": "Mes", "monto": "Monto ($)", "tipo": ""},
            color_discrete_map={"Ingreso": "#2DC653", "Egreso": "#E63946"},
        )
        fig_cash.update_layout(margin=dict(t=40, b=0), height=300)
        st.plotly_chart(fig_cash, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  SECTION 4 — COMBINED SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
st.divider()
st.subheader("🏆 Resumen Combinado")

col_don_top, col_rec_top = st.columns(2)

with col_don_top:
    st.markdown("**Top Donantes**")
    if donations:
        df_donors = pd.DataFrame(donations)
        top_donors = (
            df_donors.groupby("donor_name")["quantity"]
            .agg(total="sum", registros="count")
            .sort_values("total", ascending=False)
            .head(10)
            .reset_index()
            .rename(columns={"donor_name": "Donante", "total": "Total unidades", "registros": "Registros"})
        )
        st.dataframe(top_donors, use_container_width=True, hide_index=True)
    else:
        st.info("Sin datos de donantes aún.")

with col_rec_top:
    st.markdown("**Top Receptores**")
    if exits:
        df_recs = pd.DataFrame(exits)
        top_recs = (
            df_recs.groupby("recipient_name")["quantity"]
            .agg(total="sum", registros="count")
            .sort_values("total", ascending=False)
            .head(10)
            .reset_index()
            .rename(columns={"recipient_name": "Receptor", "total": "Total unidades", "registros": "Registros"})
        )
        st.dataframe(top_recs, use_container_width=True, hide_index=True)
    else:
        st.info("Sin datos de receptores aún.")
