"""
pages/2_Registro_Donaciones.py — Donation Entry (inventory IN).

Three modes (tabs):
  1. Entrada Individual — one item at a time.
  2. Entrada en Lote   — spreadsheet grid for multiple items at once.
  3. Entrada Rápida    — type a free-text description; smart auto-fill.
"""

from datetime import date, datetime, timezone

import pandas as pd
import streamlit as st

from db.donations_repo import add_donation, list_donations
from db.inventory_repo import add_catalog_item, list_catalog_items, upsert_stock
from utils.auth import current_org_id, current_user_email
from utils.classifier import suggest_donation, confidence_icon
from utils.constants import (
    CATEGORIES_WITH_EXPIRATION,
    DONATION_CATEGORIES,
    PACKAGING_FORMATS,
)
from utils.formatters import format_date
from utils.validators import validate_donation_form

org_id = current_org_id()
user = current_user_email() or "system"

st.header("📥 Registro de Donaciones")
st.caption("Registra los artículos que recibe la organización (inventario entrante).")

# ── Load catalog once (used in all tabs and the history table) ────────────────
all_catalog = list_catalog_items(org_id)
catalog_map = {i["item_id"]: i["name"] for i in all_catalog}

tab_single, tab_batch, tab_quick = st.tabs(
    ["📋 Entrada Individual", "📦 Entrada en Lote", "⚡ Entrada Rápida"]
)

# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 1 — SINGLE ENTRY
# ═══════════════════════════════════════════════════════════════════════════════
with tab_single:
    st.subheader("Nueva Donación")

    # ── Category / Subcategory cascading ──────────────────────────────────────
    col_cat, col_sub = st.columns(2)
    with col_cat:
        category = st.selectbox(
            "Categoría *",
            list(DONATION_CATEGORIES.keys()),
            key="s_cat",
            help="Tipo principal del artículo donado.",
        )
    with col_sub:
        subcategory = st.selectbox(
            "Subcategoría *",
            DONATION_CATEGORIES[category],
            key="s_sub",
            help="Subcategoría del artículo.",
        )

    # ── Item selection (catalog or new) ───────────────────────────────────────
    CREATE_NEW = "➕ Crear nuevo artículo"
    cat_items = [
        i for i in all_catalog
        if i["category"] == category and i.get("is_active", True)
    ]
    item_options = [i["name"] for i in cat_items] + [CREATE_NEW]

    selected_item_name = st.selectbox(
        "Artículo *",
        item_options,
        key="s_item",
        help="Elige del catálogo o selecciona '➕ Crear nuevo artículo'.",
    )

    new_item_name = ""
    tracks_exp_new = category in CATEGORIES_WITH_EXPIRATION
    if selected_item_name == CREATE_NEW:
        new_item_name = st.text_input(
            "Nombre del nuevo artículo *",
            placeholder="Ej: Arroz Diana 1 kg",
            key="s_new_name",
        )
        tracks_exp_new = st.checkbox(
            "¿Este artículo tiene fecha de vencimiento?",
            value=category in CATEGORIES_WITH_EXPIRATION,
            key="s_tracks_exp",
        )

    # ── Packaging & quantity ──────────────────────────────────────────────────
    col_emp, col_qty = st.columns(2)
    with col_emp:
        packaging = st.selectbox(
            "Formato de Empaque *",
            PACKAGING_FORMATS,
            key="s_pkg",
            help="¿Cómo viene empacado el artículo?",
        )
    with col_qty:
        quantity = st.number_input(
            "Cantidad *",
            min_value=1,
            step=1,
            value=1,
            key="s_qty",
            help="Número de unidades, cajas, sacos, etc.",
        )

    # ── Expiration date (optional, only for relevant categories) ──────────────
    expiration_date: datetime | None = None
    if category in CATEGORIES_WITH_EXPIRATION:
        show_exp = st.checkbox(
            "Registrar fecha de vencimiento",
            key="s_show_exp",
        )
        if show_exp:
            exp_val = st.date_input(
                "Fecha de Vencimiento",
                min_value=date.today(),
                key="s_exp_date",
            )
            expiration_date = datetime(
                exp_val.year, exp_val.month, exp_val.day, tzinfo=timezone.utc
            )

    # ── Donor info ────────────────────────────────────────────────────────────
    st.divider()
    donor_name = st.text_input(
        "Nombre del Donante *",
        placeholder="Persona u organización que entrega la donación",
        key="s_donor",
    )
    col_dorg, col_notes = st.columns(2)
    with col_dorg:
        donor_org = st.text_input(
            "Organización del Donante",
            placeholder="Opcional",
            key="s_dorg",
        )
    with col_notes:
        notes = st.text_area(
            "Notas",
            placeholder="Observaciones adicionales (opcional)",
            height=80,
            key="s_notes",
        )

    # ── Submit ────────────────────────────────────────────────────────────────
    st.divider()
    if st.button("✅ Registrar Donación", type="primary", use_container_width=True):
        is_new_item = selected_item_name == CREATE_NEW
        actual_name = new_item_name.strip() if is_new_item else selected_item_name

        errors = validate_donation_form(category, actual_name, int(quantity), donor_name)
        if is_new_item and not new_item_name.strip():
            errors.insert(0, 'El campo "Nombre del nuevo artículo" es obligatorio.')

        if errors:
            for err in errors:
                st.error(err)
        else:
            with st.spinner("Guardando donación…"):
                existing_doc = next(
                    (i for i in cat_items if i["name"] == actual_name), None
                )
                if existing_doc:
                    item_id = existing_doc["item_id"]
                else:
                    item_id = add_catalog_item(
                        org_id=org_id,
                        name=actual_name,
                        category=category,
                        subcategory=subcategory,
                        default_packaging=packaging,
                        tracks_expiration=tracks_exp_new,
                        user=user,
                    )

                add_donation(
                    org_id=org_id,
                    item_id=item_id,
                    category=category,
                    subcategory=subcategory,
                    packaging=packaging,
                    quantity=int(quantity),
                    donor_name=donor_name.strip(),
                    donor_org=donor_org.strip(),
                    expiration_date=expiration_date,
                    notes=notes.strip(),
                    user=user,
                )
                upsert_stock(
                    org_id=org_id,
                    item_id=item_id,
                    name=actual_name,
                    category=category,
                    subcategory=subcategory,
                    packaging=packaging,
                    quantity_delta=int(quantity),
                    expiration_date=expiration_date,
                    user=user,
                )

            st.success(
                f"✅ Donación registrada: **{int(quantity)} {packaging}(s)** "
                f"de «{actual_name}» — Donante: {donor_name.strip()}."
            )
            st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 2 — BATCH ENTRY
# ═══════════════════════════════════════════════════════════════════════════════
with tab_batch:
    st.subheader("Entrada en Lote")
    st.caption(
        "Usa esta tabla cuando llega un camión con varios artículos distintos. "
        "Completa cada fila y presiona **Registrar Todo**."
    )

    empty_batch = pd.DataFrame(
        {
            "Artículo": pd.Series([], dtype="str"),
            "Categoría": pd.Series([], dtype="str"),
            "Subcategoría": pd.Series([], dtype="str"),
            "Empaque": pd.Series([], dtype="str"),
            "Cantidad": pd.Series([], dtype="int"),
            "Vencimiento (YYYY-MM-DD)": pd.Series([], dtype="str"),
            "Donante": pd.Series([], dtype="str"),
        }
    )

    batch_df = st.data_editor(
        empty_batch,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Categoría": st.column_config.SelectboxColumn(
                "Categoría *",
                options=list(DONATION_CATEGORIES.keys()),
                required=True,
            ),
            "Empaque": st.column_config.SelectboxColumn(
                "Empaque *",
                options=PACKAGING_FORMATS,
                required=True,
            ),
            "Cantidad": st.column_config.NumberColumn(
                "Cantidad *",
                min_value=1,
                step=1,
                required=True,
            ),
            "Vencimiento (YYYY-MM-DD)": st.column_config.TextColumn(
                "Vencimiento",
                help="Formato: AAAA-MM-DD  (ej. 2025-03-31). Déjalo vacío si no aplica.",
            ),
        },
        key="batch_editor",
    )

    if st.button("✅ Registrar Todo", type="primary", use_container_width=True, key="btn_batch"):
        rows = batch_df.dropna(subset=["Artículo", "Categoría", "Donante"])
        rows = rows[rows["Artículo"].str.strip() != ""]

        if rows.empty:
            st.warning(
                "La tabla está vacía o faltan datos obligatorios "
                "(Artículo, Categoría, Donante)."
            )
        else:
            saved, errors_found = 0, []
            fresh_catalog = list_catalog_items(org_id)

            with st.spinner(f"Guardando {len(rows)} registros…"):
                for _, row in rows.iterrows():
                    try:
                        cat = str(row["Categoría"])
                        subcat = str(row.get("Subcategoría") or "").strip()
                        if not subcat:
                            subcat = DONATION_CATEGORIES.get(cat, ["Sin Clasificar"])[0]
                        item_name = str(row["Artículo"]).strip()
                        pkg = str(row.get("Empaque") or "Unidad")
                        qty = int(row.get("Cantidad") or 1)
                        donor = str(row["Donante"]).strip()
                        venc_str = str(row.get("Vencimiento (YYYY-MM-DD)") or "").strip()

                        exp_date: datetime | None = None
                        if venc_str and venc_str.lower() not in ("nan", "none", ""):
                            try:
                                d = date.fromisoformat(venc_str)
                                exp_date = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
                            except ValueError:
                                pass

                        existing = next(
                            (i for i in fresh_catalog
                             if i["name"] == item_name and i["category"] == cat),
                            None,
                        )
                        if existing:
                            item_id = existing["item_id"]
                        else:
                            item_id = add_catalog_item(
                                org_id=org_id,
                                name=item_name,
                                category=cat,
                                subcategory=subcat,
                                default_packaging=pkg,
                                tracks_expiration=cat in CATEGORIES_WITH_EXPIRATION,
                                user=user,
                            )
                            fresh_catalog.append({
                                "item_id": item_id, "name": item_name,
                                "category": cat, "is_active": True,
                            })

                        add_donation(
                            org_id=org_id,
                            item_id=item_id,
                            category=cat,
                            subcategory=subcat,
                            packaging=pkg,
                            quantity=qty,
                            donor_name=donor,
                            expiration_date=exp_date,
                            user=user,
                        )
                        upsert_stock(
                            org_id=org_id,
                            item_id=item_id,
                            name=item_name,
                            category=cat,
                            subcategory=subcat,
                            packaging=pkg,
                            quantity_delta=qty,
                            expiration_date=exp_date,
                            user=user,
                        )
                        saved += 1

                    except Exception as exc:
                        errors_found.append(f"Fila «{row.get('Artículo', '?')}»: {exc}")

            if saved:
                st.success(f"✅ {saved} donación(es) registrada(s) exitosamente.")
            for e in errors_found:
                st.error(e)

# ═══════════════════════════════════════════════════════════════════════════════
#  TAB 3 — QUICK ENTRY (auto-fill from free text)
# ═══════════════════════════════════════════════════════════════════════════════
with tab_quick:
    st.subheader("Entrada Rápida")
    st.caption(
        "Escribe una descripción en lenguaje natural y el sistema intentará "
        "rellenar los campos automáticamente. Puedes corregir cualquier campo "
        "antes de guardar."
    )
    st.info(
        "**Ejemplos:**\n"
        "- «20 cajas de arroz del Banco de Alimentos»\n"
        "- «50 sacos de harina donados por Cruz Roja»\n"
        "- «12 frazadas de ACNUR»",
        icon="💡",
    )

    quick_text = st.text_area(
        "Describe la donación *",
        placeholder="Ej: 30 paquetes de acetaminofen de Farmavida",
        height=90,
        key="q_text",
    )

    if st.button("🔍 Analizar Descripción", use_container_width=True, key="q_analyze"):
        if quick_text.strip():
            with st.spinner("Analizando…"):
                suggestion = suggest_donation(quick_text.strip(), all_catalog)
            st.session_state["q_suggestion"] = suggestion
        else:
            st.warning("Escribe una descripción primero.")

    if "q_suggestion" in st.session_state:
        sug = st.session_state["q_suggestion"]
        conf = sug.get("confidence", {})

        st.divider()
        st.markdown("**Resultados del análisis — revisa y ajusta si es necesario:**")

        col_item, col_cat = st.columns(2)
        with col_item:
            # Pre-select matched item or allow free entry
            cat_items_q = [
                i for i in all_catalog if i.get("is_active", True)
            ]
            CREATE_NEW_Q = "➕ Crear nuevo artículo"
            item_opts_q = [i["name"] for i in cat_items_q] + [CREATE_NEW_Q]
            default_item_idx = 0
            if sug["item_id"]:
                matched_names = [i["name"] for i in cat_items_q]
                if sug["item_name"] in matched_names:
                    default_item_idx = matched_names.index(sug["item_name"])
            q_item_sel = st.selectbox(
                f"Artículo  {confidence_icon(conf.get('item', 0))}",
                item_opts_q,
                index=default_item_idx,
                key="q_item_sel",
            )
        with col_cat:
            q_cat = st.selectbox(
                f"Categoría  {confidence_icon(conf.get('category', 0))}",
                list(DONATION_CATEGORIES.keys()),
                index=list(DONATION_CATEGORIES.keys()).index(sug["category"])
                if sug["category"] in DONATION_CATEGORIES else 0,
                key="q_cat",
            )

        col_sub, col_pkg = st.columns(2)
        with col_sub:
            q_sub = st.selectbox(
                "Subcategoría",
                DONATION_CATEGORIES[q_cat],
                key="q_sub",
            )
        with col_pkg:
            pkg_idx = PACKAGING_FORMATS.index(sug["packaging"]) if sug["packaging"] in PACKAGING_FORMATS else 0
            q_pkg = st.selectbox(
                f"Empaque  {confidence_icon(conf.get('packaging', 0))}",
                PACKAGING_FORMATS,
                index=pkg_idx,
                key="q_pkg",
            )

        col_qty, col_donor = st.columns(2)
        with col_qty:
            q_qty = st.number_input(
                f"Cantidad  {confidence_icon(conf.get('quantity', 0))}",
                min_value=1,
                step=1,
                value=max(1, sug["quantity"]),
                key="q_qty",
            )
        with col_donor:
            q_donor = st.text_input(
                f"Donante  {confidence_icon(conf.get('donor', 0))}",
                value=sug["donor_name"],
                key="q_donor",
                placeholder="Nombre del donante",
            )

        q_new_name = ""
        if q_item_sel == CREATE_NEW_Q:
            q_new_name = st.text_input(
                "Nombre del nuevo artículo *",
                value=sug["item_name"] if not sug["item_id"] else "",
                key="q_new_name",
            )

        # Expiration date (optional)
        q_exp_date: datetime | None = None
        if q_cat in CATEGORIES_WITH_EXPIRATION:
            q_show_exp = st.checkbox("Registrar fecha de vencimiento", key="q_show_exp")
            if q_show_exp:
                q_exp_val = st.date_input("Fecha de Vencimiento", min_value=date.today(), key="q_exp_date")
                q_exp_date = datetime(q_exp_val.year, q_exp_val.month, q_exp_val.day, tzinfo=timezone.utc)

        q_notes = st.text_area("Notas (opcional)", height=60, key="q_notes")

        st.divider()
        if st.button("✅ Registrar Donación", type="primary", use_container_width=True, key="q_submit"):
            is_new = q_item_sel == CREATE_NEW_Q
            actual_name = q_new_name.strip() if is_new else q_item_sel
            errors = validate_donation_form(q_cat, actual_name, int(q_qty), q_donor)
            if is_new and not q_new_name.strip():
                errors.insert(0, "Escribe el nombre del nuevo artículo.")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                with st.spinner("Guardando donación…"):
                    existing = next((i for i in cat_items_q if i["name"] == actual_name), None)
                    if existing:
                        q_item_id = existing["item_id"]
                    else:
                        q_item_id = add_catalog_item(
                            org_id=org_id,
                            name=actual_name,
                            category=q_cat,
                            subcategory=q_sub,
                            default_packaging=q_pkg,
                            tracks_expiration=q_cat in CATEGORIES_WITH_EXPIRATION,
                            user=user,
                        )

                    add_donation(
                        org_id=org_id,
                        item_id=q_item_id,
                        category=q_cat,
                        subcategory=q_sub,
                        packaging=q_pkg,
                        quantity=int(q_qty),
                        donor_name=q_donor.strip(),
                        donor_org="",
                        expiration_date=q_exp_date,
                        notes=q_notes.strip(),
                        user=user,
                    )
                    upsert_stock(
                        org_id=org_id,
                        item_id=q_item_id,
                        name=actual_name,
                        category=q_cat,
                        subcategory=q_sub,
                        packaging=q_pkg,
                        quantity_delta=int(q_qty),
                        expiration_date=q_exp_date,
                        user=user,
                    )

                del st.session_state["q_suggestion"]
                st.success(
                    f"✅ Donación registrada: **{int(q_qty)} {q_pkg}(s)** de «{actual_name}» "
                    f"— Donante: {q_donor.strip() or '—'}."
                )
                st.rerun()


# ── Recent donations history ───────────────────────────────────────────────────
st.divider()
st.subheader("📋 Historial de Donaciones")

with st.expander("Ver historial", expanded=False):
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        f_cat = st.selectbox(
            "Categoría",
            ["Todas"] + list(DONATION_CATEGORIES.keys()),
            key="h_cat",
        )
    with col_f2:
        f_donor = st.text_input("Donante (buscar)", key="h_donor")

    recent = list_donations(
        org_id,
        limit=50,
        category=None if f_cat == "Todas" else f_cat,
        donor=f_donor.strip() or None,
    )

    if recent:
        st.dataframe(
            [
                {
                    "Fecha": format_date(r.get("date")),
                    "Artículo": catalog_map.get(r.get("item_id", ""), r.get("item_id", "—")),
                    "Categoría": r.get("category", "—"),
                    "Empaque": r.get("packaging", "—"),
                    "Cantidad": r.get("quantity", 0),
                    "Donante": r.get("donor_name", "—"),
                    "Vence": format_date(r.get("expiration_date")),
                }
                for r in recent
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Aún no hay donaciones registradas para los filtros seleccionados.")
