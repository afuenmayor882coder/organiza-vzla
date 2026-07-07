"""
setup_test_data.py — Seed and reset the isolated test database.

This script ONLY works against databases whose name ends in "_test".
It will refuse to run against production to prevent accidental data loss.

────────────────────────────────────────────────────────
 Usage (from the project root)
────────────────────────────────────────────────────────
  Seed (add demo data without wiping first):
      python setup_test_data.py --seed

  Reset (wipe everything, then re-seed from scratch):
      python setup_test_data.py --reset

────────────────────────────────────────────────────────
 What it creates
────────────────────────────────────────────────────────
  Organizations:
    • La Posada de Jesús   (org 1)
    • Hogar Bambi          (org 2)

  Users:
    • posada@demo.com  / Demo1234!  (Admin, org 1)
    • posada2@demo.com / Demo1234!  (Usuario, org 1)
    • bambi@demo.com   / Demo1234!  (Admin, org 2)
    • bambi2@demo.com  / Demo1234!  (Usuario, org 2)

  Sample data per org:
    • 5 catalog items
    • 8 donation entries (inventory IN)
    • 5 inventory exits (inventory OUT)
    • 6 financial ledger transactions
"""

import argparse
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

try:
    import tomllib  # type: ignore  # Python 3.11+

    def _load_toml(path: str) -> dict:
        with open(path, "rb") as f:
            return tomllib.load(f)

except ImportError:
    try:
        import toml  # type: ignore

        def _load_toml(path: str) -> dict:
            with open(path, encoding="utf-8") as f:
                return toml.load(f)

    except ImportError:
        print("❌ Necesitas Python 3.11+ o la librería 'toml'.")
        sys.exit(1)

import bcrypt
from pymongo import MongoClient

SECRETS_PATH = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")

# Import constants so this script doesn't need Streamlit running
try:
    from utils.constants import NIIF_CHART_OF_ACCOUNTS
except ImportError:
    NIIF_CHART_OF_ACCOUNTS = []

# ── Safety guard ───────────────────────────────────────────────────────────────

def _require_test_db(db_name: str) -> None:
    if not db_name.endswith("_test"):
        print(f"❌ SEGURIDAD: Este script solo puede ejecutarse contra bases de datos")
        print(f"   cuyo nombre termine en '_test'. La base configurada es «{db_name}».")
        print()
        print("   Para usarlo en modo de prueba, asegúrate de que secrets.toml tenga:")
        print("   [app]")
        print('   mode = "test"')
        sys.exit(1)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _days_ago(n: int) -> datetime:
    return _now() - timedelta(days=n)


def _days_from_now(n: int) -> datetime:
    return _now() + timedelta(days=n)


# ── Seed functions ────────────────────────────────────────────────────────────

def seed_accounts(db, org_id: str) -> int:
    """Seed the default NIIF chart of accounts for a test org (idempotent)."""
    created = 0
    for acct in NIIF_CHART_OF_ACCOUNTS:
        if not db["chart_of_accounts"].find_one({"org_id": org_id, "account_code": acct["code"]}):
            db["chart_of_accounts"].insert_one({
                "account_id":   str(uuid.uuid4()),
                "org_id":       org_id,
                "account_code": acct["code"],
                "account_name": acct["name"],
                "account_type": acct["account_type"],
                "direction":    acct["direction"],
                "is_preset":    True,
                "is_active":    True,
                "created_at":   _now(),
            })
            created += 1
    return created


def seed_organizations(db) -> dict:
    """Upsert both test organizations and return {name: org_id}."""
    orgs = {
        "La Posada de Jesús": None,
        "Hogar Bambi": None,
    }
    for name in orgs:
        existing = db["organizations"].find_one({"name": name})
        if existing:
            orgs[name] = existing["org_id"]
            print(f"  ✅ Organización ya existe: «{name}»")
        else:
            oid = str(uuid.uuid4())
            db["organizations"].insert_one({
                "org_id": oid,
                "name": name,
                "created_at": _now(),
            })
            orgs[name] = oid
            print(f"  ✅ Organización creada  : «{name}»")
    return orgs


def seed_users(db, org_ids: dict) -> None:
    """Upsert demo users for both organizations. org_ids must contain both orgs."""
    posada_id = org_ids.get("La Posada de Jesús")
    bambi_id  = org_ids.get("Hogar Bambi")

    users = []
    if posada_id:
        users += [
            ("posada@demo.com",  "Admin",   posada_id, "Ana Posada"),
            ("posada2@demo.com", "Usuario", posada_id, "Carlos Posada"),
        ]
    if bambi_id:
        users += [
            ("bambi@demo.com",   "Admin",   bambi_id,  "Maria Bambi"),
            ("bambi2@demo.com",  "Usuario", bambi_id,  "Luis Bambi"),
        ]

    pw_hash = _hash("Demo1234!")
    for email, role, org_id, name in users:
        if db["users"].find_one({"email": email}):
            print(f"  ✅ Usuario ya existe    : «{email}»")
        else:
            db["users"].insert_one({
                "user_id": str(uuid.uuid4()),
                "email": email,
                "password_hash": pw_hash,
                "name": name,
                "org_id": org_id,
                "role": role,
                "is_active": True,
                "created_at": _now(),
            })
            print(f"  ✅ Usuario creado       : «{email}» ({role})")


def seed_catalog(db, org_id: str, org_label: str) -> dict:
    """Upsert 5 catalog items and return {name: item_id}."""
    items = [
        ("Arroz",         "Alimentos",          "No Perecederos",    "Saco",    False),
        ("Acetaminofen",  "Medicinas",           "Venta Libre",       "Paquete", True),
        ("Jabón de manos","Higiene y Limpieza",  "Higiene Personal",  "Unidad",  True),
        ("Cuaderno",      "Materiales Educativos","Utiles Escolares", "Unidad",  False),
        ("Frazada",       "Ropa y Calzado",       "Ropa de Cama",     "Unidad",  False),
    ]
    item_ids = {}
    for name, cat, subcat, packaging, tracks_exp in items:
        existing = db["item_catalog"].find_one({"org_id": org_id, "name": name})
        if existing:
            item_ids[name] = existing["item_id"]
        else:
            iid = str(uuid.uuid4())
            db["item_catalog"].insert_one({
                "item_id": iid,
                "org_id": org_id,
                "name": name,
                "category": cat,
                "subcategory": subcat,
                "default_packaging": packaging,
                "tracks_expiration": tracks_exp,
                "is_active": True,
                "created_at": _now(),
            })
            item_ids[name] = iid
    print(f"  ✅ Catálogo sembrado ({org_label}): {len(item_ids)} artículos")
    return item_ids


def seed_donations(db, org_id: str, item_ids: dict, org_label: str) -> None:
    """Insert 8 sample donation entries and upsert inventory_master."""
    donations = [
        ("Arroz",          "Saco",    50, 15, "Cruz Roja",       None),
        ("Arroz",          "Saco",    30, 10, "Banco de Alimentos", None),
        ("Acetaminofen",   "Paquete", 20,  5, "Farmavida",       25),
        ("Acetaminofen",   "Paquete", 15,  3, "Donante Anónimo", 60),
        ("Jabón de manos", "Unidad",  40,  8, "P&G Venezuela",   45),
        ("Jabón de manos", "Unidad",  25,  2, "Cruz Roja",       90),
        ("Cuaderno",       "Unidad",  80, 20, "Fundación Leer",  None),
        ("Frazada",        "Unidad",  12,  1, "ACNUR",           None),
    ]
    for name, packaging, qty, days_ago, donor, exp_days in donations:
        item_id = item_ids.get(name)
        if not item_id:
            continue
        # look up category info from catalog
        cat_doc = db["item_catalog"].find_one({"item_id": item_id})
        exp_date = _days_from_now(exp_days) if exp_days else None
        db["donation_entries"].insert_one({
            "entry_id": str(uuid.uuid4()),
            "org_id": org_id,
            "date": _days_ago(days_ago),
            "item_id": item_id,
            "item_name": name,
            "category": cat_doc["category"],
            "subcategory": cat_doc["subcategory"],
            "packaging": packaging,
            "quantity": qty,
            "expiration_date": exp_date,
            "donor_name": donor,
            "donor_org": donor,
            "notes": "",
            "created_at": _days_ago(days_ago),
        })
        # Upsert inventory master
        db["inventory_master"].update_one(
            {"org_id": org_id, "item_id": item_id},
            {"$inc": {"current_stock": qty},
             "$setOnInsert": {
                 "item_id": item_id,
                 "org_id": org_id,
                 "name": name,
                 "category": cat_doc["category"],
                 "subcategory": cat_doc["subcategory"],
                 "packaging": packaging,
                 "expiration_date": exp_date,
             }},
            upsert=True,
        )
    print(f"  ✅ Donaciones sembradas ({org_label}): {len(donations)} entradas")


def seed_exits(db, org_id: str, item_ids: dict, org_label: str) -> None:
    """Insert 5 sample inventory exit records and update stock."""
    exits = [
        ("Arroz",          "Saco",    20, 7,  "Familia González", "Ayuda Humanitaria"),
        ("Arroz",          "Saco",    10, 4,  "Familia Torres",   "Ayuda Humanitaria"),
        ("Acetaminofen",   "Paquete",  8, 6,  "Centro de Salud",  "Distribucion Programada"),
        ("Jabón de manos", "Unidad",  15, 3,  "Hogar Las Palmas", "Ayuda Humanitaria"),
        ("Cuaderno",       "Unidad",  30, 9,  "Escuela Básica",   "Distribucion Programada"),
    ]
    for name, packaging, qty, days_ago, recipient, reason in exits:
        item_id = item_ids.get(name)
        if not item_id:
            continue
        cat_doc = db["item_catalog"].find_one({"item_id": item_id})
        db["inventory_exits"].insert_one({
            "exit_id": str(uuid.uuid4()),
            "org_id": org_id,
            "date": _days_ago(days_ago),
            "item_id": item_id,
            "item_name": name,
            "category": cat_doc["category"],
            "subcategory": cat_doc["subcategory"],
            "packaging": packaging,
            "quantity": qty,
            "recipient_name": recipient,
            "recipient_org": recipient,
            "reason": reason,
            "notes": "",
            "created_at": _days_ago(days_ago),
        })
        db["inventory_master"].update_one(
            {"org_id": org_id, "item_id": item_id},
            {"$inc": {"current_stock": -qty}},
        )
    print(f"  ✅ Salidas sembradas     ({org_label}): {len(exits)} registros")


def seed_finance(db, org_id: str, org_label: str) -> None:
    """Insert 6 sample financial transactions."""
    transactions = [
        (500,  "USD", "Ingreso", "Actividades de Operacion", "Donacion Recibida",
         "Donación en efectivo - Cruz Roja", "Banco Principal", 20),
        (1200, "USD", "Ingreso", "Actividades de Operacion", "Subvencion",
         "Subvención ACNUR trimestre Q2", "Banco Principal", 15),
        (300,  "USD", "Egreso",  "Actividades de Operacion", "Compra de Suministros",
         "Compra insumos de higiene", "Banco Principal", 12),
        (150,  "USD", "Egreso",  "Actividades de Operacion", "Logistica",
         "Transporte donaciones región Los Andes", "Caja Chica", 8),
        (800,  "USD", "Egreso",  "Actividades de Operacion", "Salarios",
         "Nómina junio 2026", "Banco Principal", 5),
        (200,  "USD", "Ingreso", "Actividades de Operacion", "Donacion Recibida",
         "Donación anónima en efectivo", "Caja Chica", 2),
    ]
    for amount, currency, direction, niif_cat, niif_sub, description, bank, days_ago in transactions:
        db["financial_ledger"].insert_one({
            "transaction_id": str(uuid.uuid4()),
            "org_id": org_id,
            "date": _days_ago(days_ago),
            "amount": amount,
            "currency": currency,
            "direction": direction,
            "niif_category": niif_cat,
            "subcategory": niif_sub,
            "description": description,
            "source_bank": bank,
            "created_at": _days_ago(days_ago),
        })
    print(f"  ✅ Finanzas sembradas    ({org_label}): {len(transactions)} transacciones")


def seed_all(db) -> None:
    print("\n📋 Sembrando datos de prueba…\n")
    org_ids = seed_organizations(db)

    print()
    # Seed users once with all org IDs so cross-org lookups work
    seed_users(db, org_ids)
    print()

    for org_name, org_id in org_ids.items():
        short = org_name.split()[0]
        print(f"  — {org_name} —")
        n_accts = seed_accounts(db, org_id)
        if n_accts:
            print(f"  ✅ Plan de cuentas      ({short}): {n_accts} cuentas NIIF")
        else:
            print(f"  ✅ Plan de cuentas ya existe ({short})")
        item_ids = seed_catalog(db, org_id, short)
        seed_donations(db, org_id, item_ids, short)
        seed_exits(db, org_id, item_ids, short)
        seed_finance(db, org_id, short)
        print()


def reset_all(db) -> None:
    collections = [
        "organizations", "users", "item_catalog", "inventory_master",
        "donation_entries", "inventory_exits", "financial_ledger",
        "chart_of_accounts", "stakeholders", "audit_log",
    ]
    print("\n🗑️  Limpiando base de datos de prueba…")
    for col in collections:
        result = db[col].delete_many({})
        print(f"  🗑️  {col}: {result.deleted_count} documentos eliminados")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gestiona datos de prueba para Organiza Vzla."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--seed",  action="store_true", help="Agrega datos de prueba.")
    group.add_argument("--reset", action="store_true", help="Borra y re-siembra todo.")
    args = parser.parse_args()

    if not os.path.exists(SECRETS_PATH):
        print("❌ No se encontró .streamlit/secrets.toml")
        sys.exit(1)

    secrets = _load_toml(SECRETS_PATH)
    try:
        mongo_uri = secrets["mongo"]["uri"]
    except KeyError:
        print("❌ El archivo secrets.toml no tiene la clave [mongo] uri.")
        sys.exit(1)

    app_mode = secrets.get("app", {}).get("mode", "production")
    db_name  = "organiza_vzla_test" if app_mode == "test" else "organiza_vzla"

    _require_test_db(db_name)

    print(f"🔗 Conectando a MongoDB → base de datos: «{db_name}»")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=8000)
    try:
        client.admin.command("ping")
    except Exception as exc:
        print(f"❌ No se pudo conectar: {exc}")
        sys.exit(1)

    db = client[db_name]

    if args.reset:
        reset_all(db)
        seed_all(db)
        print("✅ Reset completo. Base de datos de prueba lista.\n")
    else:
        seed_all(db)
        print("✅ Datos sembrados. Base de datos de prueba lista.\n")

    print("  Usuarios de prueba disponibles:")
    print("    posada@demo.com  / Demo1234!  (Admin  - La Posada de Jesús)")
    print("    posada2@demo.com / Demo1234!  (Usuario - La Posada de Jesús)")
    print("    bambi@demo.com   / Demo1234!  (Admin  - Hogar Bambi)")
    print("    bambi2@demo.com  / Demo1234!  (Usuario - Hogar Bambi)")
    print()
    print("  Para usar el modo de prueba en la app:")
    print("    1. Abre .streamlit/secrets.toml")
    print('    2. Cambia: mode = "test"')
    print("    3. Ejecuta: streamlit run app.py")
    print()

    client.close()


if __name__ == "__main__":
    main()
