"""
utils/classifier.py — Intelligent auto-classifier for donations and cash flow.

Uses regex for quantity/packaging extraction and RapidFuzz for fuzzy item
matching against the catalog. No external AI API is required.

Key functions:
  suggest_donation(text, org_id)  →  dict of pre-filled donation fields
  suggest_financial(text)         →  dict of NIIF category + subcategory
  parse_quantity_and_packaging(t) →  (quantity, packaging)

How it works:
  1. A user types something like "20 cajas de arroz del Banco de Alimentos"
  2. parse_quantity_and_packaging extracts 20 and "Caja"
  3. The item "arroz" is fuzzy-matched against the catalog → best match returned
  4. Category/subcategory come from the matched catalog item
  5. Donor is heuristically extracted from "del ..." patterns
  6. The whole suggestion dict is returned with a confidence score per field
"""

import re
from typing import Any

from rapidfuzz import fuzz, process

from utils.constants import (
    BANK_KEYWORD_MAP,
    CATEGORIES_WITH_EXPIRATION,
    DONATION_CATEGORIES,
    NIIF_CATEGORIES,
    PACKAGING_FORMATS,
)

# ── Packaging keyword → canonical format ──────────────────────────────────────

_PACKAGING_KEYWORDS: dict[str, str] = {
    "caja":   "Caja",
    "cajas":  "Caja",
    "paquete":"Paquete",
    "paquetes":"Paquete",
    "saco":   "Saco",
    "sacos":  "Saco",
    "bolsa":  "Paquete",
    "bolsas": "Paquete",
    "unidad": "Unidad",
    "unidades":"Unidad",
    "kit":    "Kit",
    "kits":   "Kit",
    "palet":  "Palet / Tarima",
    "tarima": "Palet / Tarima",
    "bulto":  "Bulto / Granel",
    "granel": "Bulto / Granel",
}

# ── Donor extraction patterns ──────────────────────────────────────────────────
# Tries to pull a donor name from patterns like "de X", "del X", "por X",
# "donado por X", "aportado por X"
_DONOR_PATTERNS = [
    re.compile(r"donado\s+por\s+(.+?)(?:\s*[,.]|$)", re.IGNORECASE),
    re.compile(r"aportado\s+por\s+(.+?)(?:\s*[,.]|$)", re.IGNORECASE),
    re.compile(r"enviado\s+por\s+(.+?)(?:\s*[,.]|$)", re.IGNORECASE),
    re.compile(r"\bpor\s+(.+?)(?:\s*[,.]|$)", re.IGNORECASE),
    re.compile(r"\bdel?\s+(?!inventario|almacén|bodega)(.+?)(?:\s*[,.]|$)", re.IGNORECASE),
    re.compile(r"\bde\s+parte\s+de\s+(.+?)(?:\s*[,.]|$)", re.IGNORECASE),
]

# ── Category keyword hints ─────────────────────────────────────────────────────
# Used when the catalog has no match — guess category from keywords in the text
_CATEGORY_HINTS: dict[str, list[str]] = {
    "Alimentos": [
        "arroz", "pasta", "harina", "aceite", "leche", "avena", "caraotas",
        "lentejas", "azucar", "sal", "atun", "sardina", "alimento", "comida",
        "cereal", "formula", "bebé", "agua", "jugo",
    ],
    "Medicinas": [
        "acetaminofen", "ibuprofeno", "amoxicilina", "antibiotico", "medicina",
        "medicamento", "pastilla", "tableta", "jarabe", "suero", "vitamina",
        "suplemento", "analgesico", "antiinflamatorio",
    ],
    "Higiene y Limpieza": [
        "jabon", "shampoo", "champú", "desodorante", "pasta dental", "cepillo",
        "pañal", "toalla", "papel higienico", "desinfectante", "cloro",
        "limpiador", "gel", "mascarilla",
    ],
    "Ropa y Calzado": [
        "ropa", "camisa", "pantalon", "zapato", "zapatilla", "vestido",
        "chaqueta", "calzado", "frazada", "cobija", "sabana", "manta",
    ],
    "Materiales Educativos": [
        "cuaderno", "lapiz", "boligrafo", "libro", "mochila", "útil escolar",
        "marcador", "regla", "goma", "cartuchera",
    ],
    "Suministros de Emergencia": [
        "linterna", "pila", "batería", "techo", "lona", "carpa", "herramienta",
        "generador", "vela",
    ],
    "Equipos Medicos": [
        "silla de ruedas", "muleta", "tensiómetro", "termómetro", "insumo",
        "hospital", "equipo medico",
    ],
}


# ── Public API ─────────────────────────────────────────────────────────────────

def parse_quantity_and_packaging(text: str) -> tuple[int, str]:
    """
    Extract quantity and packaging format from a free-text string.

    Returns (quantity, packaging) where defaults are (1, "Unidad") if nothing
    was found.

    Examples:
      "20 cajas de arroz"       → (20, "Caja")
      "50 sacos de harina"      → (50, "Saco")
      "arroz 5 paquetes diana"  → (5, "Paquete")
      "arroz"                   → (1, "Unidad")
    """
    text_lower = text.lower()

    # Find first integer in the string
    qty_match = re.search(r"\b(\d+)\b", text_lower)
    quantity = int(qty_match.group(1)) if qty_match else 1

    # Find packaging keyword
    packaging = "Unidad"
    for kw, canonical in _PACKAGING_KEYWORDS.items():
        if re.search(r"\b" + kw + r"\b", text_lower):
            packaging = canonical
            break

    return quantity, packaging


def _extract_donor(text: str) -> str:
    """Attempt to extract a donor name from the text. Returns '' if not found."""
    for pat in _DONOR_PATTERNS:
        m = pat.search(text)
        if m:
            candidate = m.group(1).strip().rstrip(".,;:")
            # Skip if the candidate is too short or looks like a unit/packaging word
            lower = candidate.lower()
            if len(lower) < 3:
                continue
            if lower in _PACKAGING_KEYWORDS:
                continue
            return candidate.title()
    return ""


def _guess_category_from_text(text: str) -> tuple[str, str]:
    """
    Guess the donation category from keyword hints in the text.
    Returns (category, subcategory) or ("Otros", "Sin Clasificar") if no match.
    """
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for cat, keywords in _CATEGORY_HINTS.items():
        for kw in keywords:
            if kw in text_lower:
                scores[cat] = scores.get(cat, 0) + 1

    if scores:
        best_cat = max(scores, key=lambda c: scores[c])
        default_sub = DONATION_CATEGORIES.get(best_cat, ["Sin Clasificar"])[0]
        return best_cat, default_sub

    return "Otros", "Sin Clasificar"


def suggest_donation(text: str, catalog_items: list[dict]) -> dict[str, Any]:
    """
    Suggest donation form fields from a natural-language description.

    Parameters:
      text          — free-text entered by the user
      catalog_items — list of dicts from list_catalog_items(org_id)
                      each must have: item_id, name, category, subcategory

    Returns a dict:
      {
        "quantity":      int,
        "packaging":     str,
        "item_name":     str,       # best fuzzy match or raw extracted name
        "item_id":       str|None,  # catalog item_id if matched, else None
        "category":      str,
        "subcategory":   str,
        "donor_name":    str,
        "needs_expiration": bool,
        "confidence":    dict       # per-field confidence 0–100
      }
    """
    quantity, packaging = parse_quantity_and_packaging(text)

    # Strip numbers and packaging words from text to get a cleaner item name
    clean = re.sub(r"\b\d+\b", "", text)
    for kw in _PACKAGING_KEYWORDS:
        clean = re.sub(r"\b" + kw + r"\b", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s+", " ", clean).strip()

    # Fuzzy-match against catalog
    item_id: str | None = None
    item_name = clean
    category = "Otros"
    subcategory = "Sin Clasificar"
    match_score = 0

    if catalog_items:
        names = [i["name"] for i in catalog_items]
        result = process.extractOne(clean, names, scorer=fuzz.WRatio)
        if result and result[1] >= 55:
            match_score = result[1]
            matched_name = result[0]
            matched_item = next(i for i in catalog_items if i["name"] == matched_name)
            item_id   = matched_item["item_id"]
            item_name = matched_item["name"]
            category  = matched_item.get("category", "Otros")
            subcategory = matched_item.get("subcategory", "Sin Clasificar")

    # Fall back to keyword hints if catalog didn't match well
    if match_score < 55:
        category, subcategory = _guess_category_from_text(text)

    donor_name = _extract_donor(text)
    needs_expiration = category in CATEGORIES_WITH_EXPIRATION

    return {
        "quantity": quantity,
        "packaging": packaging,
        "item_name": item_name,
        "item_id": item_id,
        "category": category,
        "subcategory": subcategory,
        "donor_name": donor_name,
        "needs_expiration": needs_expiration,
        "confidence": {
            "item":     match_score,
            "category": 90 if match_score >= 55 else 50,
            "quantity": 90 if re.search(r"\b\d+\b", text) else 30,
            "packaging": 90 if any(kw in text.lower() for kw in _PACKAGING_KEYWORDS) else 30,
            "donor":    70 if donor_name else 0,
        },
    }


def suggest_financial(text: str) -> dict[str, Any]:
    """
    Suggest NIIF category and subcategory from a cash flow description.

    Returns:
      {
        "niif_category": str,
        "subcategory":   str,
        "direction":     str,   # "Ingreso" or "Egreso" (best guess)
        "confidence":    int    # 0–100
      }
    """
    text_lower = text.lower()

    # Check keyword map first (exact / partial match)
    best_kw: str | None = None
    best_cat: str | None = None
    best_sub: str | None = None

    for kw, (cat, sub) in BANK_KEYWORD_MAP.items():
        if kw in text_lower:
            if best_kw is None or len(kw) > len(best_kw):
                best_kw, best_cat, best_sub = kw, cat, sub

    if best_cat and best_sub:
        # Guess direction from NIIF subcategory name
        income_subs = {"Donacion Recibida", "Subvencion", "Prestamo Recibido", "Venta de Activo"}
        direction = "Ingreso" if best_sub in income_subs else "Egreso"
        return {
            "niif_category": best_cat,
            "subcategory": best_sub,
            "direction": direction,
            "confidence": 85,
        }

    # Fuzzy-match the description against all subcategory names
    all_subs = [(sub, cat) for cat, subs in NIIF_CATEGORIES.items() for sub in subs]
    sub_names = [s[0] for s in all_subs]
    result = process.extractOne(text, sub_names, scorer=fuzz.WRatio)
    if result and result[1] >= 60:
        matched_sub = result[0]
        matched_cat = next(c for s, c in all_subs if s == matched_sub)
        income_subs = {"Donacion Recibida", "Subvencion", "Prestamo Recibido", "Venta de Activo"}
        direction = "Ingreso" if matched_sub in income_subs else "Egreso"
        return {
            "niif_category": matched_cat,
            "subcategory": matched_sub,
            "direction": direction,
            "confidence": result[1],
        }

    return {
        "niif_category": "Actividades de Operacion",
        "subcategory": "Otro",
        "direction": "Egreso",
        "confidence": 20,
    }


def confidence_icon(score: int) -> str:
    """Return a visual indicator for a confidence score 0–100."""
    if score >= 80:
        return "🟢"
    if score >= 55:
        return "🟡"
    return "🔴"
