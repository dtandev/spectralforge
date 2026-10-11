"""Read-only introspection of the live SpectralHub database.

Run this LOCALLY, from a network that can actually reach the DB (VPN/office network) —
it will not work from a sandboxed CI/agent environment behind a restrictive firewall.

Captures table list, row counts, column schema, spectral_profiles, and the most common
(name, class) pairs per samples table (useful for judging how many replicates per mineral
exist) into a single JSON file for later offline analysis — no query results are printed
in full, only written to disk.

Usage:
    cp .env-example .env   # fill in DB_USER/DB_PASSWORD/DB_HOST/DB_PORT/DB_NAME
    uv run python scripts/inspect_live_db_schema.py [output_path]

This script only ever runs SELECT/COUNT queries. It never writes to the database.
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from spectralhub.database import SpectralDatabase

DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent.parent / "db" / "schema_snapshot.json"
SYSTEM_TABLES = {"geography_columns", "geometry_columns", "spatial_ref_sys"}


def inspect(db: SpectralDatabase) -> dict:
    snapshot: dict = {"tables": {}}

    tables = db.get_tables()
    snapshot["table_list"] = tables

    for table in tables:
        if table in SYSTEM_TABLES:
            continue

        entry: dict = {}

        try:
            db.cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
            entry["row_count"] = db.cursor.fetchone()[0]
        except Exception as e:  # noqa: BLE001 - best-effort introspection, keep going on error
            db.connection.rollback()
            entry["row_count_error"] = str(e)

        db.cursor.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = %s ORDER BY ordinal_position",
            (table,),
        )
        entry["columns"] = [{"name": c[0], "type": c[1]} for c in db.cursor.fetchall()]

        if table.endswith("_samples") or table == "samples":
            try:
                db.cursor.execute(
                    f'SELECT name, class, COUNT(*) FROM "{table}" '  # noqa: S608 - table name from information_schema, not user input
                    "GROUP BY name, class ORDER BY COUNT(*) DESC LIMIT 50"
                )
                entry["top_name_class_counts"] = [{"name": r[0], "class": r[1], "count": r[2]} for r in db.cursor.fetchall()]
            except Exception as e:  # noqa: BLE001
                db.connection.rollback()
                entry["top_name_class_counts_error"] = str(e)

        snapshot["tables"][table] = entry

    try:
        db.cursor.execute(
            "SELECT id, provider, description, array_length(centers, 1), center_units, band_quantity "
            "FROM spectral_profiles ORDER BY id"
        )
        snapshot["spectral_profiles"] = [
            {
                "id": r[0],
                "provider": r[1],
                "description": r[2],
                "n_bands": r[3],
                "center_units": r[4],
                "band_quantity": r[5],
            }
            for r in db.cursor.fetchall()
        ]
    except Exception as e:  # noqa: BLE001
        db.connection.rollback()
        snapshot["spectral_profiles_error"] = str(e)

    return snapshot


def main() -> None:
    load_dotenv()

    required = ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_NAME"]
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}. Copy .env-example to .env and fill them in.")
        sys.exit(1)

    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT_PATH

    db = SpectralDatabase(
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"],
    )
    db.connect()
    try:
        snapshot = inspect(db)
    finally:
        db.close()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, indent=2, default=str))
    print(f"Wrote schema snapshot to {output_path}")


if __name__ == "__main__":
    main()
