"""
pages/4_Flujo_de_Caja.py — Cash Flow (NIIF-based financial registration).

Two tabs:
  1. Registro Manual  — one transaction at a time.
  2. Importar Estado de Cuenta — upload CSV/Excel bank statement,
     auto-classify with keyword matching, review, and bulk-insert.
"""

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from db.finance_repo import (
    add_transaction,
    add_transactions_batch,
    get_cash_balance,
    list_transactions,
)
from utils.auth import current_org_id, current_user_email
from utils.constants import CURRENCIES, FLOW_DIRECTIONS, NIIF_CATEGORIES
from utils.formatters import format_currency, format_date
from utils.niif import classify_description
from utils.validators import validate_transaction_form

org_id = current_org_id()
user = current_user_email() or "system"

st.header("💰 Flujo de Caja")
st.caption("Registra los movimientos de dinero siguiendo la clasificación NIIF (IFRS).")

# ── Current balance banner ────────────────────────────────────────────────────
try:
    balance = get_cash_balance(org_id)
    sign = "+" if balance >= 0 else ""
    col_bal, _ = st.columns([1, 3])
    with col_bal:
        st.metric(
            "Saldo Actual (todas las monedas)",
            f"{sign}$ {balance:,.2f}",
        )
except Exception:
    pass

st.divider()

tab_manual, tab_import = st.tabs(
    ["📝 Registro Manual", "📂 Importar Estado de Cuenta"]
)

# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 1 — MANUAL ENTRY
# ═══════════════════════════════════════════════════════════════════════════════
with tab_manual:
    st.subheader("Nueva Transacción")

    col_date, col_dir = st.columns(2)
    with col_date:
        tx_date = st.date_input(
            "Fecha *",
            value=datetime.now().date(),
            help="Fecha en que ocurrió la transacción.",
        )
    with col_dir:
        direction = st.radio(
            "Dirección *",
            FLOW_DIRECTIONS,
            horizontal=True,
            help="Ingreso = dinero que entra. Egreso = dinero que sale.",
        )

    col_curr, col_amt = st.columns(2)
    with col_curr:
        currency = st.radio(
            "Moneda *",
            CURRENCIES,
            horizontal=True,
        )
    with col_amt:
        amount = st.number_input(
            "Monto *",
            min_value=0.01,
            step=0.01,
            format="%.2f",
            help="Monto de la transacción.",
        )

    # NIIF category → subcategory (cascading)
    col_niif, col_sub = st.columns(2)
    with col_niif:
        niif_category = st.selectbox(
            "Categoría NIIF *",
            list(NIIF_CATEGORIES.keys()),
            help=(
                "Operacion = actividades del día a día.  "
                "Inversion = compra/venta de activos.  "
                "Financiamiento = préstamos."
            ),
        )
    with col_sub:
        subcategory = st.selectbox(
            "Subcategoría *",
            NIIF_CATEGORIES[niif_category],
        )

    description = st.text_input(
        "Descripción *",
        placeholder="Ej: Pago de alquiler enero 2025",
        help="Describe brevemente en qué consiste este movimiento.",
    )
    source_bank = st.text_input(
        "Banco / Cuenta de Origen",
        placeholder="Opcional — ej: Banesco USD",
    )

    st.divider()
    if st.button("✅ Registrar Transacción", type="primary", use_container_width=True):
        errors = validate_transaction_form(amount, description, niif_category, subcategory)
        if errors:
            for err in errors:
                st.error(err)
        else:
            tx_datetime = datetime(
                tx_date.year, tx_date.month, tx_date.day, tzinfo=timezone.utc
            )
            with st.spinner("Guardando…"):
                add_transaction(
                    org_id=org_id,
                    date=tx_datetime,
                    amount=float(amount),
                    currency=currency,
                    direction=direction,
                    niif_category=niif_category,
                    subcategory=subcategory,
                    description=description.strip(),
                    source_bank=source_bank.strip(),
                    user=user,
                )
            st.success(
                f"✅ Transacción registrada: **{format_currency(float(amount), currency)}** "
                f"({direction}) — {description.strip()}."
            )
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 2 — BANK STATEMENT IMPORT
# ═══════════════════════════════════════════════════════════════════════════════
with tab_import:
    st.subheader("Importar Estado de Cuenta")
    st.info(
        "Sube un archivo CSV o Excel. El archivo debe tener estas columnas "
        "(los nombres exactos no importan, tú las mapeas abajo):\n\n"
        "**Fecha · Descripcion · Monto · Tipo** (Ingreso o Egreso)"
    )

    with st.expander("📥 Descargar plantilla de ejemplo"):
        sample = pd.DataFrame(
            {
                "Fecha": ["2025-01-15", "2025-01-16", "2025-01-20"],
                "Descripcion": [
                    "Donacion Cruz Roja",
                    "Pago alquiler oficina",
                    "Compra suministros medicos",
                ],
                "Monto": [500.00, 200.00, 150.00],
                "Tipo": ["Ingreso", "Egreso", "Egreso"],
            }
        )
        st.download_button(
            "⬇️ Descargar CSV de ejemplo",
            sample.to_csv(index=False).encode("utf-8"),
            file_name="plantilla_estado_cuenta.csv",
            mime="text/csv",
        )

    uploaded = st.file_uploader(
        "Selecciona un archivo",
        type=["csv", "xlsx", "xls"],
        help="Formatos aceptados: CSV, Excel (.xlsx, .xls).",
    )

    if uploaded:
        try:
            if uploaded.name.endswith(".csv"):
                raw_df = pd.read_csv(uploaded)
            else:
                raw_df = pd.read_excel(uploaded)
        except Exception as exc:
            st.error(f"No se pudo leer el archivo: {exc}")
            st.stop()

        st.write(f"**{len(raw_df)} filas detectadas.** Vista previa:")
        st.dataframe(raw_df.head(5), use_container_width=True)

        cols = list(raw_df.columns)
        st.divider()
        st.subheader("Mapeo de Columnas")
        st.caption("Indica cuál columna de tu archivo corresponde a cada campo.")

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            col_date_m = st.selectbox("Columna Fecha", cols, key="m_date")
        with col_m2:
            col_desc_m = st.selectbox("Columna Descripción", cols, key="m_desc")
        with col_m3:
            col_amt_m = st.selectbox("Columna Monto", cols, key="m_amt")
        with col_m4:
            col_type_m = st.selectbox("Columna Tipo (Ingreso/Egreso)", cols, key="m_type")

        col_curr_m, _ = st.columns([1, 3])
        with col_curr_m:
            import_currency = st.radio("Moneda de este estado de cuenta", CURRENCIES, horizontal=True, key="m_curr")

        if st.button("🔍 Analizar y Clasificar", use_container_width=True):
            try:
                work = raw_df[[col_date_m, col_desc_m, col_amt_m, col_type_m]].copy()
                work.columns = ["fecha", "descripcion", "monto", "tipo"]
                work["monto"] = pd.to_numeric(work["monto"], errors="coerce").fillna(0)

                cats, subs = [], []
                for desc in work["descripcion"].fillna(""):
                    c, s = classify_description(str(desc))
                    cats.append(c)
                    subs.append(s)
                work["Categoría NIIF"] = cats
                work["Subcategoría"] = subs

                st.session_state["import_df"] = work
                st.session_state["import_currency"] = import_currency
                st.rerun()

            except Exception as exc:
                st.error(f"Error al procesar el archivo: {exc}")

    if "import_df" in st.session_state:
        work = st.session_state["import_df"].copy()
        imp_curr = st.session_state.get("import_currency", "USD")

        st.divider()
        st.subheader("Revisar y Confirmar Clasificaciones")
        st.caption(
            "Revisa las columnas **Categoría NIIF** y **Subcategoría**. "
            "Haz clic en cualquier celda para corregir la clasificación antes de confirmar."
        )

        niif_opts = list(NIIF_CATEGORIES.keys()) + ["Sin Clasificar"]
        sub_opts = [s for subs in NIIF_CATEGORIES.values() for s in subs] + ["Sin Clasificar"]

        edited = st.data_editor(
            work,
            use_container_width=True,
            column_config={
                "Categoría NIIF": st.column_config.SelectboxColumn(
                    "Categoría NIIF",
                    options=niif_opts,
                ),
                "Subcategoría": st.column_config.SelectboxColumn(
                    "Subcategoría",
                    options=sub_opts,
                ),
                "tipo": st.column_config.SelectboxColumn(
                    "Tipo",
                    options=["Ingreso", "Egreso"],
                ),
            },
            key="import_editor",
        )

        unclassified = (edited["Categoría NIIF"] == "Sin Clasificar").sum()
        if unclassified:
            st.warning(
                f"⚠️ {unclassified} fila(s) sin clasificar. "
                "Corrígelas antes de importar o se guardarán como 'Sin Clasificar'."
            )

        if st.button("✅ Confirmar e Importar Todo", type="primary", use_container_width=True):
            rows_to_insert = []
            for _, row in edited.iterrows():
                try:
                    fecha_dt = pd.to_datetime(row["fecha"])
                    fecha_utc = datetime(
                        fecha_dt.year, fecha_dt.month, fecha_dt.day, tzinfo=timezone.utc
                    )
                except Exception:
                    fecha_utc = datetime.now(timezone.utc)

                rows_to_insert.append(
                    {
                        "date": fecha_utc,
                        "amount": float(row["monto"]),
                        "currency": imp_curr,
                        "direction": str(row.get("tipo", "Egreso")),
                        "niif_category": str(row.get("Categoría NIIF", "Sin Clasificar")),
                        "subcategory": str(row.get("Subcategoría", "Sin Clasificar")),
                        "description": str(row.get("descripcion", "")),
                        "source_bank": "",
                    }
                )

            with st.spinner(f"Importando {len(rows_to_insert)} transacciones…"):
                count = add_transactions_batch(org_id, rows_to_insert, user=user)

            del st.session_state["import_df"]
            st.success(f"✅ {count} transacción(es) importada(s) exitosamente.")
            st.rerun()

# ── Recent transactions ───────────────────────────────────────────────────────
st.divider()
st.subheader("📋 Transacciones Recientes")

with st.expander("Ver historial", expanded=False):
    col_tf1, col_tf2 = st.columns(2)
    with col_tf1:
        f_dir = st.selectbox("Dirección", ["Todas", "Ingreso", "Egreso"], key="tx_dir")
    with col_tf2:
        f_niif = st.selectbox(
            "Categoría NIIF",
            ["Todas"] + list(NIIF_CATEGORIES.keys()),
            key="tx_niif",
        )

    recent_txs = list_transactions(
        org_id,
        limit=100,
        direction=None if f_dir == "Todas" else f_dir,
        niif_category=None if f_niif == "Todas" else f_niif,
    )

    if recent_txs:
        st.dataframe(
            [
                {
                    "Fecha": format_date(r.get("date")),
                    "Descripción": r.get("description", "—"),
                    "Monto": format_currency(r.get("amount", 0), r.get("currency", "USD")),
                    "Tipo": r.get("direction", "—"),
                    "NIIF": r.get("niif_category", "—"),
                    "Subcategoría": r.get("subcategory", "—"),
                    "Banco": r.get("source_bank", "—"),
                }
                for r in recent_txs
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Aún no hay transacciones registradas.")
