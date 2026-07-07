"""
All Spanish-facing labels, dropdown option lists, and category trees.
Imported by pages and repo modules so labels stay consistent everywhere.
"""

# ---------------------------------------------------------------------------
# Donation category tree
# Keys = main categories, values = list of subcategories
# ---------------------------------------------------------------------------
DONATION_CATEGORIES: dict[str, list[str]] = {
    "Alimentos": [
        "No Perecederos",
        "Perecederos",
        "Formula Infantil",
        "Agua Embotellada",
    ],
    "Medicinas": [
        "Venta Libre",
        "Con Receta",
        "Primeros Auxilios",
        "Suplementos",
    ],
    "Higiene y Limpieza": [
        "Higiene Personal",
        "Limpieza",
        "Sanitario",
    ],
    "Ropa y Calzado": [
        "Ropa Adulto",
        "Ropa Infantil",
        "Calzado",
        "Ropa de Cama",
    ],
    "Materiales Educativos": [
        "Utiles Escolares",
        "Libros",
        "Equipos",
    ],
    "Suministros de Emergencia": [
        "Lonas y Carpas",
        "Linternas",
        "Herramientas",
        "Generadores",
    ],
    "Equipos Medicos": [
        "Sillas de Ruedas",
        "Muletas",
        "Equipos de Diagnostico",
        "Insumos Hospitalarios",
    ],
    "Otros": [
        "Juguetes",
        "Articulos del Hogar",
        "Tecnologia",
        "Sin Clasificar",
    ],
}

# Categories whose items may have an expiration date
CATEGORIES_WITH_EXPIRATION: list[str] = [
    "Alimentos",
    "Medicinas",
    "Higiene y Limpieza",
]

# ---------------------------------------------------------------------------
# Packaging formats
# ---------------------------------------------------------------------------
PACKAGING_FORMATS: list[str] = [
    "Unidad",
    "Paquete",
    "Caja",
    "Saco",
    "Bulto / Granel",
    "Palet / Tarima",
    "Kit",
]

# ---------------------------------------------------------------------------
# NIIF (IFRS) cash-flow classification tree
# ---------------------------------------------------------------------------
NIIF_CATEGORIES: dict[str, list[str]] = {
    "Actividades de Operacion": [
        "Donacion Recibida",
        "Subvencion",
        "Compra de Suministros",
        "Logistica",
        "Salarios",
        "Servicios",
        "Otro",
    ],
    "Actividades de Inversion": [
        "Compra de Equipo",
        "Venta de Activo",
        "Otro",
    ],
    "Actividades de Financiamiento": [
        "Prestamo Recibido",
        "Pago de Prestamo",
        "Otro",
    ],
}

# ---------------------------------------------------------------------------
# Bank-statement keyword map  (keyword -> (niif_category, subcategory))
# Used when auto-classifying imported bank statements.
# ---------------------------------------------------------------------------
BANK_KEYWORD_MAP: dict[str, tuple[str, str]] = {
    "nomina": ("Actividades de Operacion", "Salarios"),
    "salario": ("Actividades de Operacion", "Salarios"),
    "alquiler": ("Actividades de Operacion", "Servicios"),
    "luz": ("Actividades de Operacion", "Servicios"),
    "agua": ("Actividades de Operacion", "Servicios"),
    "internet": ("Actividades de Operacion", "Servicios"),
    "donacion": ("Actividades de Operacion", "Donacion Recibida"),
    "subvencion": ("Actividades de Operacion", "Subvencion"),
    "suministro": ("Actividades de Operacion", "Compra de Suministros"),
    "transporte": ("Actividades de Operacion", "Logistica"),
    "flete": ("Actividades de Operacion", "Logistica"),
    "equipo": ("Actividades de Inversion", "Compra de Equipo"),
    "prestamo": ("Actividades de Financiamiento", "Prestamo Recibido"),
}

# ---------------------------------------------------------------------------
# Inventory exit reasons
# ---------------------------------------------------------------------------
EXIT_REASONS: list[str] = [
    "Ayuda Humanitaria",
    "Emergencia",
    "Distribucion Programada",
    "Otro",
]

# ---------------------------------------------------------------------------
# Cash-flow directions
# ---------------------------------------------------------------------------
FLOW_DIRECTIONS: list[str] = ["Ingreso", "Egreso"]

# ---------------------------------------------------------------------------
# Currency options
# ---------------------------------------------------------------------------
CURRENCIES: list[str] = ["USD", "VES"]

# ---------------------------------------------------------------------------
# Stakeholder types
# ---------------------------------------------------------------------------
STAKEHOLDER_TYPES: list[str] = [
    "Donante",
    "Beneficiario",
    "Proveedor",
]

# ---------------------------------------------------------------------------
# User roles
# ---------------------------------------------------------------------------
USER_ROLES: list[str] = ["Admin", "Usuario"]
