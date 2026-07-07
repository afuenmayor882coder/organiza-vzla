"""
pages/5_Panel_de_Control.py — Dashboard & Overview.

Organized in four tabs:
  1. Resumen General  — KPI cards + key summary charts
  2. Inventario       — stock trends, category breakdowns, item charts
  3. Finanzas         — NIIF cash flow statement + waterfall, area, pies
  4. Donantes y Receptores — stakeholder analysis + activity trends
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
from utils.auth import current_org_id, current_org_name, current_org_settings
from utils.constants import NIIF_CATEGORIES
from utils.formatters import format_currency, format_date

org_id = current_org_id()
org    = current_org_name() or ""

# Read org-level thresholds from settings (falls back to defaults)
_settings              = current_org_settings()
LOW_STOCK_THRESHOLD    = int(_settings.get("low_stock_threshold", 10))
EXPIRATION_WARN_DAYS   = int(_settings.get("expiration_warning_days", 30))
ORG_PRIMARY_COLOR      = _settings.get("primary_color", "#0066CC")

st.header("📊 Panel de Control")
st.caption(f"Vista general del estado de {org}.")

# ── Time period selector ──────────────────────────────────────────────────────
period_label = st.radio(
    "Período",
    ["Este mes", "Últimos 3 meses", "Este año", "Todo"],
    horizontal=True,
)

now = datetime.now(timezone.utc)
if period_label == "Este mes":
    start_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
elif period_label == "Últimos 3 meses":
    month = now.month - 3
    year  = now.year + (month - 1) // 12
    month = ((month - 1) % 12) + 1
    start_dt = now.replace(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0)
elif period_label == "Este año":
    start_dt = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
else:
    start_dt = datetime(2000, 1, 1, tzinfo=timezone.utc)

# ── Load all data once ────────────────────────────────────────────────────────
try:
    stock_items  = get_stock(org_id)
    expiring     = get_expiring_items(org_id, within_days=EXPIRATION_WARN_DAYS)
    zero_stock   = get_zero_stock_items(org_id)
    low_stock    = get_low_stock_items(org_id, threshold=LOW_STOCK_THRESHOLD)
    donations    = list_donations(org_id, limit=3000)
    exits        = list_exits(org_id, limit=3000)
    transactions = list_transactions(org_id, limit=3000)
    cash_balance = get_cash_balance(org_id)
    niif_summary = get_niif_summary(org_id, start=start_dt, end=now)
except Exception as exc:
    st.error(f"Error cargando datos: {exc}")
    st.stop()

# Filter donations/exits/transactions to the selected period
def _in_period(records: list[dict]) -> list[dict]:
    return [r for r in records if r.get("date") and r["date"] >= start_dt]

don_period  = _in_period(donations)
exit_period = _in_period(exits)
tx_period   = _in_period(transactions)

# ── Helper: empty-state message ───────────────────────────────────────────────
def _no_data(msg: str = "Sin datos para el período seleccionado.") -> None:
    st.info(msg)

# ═══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD TABS
# ═══════════════════════════════════════════════════════════════════════════════
tab_resumen, tab_inv, tab_fin, tab_stakeholders = st.tabs(
    ["📋 Resumen General", "📦 Inventario", "💰 Finanzas", "🤝 Donantes y Receptores"]
)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — RESUMEN GENERAL
# ══════════════════════════════════════════════════════════════════════════════
with tab_resumen:
    # ── KPI metrics ───────────────────────────────────────────────────────────
    total_stock     = sum(i.get("current_stock", 0) for i in stock_items)
    total_donations = sum(d.get("quantity", 0) for d in don_period)
    total_exits_qty = sum(e.get("quantity", 0) for e in exit_period)
    total_income    = sum(t.get("amount", 0) for t in tx_period if t.get("direction") == "Ingreso")
    total_expense   = sum(t.get("amount", 0) for t in tx_period if t.get("direction") == "Egreso")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Artículos en Stock", f"{total_stock:,}", help="Total de unidades en inventario ahora.")
    k2.metric("Donaciones Recibidas", f"{total_donations:,}", help=f"Unidades recibidas en el período seleccionado.")
    k3.metric("Salidas Registradas", f"{total_exits_qty:,}", help=f"Unidades distribuidas en el período.")
    sign = "+" if cash_balance >= 0 else ""
    k4.metric("Saldo en Efectivo", f"{sign}$ {cash_balance:,.2f}", help="Saldo total acumulado (ingresos − egresos).")

    st.divider()

    # ── Alerts banner ─────────────────────────────────────────────────────────
    st.subheader("🔔 Alertas")
    alert_count = len(expiring) + len(zero_stock)
    low_not_zero = [i for i in low_stock if i.get("current_stock", 0) > 0]

    if alert_count == 0 and not low_not_zero:
        st.success("✅ Sin alertas activas. Todo está bajo control.")
    else:
        if expiring:
            st.warning(
                f"⏰ **{len(expiring)} artículo(s) vencen en los próximos "
                f"{EXPIRATION_WARN_DAYS} días.** Planifica su distribución."
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
        if low_not_zero:
            st.warning(
                f"🟡 **{len(low_not_zero)} artículo(s) con stock bajo** "
                f"(≤ {LOW_STOCK_THRESHOLD} unidades)."
            )

    st.divider()

    # ── Gauge: inventory health ────────────────────────────────────────────────
    if stock_items:
        healthy   = sum(1 for i in stock_items if i.get("current_stock", 0) > LOW_STOCK_THRESHOLD)
        health_pct = round(healthy / len(stock_items) * 100) if stock_items else 0

        col_gauge, col_mini = st.columns([1, 2])
        with col_gauge:
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=health_pct,
                title={"text": "Salud del Inventario"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": ORG_PRIMARY_COLOR},
                    "steps": [
                        {"range": [0, 30],  "color": "#FFE0E0"},
                        {"range": [30, 70], "color": "#FFF3CD"},
                        {"range": [70, 100],"color": "#D4EDDA"},
                    ],
                    "threshold": {
                        "line": {"color": "#333", "width": 2},
                        "thickness": 0.75,
                        "value": health_pct,
                    },
                },
                number={"suffix": "%"},
            ))
            fig_gauge.update_layout(height=220, margin=dict(t=30, b=0, l=20, r=20))
            st.plotly_chart(fig_gauge, use_container_width=True)

        with col_mini:
            if don_period or exit_period:
                don_rows = [
                    {"mes": pd.to_datetime(d["date"]).strftime("%Y-%m"),
                     "qty": d.get("quantity", 0), "tipo": "Donación"}
                    for d in don_period
                ]
                exit_rows = [
                    {"mes": pd.to_datetime(e["date"]).strftime("%Y-%m"),
                     "qty": e.get("quantity", 0), "tipo": "Salida"}
                    for e in exit_period
                ]
                df_mov = pd.DataFrame(don_rows + exit_rows)
                df_agg = df_mov.groupby(["mes", "tipo"])["qty"].sum().reset_index()
                fig_summary_bar = px.bar(
                    df_agg, x="mes", y="qty", color="tipo", barmode="group",
                    title="Donaciones vs Salidas por Mes",
                    labels={"mes": "Mes", "qty": "Unidades", "tipo": ""},
                    color_discrete_map={"Donación": ORG_PRIMARY_COLOR, "Salida": "#E63946"},
                )
                fig_summary_bar.update_layout(height=220, margin=dict(t=30, b=0))
                st.plotly_chart(fig_summary_bar, use_container_width=True)
    else:
        _no_data("Registra donaciones para ver el resumen de inventario.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — INVENTARIO
# ══════════════════════════════════════════════════════════════════════════════
with tab_inv:
    active_stock = [i for i in stock_items if i.get("current_stock", 0) > 0]

    if not active_stock and not don_period:
        _no_data("Registra donaciones para ver el inventario.")
    else:
        # ── Row 1: Stock table + Category donut ──────────────────────────────
        col_tbl, col_donut = st.columns([3, 2])

        with col_tbl:
            st.markdown("**Stock actual (orden: menor primero)**")
            st.dataframe(
                [
                    {
                        "Artículo": i.get("name", "—"),
                        "Categoría": i.get("category", "—"),
                        "Stock": i.get("current_stock", 0),
                        "Empaque": i.get("packaging", "—"),
                        "Vence": format_date(i.get("expiration_date")),
                    }
                    for i in sorted(active_stock, key=lambda x: x.get("current_stock", 0))
                ],
                use_container_width=True,
                hide_index=True,
                height=280,
            )

        with col_donut:
            cat_totals: dict = {}
            for i in active_stock:
                cat = i.get("category", "Otros")
                cat_totals[cat] = cat_totals.get(cat, 0) + i.get("current_stock", 0)
            if cat_totals:
                fig_donut = px.pie(
                    values=list(cat_totals.values()),
                    names=list(cat_totals.keys()),
                    title="Stock por Categoría",
                    hole=0.4,
                )
                fig_donut.update_layout(margin=dict(t=40, b=0, l=0, r=0), height=280)
                st.plotly_chart(fig_donut, use_container_width=True)

        st.divider()

        # ── Row 2: Horizontal bar — top 15 items by stock ────────────────────
        if active_stock:
            top_items = sorted(active_stock, key=lambda x: x.get("current_stock", 0), reverse=True)[:15]
            df_top = pd.DataFrame([
                {"name": i.get("name", "—"), "stock": i.get("current_stock", 0)}
                for i in top_items
            ])
            fig_hbar = px.bar(
                df_top,
                x="stock",
                y="name",
                orientation="h",
                title="Top 15 Artículos por Stock",
                labels={"stock": "Unidades en Stock", "name": "Artículo"},
                color="stock",
                color_continuous_scale=["#D4EDDA", ORG_PRIMARY_COLOR],
            )
            fig_hbar.update_layout(
                height=400,
                margin=dict(t=40, b=0),
                yaxis={"categoryorder": "total ascending"},
                coloraxis_showscale=False,
            )
            st.plotly_chart(fig_hbar, use_container_width=True)

        st.divider()

        # ── Row 3: Stacked bar — donations by category per month ─────────────
        if don_period:
            df_don = pd.DataFrame([
                {
                    "mes": pd.to_datetime(d["date"]).strftime("%Y-%m"),
                    "categoria": d.get("category", "Otros"),
                    "qty": d.get("quantity", 0),
                }
                for d in don_period
            ])
            df_don_agg = df_don.groupby(["mes", "categoria"])["qty"].sum().reset_index()
            fig_stack = px.bar(
                df_don_agg,
                x="mes", y="qty", color="categoria",
                barmode="stack",
                title="Donaciones por Categoría y Mes",
                labels={"mes": "Mes", "qty": "Unidades", "categoria": "Categoría"},
            )
            fig_stack.update_layout(height=320, margin=dict(t=40, b=0))
            st.plotly_chart(fig_stack, use_container_width=True)

        st.divider()

        # ── Row 4: Treemap — inventory by category + subcategory ─────────────
        if active_stock:
            df_tree = pd.DataFrame([
                {
                    "category": i.get("category", "Otros"),
                    "subcategory": i.get("subcategory", "Sin Clasificar"),
                    "name": i.get("name", "—"),
                    "stock": i.get("current_stock", 0),
                }
                for i in active_stock
            ])
            fig_tree = px.treemap(
                df_tree,
                path=["category", "subcategory", "name"],
                values="stock",
                title="Mapa de Inventario (Categoría → Subcategoría → Artículo)",
                color="stock",
                color_continuous_scale=["#E8F0FE", ORG_PRIMARY_COLOR],
            )
            fig_tree.update_layout(height=420, margin=dict(t=40, b=0))
            fig_tree.update_traces(textinfo="label+value")
            st.plotly_chart(fig_tree, use_container_width=True)

        st.divider()

        # ── Row 5: Expiration timeline (next 90 days) ─────────────────────────
        exp_90 = get_expiring_items(org_id, within_days=90)
        if exp_90:
            df_exp = pd.DataFrame([
                {
                    "Artículo": i.get("name", "—"),
                    "Stock":    i.get("current_stock", 0),
                    "Vence":    pd.to_datetime(i.get("expiration_date")),
                    "Categoría": i.get("category", "—"),
                }
                for i in exp_90 if i.get("expiration_date")
            ])
            if not df_exp.empty:
                df_exp = df_exp.sort_values("Vence")
                fig_timeline = px.scatter(
                    df_exp,
                    x="Vence",
                    y="Artículo",
                    size="Stock",
                    color="Categoría",
                    title=f"Vencimientos Próximos (próximos 90 días)",
                    labels={"Vence": "Fecha de Vencimiento"},
                    hover_data={"Stock": True, "Vence": "|%d %b %Y"},
                )
                fig_timeline.update_layout(height=380, margin=dict(t=40, b=0))
                st.plotly_chart(fig_timeline, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — FINANZAS
# ══════════════════════════════════════════════════════════════════════════════
with tab_fin:
    # ── KPI row ───────────────────────────────────────────────────────────────
    income_total  = sum(t.get("amount", 0) for t in tx_period if t.get("direction") == "Ingreso")
    expense_total = sum(t.get("amount", 0) for t in tx_period if t.get("direction") == "Egreso")
    net_period    = income_total - expense_total

    f1, f2, f3, f4 = st.columns(4)
    f1.metric("Ingresos (período)",  f"$ {income_total:,.2f}")
    f2.metric("Egresos (período)",   f"$ {expense_total:,.2f}")
    f3.metric("Resultado del Período", f"{'+'  if net_period>=0 else ''}$ {net_period:,.2f}")
    sign_bal = "+" if cash_balance >= 0 else ""
    f4.metric("Saldo Acumulado",     f"{sign_bal}$ {cash_balance:,.2f}")

    st.divider()

    # ── NIIF Statement ────────────────────────────────────────────────────────
    st.markdown("**Estado de Flujo de Efectivo (NIIF)**")
    total_net = 0.0
    niif_rows = []
    for cat_key, cat_label in [
        ("Actividades de Operacion",      "Actividades de Operación"),
        ("Actividades de Inversion",       "Actividades de Inversión"),
        ("Actividades de Financiamiento", "Actividades de Financiamiento"),
    ]:
        net = niif_summary.get(cat_key, 0.0)
        total_net += net
        s = "+" if net >= 0 else ""
        niif_rows.append({"Sección": cat_label, "Flujo Neto": f"{s}$ {net:,.2f}"})
    niif_rows.append({"Sección": "🔵 Variación Neta del Efectivo", "Flujo Neto": f"$ {total_net:,.2f}"})
    st.dataframe(pd.DataFrame(niif_rows), use_container_width=True, hide_index=True)

    st.divider()

    if tx_period:
        df_tx = pd.DataFrame(tx_period)
        df_tx["mes"] = pd.to_datetime(df_tx["date"]).dt.strftime("%Y-%m")
        df_tx["amount"] = pd.to_numeric(df_tx["amount"], errors="coerce").fillna(0)

        # ── Row 1: Ingresos vs Egresos bar + Cumulative area ─────────────────
        col_bar_f, col_area = st.columns(2)

        with col_bar_f:
            df_month = df_tx.groupby(["mes", "direction"])["amount"].sum().reset_index()
            fig_cash_bar = px.bar(
                df_month, x="mes", y="amount", color="direction", barmode="group",
                title="Ingresos vs Egresos por Mes",
                labels={"mes": "Mes", "amount": "Monto ($)", "direction": ""},
                color_discrete_map={"Ingreso": "#2DC653", "Egreso": "#E63946"},
            )
            fig_cash_bar.update_layout(height=300, margin=dict(t=40, b=0))
            st.plotly_chart(fig_cash_bar, use_container_width=True)

        with col_area:
            df_sorted = df_tx.sort_values("date")
            df_sorted["signed"] = df_sorted.apply(
                lambda r: r["amount"] if r["direction"] == "Ingreso" else -r["amount"], axis=1
            )
            df_sorted["cumulative"] = df_sorted["signed"].cumsum()
            fig_area = px.area(
                df_sorted, x="date", y="cumulative",
                title="Saldo Acumulado en el Tiempo",
                labels={"date": "Fecha", "cumulative": "Saldo ($)"},
                color_discrete_sequence=[ORG_PRIMARY_COLOR],
            )
            fig_area.update_layout(height=300, margin=dict(t=40, b=0))
            st.plotly_chart(fig_area, use_container_width=True)

        st.divider()

        # ── Row 2: Waterfall chart ────────────────────────────────────────────
        waterfall_cats = [
            ("Actividades de Operacion",       "Operación"),
            ("Actividades de Inversion",        "Inversión"),
            ("Actividades de Financiamiento",  "Financiamiento"),
        ]
        wf_names  = []
        wf_values = []
        wf_types  = []
        for key, label in waterfall_cats:
            val = niif_summary.get(key, 0.0)
            wf_names.append(label)
            wf_values.append(val)
            wf_types.append("relative")

        if any(v != 0 for v in wf_values):
            wf_names.append("Variación Neta")
            wf_values.append(sum(wf_values))
            wf_types.append("total")

            fig_wf = go.Figure(go.Waterfall(
                name="Flujo NIIF",
                orientation="v",
                measure=wf_types,
                x=wf_names,
                y=wf_values,
                connector={"line": {"color": "#999"}},
                increasing={"marker": {"color": "#2DC653"}},
                decreasing={"marker": {"color": "#E63946"}},
                totals={"marker": {"color": ORG_PRIMARY_COLOR}},
                text=[f"$ {v:,.0f}" for v in wf_values],
                textposition="outside",
            ))
            fig_wf.update_layout(
                title="Flujo de Caja por Sección NIIF (Waterfall)",
                height=340,
                margin=dict(t=40, b=0),
            )
            st.plotly_chart(fig_wf, use_container_width=True)

        st.divider()

        # ── Row 3: Income pie + Expense pie ──────────────────────────────────
        col_in_pie, col_out_pie = st.columns(2)

        with col_in_pie:
            df_in = df_tx[df_tx["direction"] == "Ingreso"]
            if not df_in.empty:
                in_sub = df_in.groupby("subcategory")["amount"].sum().reset_index()
                fig_in_pie = px.pie(
                    in_sub, values="amount", names="subcategory",
                    title="Desglose de Ingresos (por subcategoría)",
                    hole=0.3,
                )
                fig_in_pie.update_layout(height=300, margin=dict(t=40, b=0, l=0, r=0))
                st.plotly_chart(fig_in_pie, use_container_width=True)
            else:
                _no_data("Sin ingresos en el período.")

        with col_out_pie:
            df_out = df_tx[df_tx["direction"] == "Egreso"]
            if not df_out.empty:
                out_sub = df_out.groupby("subcategory")["amount"].sum().reset_index()
                fig_out_pie = px.pie(
                    out_sub, values="amount", names="subcategory",
                    title="Desglose de Egresos (por subcategoría)",
                    hole=0.3,
                    color_discrete_sequence=px.colors.sequential.Reds,
                )
                fig_out_pie.update_layout(height=300, margin=dict(t=40, b=0, l=0, r=0))
                st.plotly_chart(fig_out_pie, use_container_width=True)
            else:
                _no_data("Sin egresos en el período.")

    else:
        _no_data("No hay transacciones financieras para el período seleccionado.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — DONANTES Y RECEPTORES
# ══════════════════════════════════════════════════════════════════════════════
with tab_stakeholders:
    if not donations and not exits:
        _no_data("Registra donaciones y salidas para ver el análisis de donantes y receptores.")
    else:
        # ── Top donors bar ────────────────────────────────────────────────────
        col_don, col_rec = st.columns(2)

        with col_don:
            if donations:
                df_donors = pd.DataFrame(donations)
                top_don = (
                    df_donors.groupby("donor_name")["quantity"]
                    .sum()
                    .sort_values(ascending=False)
                    .head(10)
                    .reset_index()
                )
                top_don.columns = ["Donante", "Total Unidades"]
                fig_don = px.bar(
                    top_don, x="Total Unidades", y="Donante", orientation="h",
                    title="Top 10 Donantes (por unidades)",
                    color="Total Unidades",
                    color_continuous_scale=["#D4EDDA", "#2DC653"],
                )
                fig_don.update_layout(
                    height=360, margin=dict(t=40, b=0),
                    yaxis={"categoryorder": "total ascending"},
                    coloraxis_showscale=False,
                )
                st.plotly_chart(fig_don, use_container_width=True)
            else:
                _no_data("Sin datos de donantes.")

        with col_rec:
            if exits:
                df_recs = pd.DataFrame(exits)
                top_rec = (
                    df_recs.groupby("recipient_name")["quantity"]
                    .sum()
                    .sort_values(ascending=False)
                    .head(10)
                    .reset_index()
                )
                top_rec.columns = ["Receptor", "Total Unidades"]
                fig_rec = px.bar(
                    top_rec, x="Total Unidades", y="Receptor", orientation="h",
                    title="Top 10 Receptores (por unidades)",
                    color="Total Unidades",
                    color_continuous_scale=["#FFE0E0", "#E63946"],
                )
                fig_rec.update_layout(
                    height=360, margin=dict(t=40, b=0),
                    yaxis={"categoryorder": "total ascending"},
                    coloraxis_showscale=False,
                )
                st.plotly_chart(fig_rec, use_container_width=True)
            else:
                _no_data("Sin datos de receptores.")

        st.divider()

        # ── Donor activity trend: unique donors per month ─────────────────────
        if don_period:
            df_don_trend = pd.DataFrame([
                {
                    "mes": pd.to_datetime(d["date"]).strftime("%Y-%m"),
                    "donor": d.get("donor_name", "Desconocido"),
                }
                for d in don_period
            ])
            df_unique_donors = (
                df_don_trend.groupby("mes")["donor"]
                .nunique()
                .reset_index()
                .rename(columns={"mes": "Mes", "donor": "Donantes Únicos"})
            )
            fig_trend = px.line(
                df_unique_donors, x="Mes", y="Donantes Únicos",
                markers=True,
                title="Tendencia de Donantes Únicos por Mes",
                labels={"Mes": "Mes", "Donantes Únicos": "Nº de Donantes"},
                color_discrete_sequence=[ORG_PRIMARY_COLOR],
            )
            fig_trend.update_traces(line_width=2.5)
            fig_trend.update_layout(height=300, margin=dict(t=40, b=0))
            st.plotly_chart(fig_trend, use_container_width=True)

        st.divider()

        # ── Category breakdown: what types do donors give most? ───────────────
        if don_period:
            df_cat_don = pd.DataFrame([
                {
                    "categoria": d.get("category", "Otros"),
                    "qty": d.get("quantity", 0),
                    "donor": d.get("donor_name", "—"),
                }
                for d in don_period
            ])
            cat_summary = (
                df_cat_don.groupby("categoria")["qty"]
                .sum()
                .sort_values(ascending=False)
                .reset_index()
                .rename(columns={"categoria": "Categoría", "qty": "Unidades Donadas"})
            )
            fig_cat = px.bar(
                cat_summary, x="Categoría", y="Unidades Donadas",
                title="Donaciones por Categoría (período seleccionado)",
                color="Unidades Donadas",
                color_continuous_scale=["#D4EDDA", ORG_PRIMARY_COLOR],
            )
            fig_cat.update_layout(height=300, margin=dict(t=40, b=0), coloraxis_showscale=False)
            st.plotly_chart(fig_cat, use_container_width=True)

        st.divider()

        # ── Side by side tables ───────────────────────────────────────────────
        col_dt, col_rt = st.columns(2)
        with col_dt:
            st.markdown("**Tabla Donantes**")
            if donations:
                df_don_tbl = pd.DataFrame(donations)
                tbl = (
                    df_don_tbl.groupby("donor_name")["quantity"]
                    .agg(total="sum", registros="count")
                    .sort_values("total", ascending=False)
                    .head(20)
                    .reset_index()
                    .rename(columns={"donor_name": "Donante", "total": "Unidades", "registros": "Entregas"})
                )
                st.dataframe(tbl, use_container_width=True, hide_index=True)
        with col_rt:
            st.markdown("**Tabla Receptores**")
            if exits:
                df_rec_tbl = pd.DataFrame(exits)
                tbl_r = (
                    df_rec_tbl.groupby("recipient_name")["quantity"]
                    .agg(total="sum", registros="count")
                    .sort_values("total", ascending=False)
                    .head(20)
                    .reset_index()
                    .rename(columns={"recipient_name": "Receptor", "total": "Unidades", "registros": "Entregas"})
                )
                st.dataframe(tbl_r, use_container_width=True, hide_index=True)
