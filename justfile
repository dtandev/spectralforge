# TerraEye S&I Project Justfile
# Usage: just <command>
# Requires: just (https://github.com/casey/just), uv (https://github.com/astral-sh/uv)

# Default: list available commands
default:
    @just --list

# Explain what this product does and how to run it
help:
    @echo "SpectralForge — TODO: describe what this product actually does once implemented."
    @echo "Currently this is a scaffolded skeleton: src/main.py is a generated placeholder"
    @echo "entry point with no real spectral-data processing logic implemented yet."
    @echo ""
    @echo "Run 'just --list' for the full mechanical command reference."

# Install dependencies and set up the project environment
setup:
    @echo "Setting up project environment..."
    uv sync
    uv run pre-commit install
    uv run pre-commit install --hook-type commit-msg
    @echo "Copying .env-example to .env (if not exists)..."
    cp -n .env-example .env || true
    @echo "✅ Setup complete. Edit .env with your values."

# Run the main entry point
run *ARGS:
    uv run python src/main.py {{ARGS}}

# Run all tests
test:
    uv run pytest tests/ -v

# Run all quality checks (lint, format, type check)
check:
    uv run ruff check src/ tests/
    uv run ruff format --check src/ tests/
    @echo "✅ All checks passed."

# Auto-fix lint and format issues
fix:
    uv run ruff check --fix src/ tests/
    uv run ruff format src/ tests/

# Run pre-commit on all files
lint:
    uv run pre-commit run --all-files

# Bump version based on conventional commits, update CHANGELOG, tag, and push
release:
    uv run cz bump
    git push && git push --tags

# Start the local dev database (Postgres+PostGIS), auto-applying db/schema/*.sql on first run
db-up:
    docker compose -f db/docker-compose.yml up -d
    @echo "Waiting for database to become healthy..."
    docker compose -f db/docker-compose.yml exec db pg_isready -U spectralforge -d spectralforge_dev

# Stop the local dev database (data persists in the named volume)
db-down:
    docker compose -f db/docker-compose.yml down

# Apply SpectralForge's own `spectralforge` schema to the DB configured in .env (safe against the real Azure DB too — see src/db.py)
db-apply-schema:
    uv run --extra db python src/db.py

# Snapshot the live SpectralHub DB schema/row counts to db/schema_snapshot.json (read-only; needs VPN/office network, see scripts/inspect_live_db_schema.py)
db-inspect:
    uv run --extra db python scripts/inspect_live_db_schema.py

# Export a full local copy of the live DB to db/snapshot/spectralhub.dump via pg_dump (read-only; needs VPN/office network + pg_dump installed)
db-export-snapshot:
    ./scripts/export_live_db_snapshot.sh

# Restore db/snapshot/spectralhub.dump into the local dev DB configured in .env via pg_restore — run `just db-up` first (fully offline, needs pg_restore installed)
db-import-snapshot:
    ./scripts/import_db_snapshot.sh
