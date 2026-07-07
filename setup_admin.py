"""
setup_admin.py — One-time database seed script.

Creates the initial organization ("La Posada de Jesús") and the first Admin
user in MongoDB.  Safe to run multiple times — it will never create duplicates.

────────────────────────────────────────────────────────
 Prerequisites
────────────────────────────────────────────────────────
 1. Your .streamlit/secrets.toml must exist with your MongoDB URI:

        [mongo]
        uri = "mongodb+srv://user:password@cluster.mongodb.net/..."

 2. All project dependencies must be installed:

        pip install -r requirements.txt

────────────────────────────────────────────────────────
 Usage (from the project root in your terminal)
────────────────────────────────────────────────────────
        python setup_admin.py

────────────────────────────────────────────────────────
 What it creates
────────────────────────────────────────────────────────
  • Organization  : La Posada de Jesús
  • Admin email   : alejandrofuenmayor882@gmail.com
  • Initial password: LaPosada2024!
    ⚠️  Change this password on your very first login!
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

# ── Configuration ─────────────────────────────────────────────────────────────
SECRETS_PATH = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")

ORG_NAME = "La Posada de Jesús"
ADMIN_EMAIL = "alejandrofuenmayor882@gmail.com"
ADMIN_NAME = "Alejandro Fuenmayor"
ADMIN_PASSWORD = "LaPosada2024!"  # Change after first login


# ── Helpers ───────────────────────────────────────────────────────────────────

def _box(lines: list[str]) -> None:
    """Print lines wrapped in a simple ASCII box."""
    width = max(len(l) for l in lines) + 4
    print("  ┌" + "─" * width + "┐")
    for line in lines:
        pad = width - len(line) - 2
        print(f"  │  {line}{' ' * pad}  │")
    print("  └" + "─" * width + "┘")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    # 1. Load secrets
    if not os.path.exists(SECRETS_PATH):
        print("❌ No se encontró .streamlit/secrets.toml")
        print()
        print("  Crea ese archivo con tu URI de MongoDB:")
        print()
        print("  [mongo]")
        print('  uri = "mongodb+srv://..."')
        sys.exit(1)

    secrets = _load_toml(SECRETS_PATH)
    try:
        mongo_uri = secrets["mongo"]["uri"]
    except KeyError:
        print("❌ El archivo secrets.toml no tiene la clave [mongo] uri.")
        sys.exit(1)

    # 2. Connect
    print("🔗 Conectando a MongoDB…")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=8000)
    try:
        client.admin.command("ping")
    except Exception as exc:
        print(f"❌ No se pudo conectar a MongoDB: {exc}")
        sys.exit(1)

    db = client["organiza_vzla"]

    # 3. Organization
    existing_org = db["organizations"].find_one({"name": ORG_NAME})
    if existing_org:
        org_id = existing_org["org_id"]
        print(f"✅ Organización ya existe : «{ORG_NAME}»")
    else:
        org_id = str(uuid.uuid4())
        db["organizations"].insert_one(
            {
                "org_id": org_id,
                "name": ORG_NAME,
                "created_at": datetime.now(timezone.utc),
            }
        )
        print(f"✅ Organización creada   : «{ORG_NAME}»")

    # 4. Admin user
    existing_user = db["users"].find_one({"email": ADMIN_EMAIL.lower()})
    if existing_user:
        print(f"✅ Usuario admin ya existe: «{ADMIN_EMAIL}»")
    else:
        user_id = str(uuid.uuid4())
        password_hash = bcrypt.hashpw(
            ADMIN_PASSWORD.encode(), bcrypt.gensalt()
        ).decode()

        db["users"].insert_one(
            {
                "user_id": user_id,
                "email": ADMIN_EMAIL.lower(),
                "password_hash": password_hash,
                "name": ADMIN_NAME,
                "org_id": org_id,
                "role": "Admin",
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
            }
        )
        db["audit_log"].insert_one(
            {
                "org_id": org_id,
                "timestamp": datetime.now(timezone.utc),
                "action": "create",
                "collection": "users",
                "record_id": user_id,
                "user": "setup_admin.py",
                "changes": {},
            }
        )
        print(f"✅ Usuario admin creado  : «{ADMIN_EMAIL}»")
        print()
        _box(
            [
                f"Correo      : {ADMIN_EMAIL}",
                f"Contraseña  : {ADMIN_PASSWORD}",
                "",
                "⚠️  CAMBIA esta contraseña en tu primer inicio de sesión.",
            ]
        )

    print()
    print("✅ Configuración completada. Ahora ejecuta:")
    print()
    print("   streamlit run app.py")
    print()
    client.close()


if __name__ == "__main__":
    main()
