"""
Load production variables from the git-ignored `.env.prod` file.

Import this BEFORE anything from `backend` so the settings pick the values up.
Values already present in the environment win. SECRET_KEY / CRON_SECRET are
generated (and written back to the file) when empty, so they stay stable.
"""
import os
import secrets
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env.prod"
GENERATED = ("SECRET_KEY", "CRON_SECRET")


def read() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_FILE.exists():
        return values
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def ensure_generated() -> None:
    """Fill empty SECRET_KEY / CRON_SECRET in .env.prod with random values."""
    if not ENV_FILE.exists():
        return
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    changed = False
    for i, line in enumerate(lines):
        for key in GENERATED:
            if line.strip() == f"{key}=":
                lines[i] = f"{key}={secrets.token_urlsafe(48)}"
                changed = True
    if changed:
        ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load() -> dict[str, str]:
    ensure_generated()
    values = read()
    for key, value in values.items():
        if value and key not in os.environ:
            os.environ[key] = value
    os.environ.setdefault("DEBUG", "false")
    return values


def missing(required: list[str]) -> list[str]:
    return [k for k in required if not os.environ.get(k)]
