import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = os.getenv("DDNS_DB_PATH", str(BASE_DIR / "data" / "ddns.sqlite"))

ADMIN_USERNAME = os.getenv("DDNS_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("DDNS_ADMIN_PASSWORD", "admin")
ADMIN_PASSWORD_HASH = os.getenv("DDNS_ADMIN_PASSWORD_HASH")

# 自动生成 session secret
SESSION_SECRET = os.getenv("DDNS_SESSION_SECRET") or secrets.token_urlsafe(32)

CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")

# Optional default zone id used if a domain does not specify one
DEFAULT_ZONE_ID = os.getenv("CLOUDFLARE_DEFAULT_ZONE_ID", "")
