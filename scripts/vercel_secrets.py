"""
Push the backend secrets from `.env.prod` to the linked Vercel API project
(production environment) without printing them.

Run from the project root after `vercel link`:
    python -m scripts.vercel_secrets
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import prod_env

BACKEND_VARS = [
    "DATABASE_URL",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_BUCKET",
    "SECRET_KEY",
    "CRON_SECRET",
    "ANTHROPIC_API_KEY",
]
REQUIRED = ["DATABASE_URL", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SECRET_KEY", "CRON_SECRET"]
SECRET = {"DATABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SECRET_KEY", "CRON_SECRET", "ANTHROPIC_API_KEY"}


def main() -> None:
    values = prod_env.load()
    missing = [k for k in REQUIRED if not values.get(k)]
    if missing:
        sys.exit(f"Faltan en .env.prod: {', '.join(missing)}")

    vercel = "vercel.cmd" if os.name == "nt" else "vercel"
    for key in BACKEND_VARS:
        value = values.get(key)
        if not value:
            continue
        cmd = [vercel, "env", "add", key, "production", "--force",
               "--sensitive" if key in SECRET else "--no-sensitive"]
        result = subprocess.run(cmd, input=value, text=True, capture_output=True)
        status = "✓" if result.returncode == 0 else "✗"
        print(f"{status} {key}")
        if result.returncode != 0:
            # stderr from the CLI never contains the value itself
            print("   " + (result.stderr.strip().splitlines() or ["error"])[-1])


if __name__ == "__main__":
    main()
