"""
pages/6_Catalogo_Articulos.py — Item Catalog management.

The catalog is the master list of known items. Donation and exit forms
pull items from here, preventing typos and duplicate entries.

Features:
  • Searchable, filterable table of all active catalog items.
  • "Agregar Artículo" form to add a new item.
  • Deactivate button to hide items without deleting historical records.
"""

import streamlit as st

from db.inventory_repo import (
    add_catalog_item,
    deactivate_catalog_item,
    list_catalog_items,
)
from utils.auth import current_org_id, current_user_email
from utils.constants import (
    CATEGORIES_WITH_EXPIRATION,
    DONATION_CATEGORIES,
    PACKAGING_FORMATS,
)

org_id = current_org_id()
user = current_user_email() or "system"

st.header("📋 Catálogo de Artículos")
st.caption(
    "Lista maestra de todos los artículos que maneja la organización. "
    "Los formularios de donación y salida usan esta lista para evitar duplicados."
)

# ── Load catalog ──────────────────────────────────────────────────────────────
show_inactive = st.checkbox("Mostrar artículos desactivados", value=False)
all_items = list_catalog_items(org_id, active_only=not show_inactive)

# ── Search / filter ───────────────────────────────────────────────────────────
col_s, col_f = st.columns([2, 1])
with col_s:
    search = st.text_input("🔍 Buscar por nombre", placeholder="Ej: arroz")
with col_f:
    f_cat = st.selectbox(
        "Filtrar por categoría",
        ["Todas"] + list(DONATION_CATEGORIES.keys()),
    )

filtered = [
    i for i in all_items
    if (f_cat == "Todas" or i.get("category") == f_cat)
    and (not search or search.lower() in i.get("name", "").lower())
]

st.divider()

# ── Catalog table ─────────────────────────────────────────────────────────────
if filtered:
    st.write(f"**{len(filtered)}** artículo(s) encontrado(s).")
    st.dataframe(
        [
            {
                "Nombre": i.get("name", "—"),
                "Categoría": i.get("category", "—"),
                "Subcategoría": i.get("subcategory", "—"),
                "Empaque predeterminado": i.get("default_packaging", "—"),
                "Registra vencimiento": "Sí" if i.get("tracks_expiration") else "No",
                "Estado": "Activo" if i.get("is_active", True) else "Inactivo",
            }
            for i in filtered
        ],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info(
        "No se encontraron artículos con los filtros seleccionados. "
        "Agrega el primero usando el formulario de abajo."
    )

# ── Add new item ──────────────────────────────────────────────────────────────
st.divider()
with st.expander("➕ Agregar nuevo artículo al catálogo", expanded=len(all_items) == 0):
    st.subheader("Nuevo Artículo")

    item_name = st.text_input(
        "Nombre del artículo *",
        placeholder="Ej: Arroz Diana 1 kg",
        help="Usa un nombre descriptivo y consistente para evitar duplicados.",
    )

    col_nc, col_ns = st.columns(2)
    with col_nc:
        new_cat = st.selectbox(
            "Categoría *",
            list(DONATION_CATEGORIES.keys()),
            key="nc_cat",
        )
    with col_ns:
        new_sub = st.selectbox(
            "Subcategoría *",
            DONATION_CATEGORIES[new_cat],
            key="nc_sub",
        )

    col_np, col_ne = st.columns(2)
    with col_np:
        new_pkg = st.selectbox(
            "Empaque predeterminado *",
            PACKAGING_FORMATS,
            key="nc_pkg",
            help="El formato de empaque más común para este artículo.",
        )
    with col_ne:
        tracks_exp = st.checkbox(
            "¿Tiene fecha de vencimiento?",
            value=new_cat in CATEGORIES_WITH_EXPIRATION,
            key="nc_exp",
            help="Marca esto si el artículo puede vencerse (medicinas, alimentos, etc.).",
        )

    if st.button("✅ Agregar al Catálogo", type="primary", use_container_width=True):
        if not item_name.strip():
            st.error('El campo "Nombre del artículo" es obligatorio.')
        else:
            duplicate = next(
                (i for i in all_items if i["name"].lower() == item_name.strip().lower()),
                None,
            )
            if duplicate:
                st.warning(
                    f"Ya existe un artículo con el nombre «{duplicate['name']}» "
                    f"en la categoría «{duplicate['category']}»."
                )
            else:
                with st.spinner("Guardando…"):
                    add_catalog_item(
                        org_id=org_id,
                        name=item_name.strip(),
                        category=new_cat,
                        subcategory=new_sub,
                        default_packaging=new_pkg,
                        tracks_expiration=tracks_exp,
                        user=user,
                    )
                st.success(f"✅ «{item_name.strip()}» agregado al catálogo.")
                st.rerun()

# ── Deactivate item ───────────────────────────────────────────────────────────
active_items = [i for i in all_items if i.get("is_active", True)]
if active_items:
    st.divider()
    with st.expander("🚫 Desactivar un artículo"):
        st.caption(
            "Desactivar un artículo lo oculta de los formularios de entrada y salida. "
            "Los registros históricos NO se eliminan."
        )
        deact_options = {i["name"]: i for i in active_items}
        to_deactivate = st.selectbox(
            "Artículo a desactivar",
            list(deact_options.keys()),
        )
        if st.button("🚫 Desactivar", type="secondary"):
            doc = deact_options[to_deactivate]
            with st.spinner("Desactivando…"):
                deactivate_catalog_item(org_id, doc["item_id"], user=user)
            st.success(f"«{to_deactivate}» ha sido desactivado.")
            st.rerun()
