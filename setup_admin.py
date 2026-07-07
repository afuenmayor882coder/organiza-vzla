"""
setup_admin.py — Database seed script.

Creates all organizations, the first Admin/Master users, and seeds the NIIF
chart of accounts.  Safe to run multiple times — it never creates duplicates.

This script respects the [app] mode setting in .streamlit/secrets.toml:
  mode = "production"  →  writes to  organiza_vzla        (real data)
  mode = "test"        →  writes to  organiza_vzla_test   (safe sandbox)

────────────────────────────────────────────────────────
 What it creates
────────────────────────────────────────────────────────
  • Org         : La Posada de Jesús
  • Master user : alejandrofuenmayor882@gmail.com  (role: Master)
  • Demo admin  : posada@demo.com / Posada2024!    (Admin – La Posada)
  • Org         : Hogar Bambi
  • Demo admin  : bambi@demo.com  / Bambi2024!     (Admin – Hogar Bambi)
  • NIIF Chart of Accounts seeded for both orgs
"""

import os
import sys
import uuid
from datetime import datetime, timezone

# ── TOML parser (Python 3.11+ has tomllib built-in) ──────────────────────────
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
        print("❌ Necesitas Python 3.11+ o la librería 'toml' (pip install toml).")
        sys.exit(1)

import bcrypt
from pymongo import MongoClient

from utils.constants import NIIF_CHART_OF_ACCOUNTS

# ── Configuration ─────────────────────────────────────────────────────────────
SECRETS_PATH = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")

_DEFAULT_ORG_SETTINGS = {
    "display_name": "",
    "logo_url": "",
    "primary_color": "#0066CC",
    "secondary_color": "#E8F0FE",
    "welcome_message": "",
    "currency_default": "USD",
    "low_stock_threshold": 10,
    "expiration_warning_days": 30,
}

# Master user — owns La Posada, but has cross-org access
MASTER_EMAIL     = "alejandrofuenmayor882@gmail.com"
MASTER_NAME      = "Alejandro Fuenmayor"
MASTER_PASSWORD  = "LaPosada2024!"

# Organizations and their demo admins
ORGS = [
    {
        "name":       "La Posada de Jesús",
        "color":      "#0066CC",
        "demo_email": "posada@demo.com",
        "demo_name":  "Admin Posada",
        "demo_pass":  "Posada2024!",
        # Optional second user (regular role)
        "user_email": "posada2@demo.com",
        "user_name":  "Usuario Posada",
        "user_pass":  "Posada2024!",
    },
    {
        "name":       "Hogar Bambi",
        "color":      "#E05C00",
        "demo_email": "bambi@demo.com",
        "demo_name":  "Admin Bambi",
        "demo_pass":  "Bambi2024!",
        # Optional second user (regular role)
        "user_email": "bambi2@demo.com",
        "user_name":  "Usuario Bambi",
        "user_pass":  "Bambi2024!",
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _box(lines: list[str]) -> None:
    width = max(len(l) for l in lines) + 4
    print("  ┌" + "─" * width + "┐")
    for line in lines:
        pad = width - len(line) - 2
        print(f"  │  {line}{' ' * pad}  │")
    print("  └" + "─" * width + "┘")


def _ensure_org(db, name: str, color: str) -> str:
    """Get or create an organization; returns its org_id."""
    existing = db["organizations"].find_one({"name": name})
    if existing:
        print(f"   ✅ Org ya existe    : «{name}»")
        return existing["org_id"]
    org_id = str(uuid.uuid4())
    settings = {**_DEFAULT_ORG_SETTINGS, "primary_color": color}
    db["organizations"].insert_one({
        "org_id":     org_id,
        "name":       name,
        "settings":   settings,
        "created_at": datetime.now(timezone.utc),
    })
    print(f"   ✅ Org creada       : «{name}»")
    return org_id


def _ensure_user(db, email: str, name: str, password: str,
                 org_id: str, role: str) -> None:
    """Get or create a user (idempotent). Also upgrades role if needed."""
    existing = db["users"].find_one({"email": email.lower()})
    if existing:
        if existing.get("role") != role:
            db["users"].update_one(
                {"email": email.lower()},
                {"$set": {"role": role}},
            )
            print(f"   🔄 Rol actualizado  : «{email}» → {role}")
        else:
            print(f"   ✅ Usuario ya existe: «{email}» ({role})")
        return
    user_id = str(uuid.uuid4())
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    db["users"].insert_one({
        "user_id":       user_id,
        "email":         email.lower(),
        "password_hash": pw_hash,
        "name":          name,
        "org_id":        org_id,
        "role":          role,
        "is_active":     True,
        "created_at":    datetime.now(timezone.utc),
    })
    print(f"   ✅ Usuario creado   : «{email}» ({role})")


def _seed_accounts(db, org_id: str) -> int:
    """Seed the default NIIF chart of accounts for an org (idempotent)."""
    created = 0
    for acct in NIIF_CHART_OF_ACCOUNTS:
        if not db["chart_of_accounts"].find_one(
            {"org_id": org_id, "account_code": acct["code"]}
        ):
            db["chart_of_accounts"].insert_one({
                "account_id":   str(uuid.uuid4()),
                "org_id":       org_id,
                "account_code": acct["code"],
                "account_name": acct["name"],
                "account_type": acct["account_type"],
                "direction":    acct["direction"],
                "is_preset":    True,
                "is_active":    True,
                "created_at":   datetime.now(timezone.utc),
            })
            created += 1
    return created


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    # 1. Load secrets
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
    print(f"\n🔧 Modo: {app_mode.upper()} → base de datos: «{db_name}»\n")

    # 2. Connect
    print("🔗 Conectando a MongoDB…")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=8000)
    try:
        client.admin.command("ping")
        print("   Conexión exitosa.\n")
    except Exception as exc:
        print(f"❌ No se pudo conectar a MongoDB: {exc}")
        sys.exit(1)

    db = client[db_name]

    # 3. Seed each organization + its demo admin
    org_ids: dict[str, str] = {}
    for org_cfg in ORGS:
        print(f"── {org_cfg['name']} ──")
        oid = _ensure_org(db, org_cfg["name"], org_cfg["color"])
        org_ids[org_cfg["name"]] = oid

        n = _seed_accounts(db, oid)
        if n:
            print(f"   ✅ Plan de cuentas : {n} cuentas NIIF creadas")
        else:
            print(f"   ✅ Plan de cuentas : ya existe")

        _ensure_user(
            db,
            org_cfg["demo_email"],
            org_cfg["demo_name"],
            org_cfg["demo_pass"],
            oid,
            "Admin",
        )
        if org_cfg.get("user_email"):
            _ensure_user(
                db,
                org_cfg["user_email"],
                org_cfg["user_name"],
                org_cfg["user_pass"],
                oid,
                "Usuario",
            )
        print()

    # 4. Master user (belongs to La Posada, but has cross-org view)
    print("── Usuario Master ──")
    posada_id = org_ids.get("La Posada de Jesús", "")
    _ensure_user(db, MASTER_EMAIL, MASTER_NAME, MASTER_PASSWORD, posada_id, "Master")

    print()
    print("=" * 55)
    print("✅  Todo listo. Credenciales de acceso:")
    print("=" * 55)
    _box([
        f"Master  : {MASTER_EMAIL}  /  {MASTER_PASSWORD}",
        f"Posada  : posada@demo.com   /  Posada2024!  (Admin)",
        f"Posada2 : posada2@demo.com  /  Posada2024!  (Usuario)",
        f"Bambi   : bambi@demo.com    /  Bambi2024!   (Admin)",
        f"Bambi2  : bambi2@demo.com   /  Bambi2024!   (Usuario)",
        "",
        "⚠️  Cambia la contraseña master en tu primer login.",
    ])
    print()
    print("   streamlit run app.py")
    print()
    client.close()


if __name__ == "__main__":
    main()
