"""Connection + schema helpers for SpectralForge's own Postgres schema.

Reuses spectralhub.database.SpectralDatabase for the connection itself (so SpectralForge
never reimplements DB access) and adds application of db/schema/*.sql — SpectralForge's
own tables (spectralforge.operator_runs, spectralforge.generated_spectra,
spectralforge.generation_inputs), not SpectralHub's.

Usage:
    cp .env-example .env   # fill in DB_USER/DB_PASSWORD/DB_HOST/DB_PORT/DB_NAME
    uv run python src/db.py                                    # applies 002_spectralforge_schema.sql
    uv run python src/db.py 001_spectralhub_reconstructed.sql   # local dev only, see file header
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from spectralhub.database import SpectralDatabase

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "db" / "schema"
DEFAULT_SCHEMA_FILES = ["002_spectralforge_schema.sql"]


def get_db() -> SpectralDatabase:
    load_dotenv()
    db = SpectralDatabase(
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"],
    )
    db.connect()
    return db


def apply_schema(db: SpectralDatabase, filenames: list[str]) -> None:
    for filename in filenames:
        sql_path = SCHEMA_DIR / filename
        db.cursor.execute(sql_path.read_text())
        db.connection.commit()
        print(f"Applied {filename}")


if __name__ == "__main__":
    files = sys.argv[1:] or DEFAULT_SCHEMA_FILES
    connection = get_db()
    try:
        apply_schema(connection, files)
    finally:
        connection.close()
