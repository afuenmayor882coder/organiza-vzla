"""
pages/3_Salida_Inventario.py — Inventory Exit (inventory OUT).

Records when items leave the warehouse (distributions to beneficiaries).
Validates that the exit quantity does not exceed current stock.
"""

import streamlit as st

from db.exits_repo import add_exit, list_exits
from db.inventory_repo import get_stock, upsert_stock
from utils.auth import current_org_id, current_user_email
from utils.constants import EXIT_REASONS
from utils.formatters import format_date
from utils.validators import validate_exit_form

org_id = current_org_id()
user = current_user_email() or "system"

st.header("📤 Salida de Inventario")
st.caption("Registra los artículos que salen del inventario hacia los beneficiarios.")

# ── Load items that have stock available ──────────────────────────────────────
all_stock = get_stock(org_id)
available = [i for i in all_stock if i.get("current_stock", 0) > 0]

if not available:
    st.warning(
        "No hay artículos con stock disponible. "
        "Registra primero algunas donaciones en la página de **Donaciones**."
    )
    st.stop()

# Build label → doc map for the dropdown
item_labels = {
    f"{i['name']}  —  Stock disponible: {i['current_stock']} {i.get('packaging', '')}".strip(): i
    for i in available
}

# ── Exit form ─────────────────────────────────────────────────────────────────
st.subheader("Nueva Salida")

selected_label = st.selectbox(
    "Artículo *",
    list(item_labels.keys()),
    help="Selecciona el artículo que se va a distribuir. El stock disponible se muestra junto al nombre.",
)
selected_doc = item_labels[selected_label]
current_stock = selected_doc.get("current_stock", 0)

col_qty, col_reason = st.columns(2)
with col_qty:
    quantity = st.number_input(
        "Cantidad a Entregar *",
        min_value=1,
        max_value=int(current_stock),
        step=1,
        value=1,
        help=f"Máximo disponible: {current_stock} unidad(es).",
    )
with col_reason:
    reason = st.selectbox(
        "Motivo *",
        EXIT_REASONS,
        help="¿Por qué sale este artículo del inventario?",
    )

st.divider()
recipient_name = st.text_input(
    "Nombre del Receptor *",
    placeholder="Persona que recibe la donación",
)
col_rorg, col_notes = st.columns(2)
with col_rorg:
    recipient_org = st.text_input(
        "Organización Receptora",
        placeholder="Opcional",
    )
with col_notes:
    notes = st.text_area(
        "Notas",
        placeholder="Observaciones adicionales (opcional)",
        height=80,
    )

st.divider()
if st.button("✅ Registrar Salida", type="primary", use_container_width=True):
    errors = validate_exit_form(
        item_id=selected_doc["item_id"],
        quantity=int(quantity),
        available_stock=current_stock,
        recipient_name=recipient_name,
    )
    if errors:
        for err in errors:
            st.error(err)
    else:
        with st.spinner("Guardando salida…"):
            add_exit(
                org_id=org_id,
                item_id=selected_doc["item_id"],
                category=selected_doc.get("category", ""),
                subcategory=selected_doc.get("subcategory", ""),
                packaging=selected_doc.get("packaging", ""),
                quantity=int(quantity),
                recipient_name=recipient_name.strip(),
                recipient_org=recipient_org.strip(),
                reason=reason,
                notes=notes.strip(),
                user=user,
            )
            upsert_stock(
                org_id=org_id,
                item_id=selected_doc["item_id"],
                name=selected_doc["name"],
                category=selected_doc.get("category", ""),
                subcategory=selected_doc.get("subcategory", ""),
                packaging=selected_doc.get("packaging", ""),
                quantity_delta=-int(quantity),
                user=user,
            )

        st.success(
            f"✅ Salida registrada: **{int(quantity)}** unidad(es) de "
            f"«{selected_doc['name']}» → {recipient_name.strip()}."
        )
        st.rerun()

# ── Recent exits history ───────────────────────────────────────────────────────
st.divider()
st.subheader("📋 Historial de Salidas")

with st.expander("Ver historial", expanded=False):
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        from utils.constants import DONATION_CATEGORIES
        f_cat = st.selectbox(
            "Categoría",
            ["Todas"] + list(DONATION_CATEGORIES.keys()),
            key="exits_f_cat",
        )
    with col_f2:
        f_recipient = st.text_input("Receptor (buscar)", key="exits_f_rec")

    recent_exits = list_exits(
        org_id,
        limit=50,
        category=None if f_cat == "Todas" else f_cat,
        recipient=f_recipient.strip() or None,
    )

    if recent_exits:
        # Build a name lookup from stock snapshot
        name_map = {i["item_id"]: i["name"] for i in all_stock}
        st.dataframe(
            [
                {
                    "Fecha": format_date(r.get("date")),
                    "Artículo": name_map.get(r.get("item_id", ""), "—"),
                    "Categoría": r.get("category", "—"),
                    "Cantidad": r.get("quantity", 0),
                    "Receptor": r.get("recipient_name", "—"),
                    "Organización": r.get("recipient_org", "—"),
                    "Motivo": r.get("reason", "—"),
                }
                for r in recent_exits
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Aún no hay salidas registradas para los filtros seleccionados.")
