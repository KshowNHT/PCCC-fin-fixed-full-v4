"""Generate first-deployment secrets. Never overwrite an existing .env."""
import re
import os
import secrets
from pathlib import Path
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--domain", required=True)
parser.add_argument("--email", required=True)
args = parser.parse_args()
if not re.fullmatch(r"(?=.{1,253}$)[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", args.domain) or "." not in args.domain:
    parser.error("Specify a DNS hostname only; no scheme, path or port")
if not re.fullmatch(r"[^\s@=]+@[^\s@=]+\.[^\s@=]+", args.email):
    parser.error("Invalid ACME email")
path=Path(__file__).resolve().parents[1]/".env"
os.umask(0o077)
with path.open("x") as f:
    f.write(f"PCCC_DOMAIN={args.domain}\nACME_EMAIL={args.email}\nPOSTGRES_PASSWORD={secrets.token_hex(24)}\nJWT_SECRET={secrets.token_hex(32)}\nPCCC_ADMIN_USERNAME=admin\nPCCC_ADMIN_PASSWORD=A1{secrets.token_hex(16)}\nGEMINI_API_KEY=\nGEMINI_MODELS=gemini-3.8-flash\nJWT_EXPIRE_MINUTES=120\nMAX_UPLOAD_SIZE_MB=25\nMAX_STAFF_ACCOUNTS=10\n")
path.chmod(0o600)
print("Created .env. Set GEMINI_API_KEY if needed; use the admin password from this file.")
