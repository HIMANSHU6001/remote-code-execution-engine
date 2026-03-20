#!/usr/bin/env bash
# Run Alembic migrations (upgrade to latest revision).
# Requires DATABASE_URL to be set in the environment or .env file.
# Usage: bash scripts/migrate.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Running database migrations..."
python -m alembic upgrade head
echo "==> Migrations complete."
