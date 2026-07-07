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

# ---------------------------------------------------------------------------
# NIIF Chart of Accounts (Plan de Cuentas)
# Preset accounts seeded for every new organization.
# Fields: code, name, account_type, direction (Ingreso/Egreso/N/A)
# ---------------------------------------------------------------------------
NIIF_CHART_OF_ACCOUNTS: list[dict] = [
    # Activos (Assets)
    {"code": "1.1.01", "name": "Caja Chica",              "account_type": "Activo",  "direction": "N/A"},
    {"code": "1.1.02", "name": "Banco Principal",          "account_type": "Activo",  "direction": "N/A"},
    {"code": "1.1.03", "name": "Banco Secundario",         "account_type": "Activo",  "direction": "N/A"},
    {"code": "1.1.04", "name": "Fondos por Depositar",     "account_type": "Activo",  "direction": "N/A"},
    {"code": "1.2.01", "name": "Inventario de Donaciones", "account_type": "Activo",  "direction": "N/A"},
    # Pasivos (Liabilities)
    {"code": "2.1.01", "name": "Cuentas por Pagar",        "account_type": "Pasivo",  "direction": "Egreso"},
    {"code": "2.1.02", "name": "Préstamos por Pagar",      "account_type": "Pasivo",  "direction": "Egreso"},
    # Fondos (Funds / Equity)
    {"code": "3.1.01", "name": "Fondo General",            "account_type": "Fondo",   "direction": "N/A"},
    {"code": "3.1.02", "name": "Fondo de Emergencia",      "account_type": "Fondo",   "direction": "N/A"},
    {"code": "3.1.03", "name": "Fondo de Alimentación",    "account_type": "Fondo",   "direction": "N/A"},
    {"code": "3.1.04", "name": "Fondo de Salud",           "account_type": "Fondo",   "direction": "N/A"},
    # Ingresos (Income)
    {"code": "4.1.01", "name": "Donaciones en Efectivo",   "account_type": "Ingreso", "direction": "Ingreso"},
    {"code": "4.1.02", "name": "Donaciones en Especie",    "account_type": "Ingreso", "direction": "Ingreso"},
    {"code": "4.1.03", "name": "Subvenciones",             "account_type": "Ingreso", "direction": "Ingreso"},
    {"code": "4.1.04", "name": "Otros Ingresos",           "account_type": "Ingreso", "direction": "Ingreso"},
    # Egresos (Expenses)
    {"code": "5.1.01", "name": "Compra de Suministros",    "account_type": "Egreso",  "direction": "Egreso"},
    {"code": "5.1.02", "name": "Logística y Transporte",   "account_type": "Egreso",  "direction": "Egreso"},
    {"code": "5.1.03", "name": "Salarios y Beneficios",    "account_type": "Egreso",  "direction": "Egreso"},
    {"code": "5.1.04", "name": "Servicios Públicos",       "account_type": "Egreso",  "direction": "Egreso"},
    {"code": "5.1.05", "name": "Alquiler",                 "account_type": "Egreso",  "direction": "Egreso"},
    {"code": "5.1.06", "name": "Gastos Administrativos",   "account_type": "Egreso",  "direction": "Egreso"},
    {"code": "5.1.07", "name": "Gastos de Programa",       "account_type": "Egreso",  "direction": "Egreso"},
]

# Lookup map: account code → account name (for display in dropdowns)
ACCOUNT_CODE_TO_NAME: dict[str, str] = {
    a["code"]: f"{a['code']} — {a['name']}" for a in NIIF_CHART_OF_ACCOUNTS
}
