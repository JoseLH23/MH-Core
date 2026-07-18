"""Copia el estado EjiXhole de SQLite a PostgreSQL y verifica cada tabla."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3

from mh_core.core.config import DATABASE_DIR
from mh_core.integrations.ejixhole_sql_connection import PostgresCompatConnection
from mh_core.integrations.ejixhole_state_schema import TABLES, initialize_state_schema
from mh_core.persistence.database import create_engine_for_url, normalize_database_url


def _source_path(value: Path | None) -> Path:
    if value is not None:
        return value.expanduser().resolve()
    configured = os.getenv("EJIXHOLE_EVENT_INBOX_PATH", "").strip()
    return (
        Path(configured).expanduser().resolve()
        if configured
        else (DATABASE_DIR / "integrations" / "ejixhole_events.sqlite3").resolve()
    )


def _destination_url() -> str:
    value = os.getenv("EJIXHOLE_STATE_DATABASE_URL", "").strip()
    if not value:
        raise ValueError("Falta EJIXHOLE_STATE_DATABASE_URL")
    normalized = normalize_database_url(value)
    if not normalized.startswith("postgresql+"):
        raise ValueError("El destino debe ser PostgreSQL")
    return normalized


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def _rows(connection, table: str, columns: tuple[str, ...]) -> list[dict]:
    order = ",".join(columns)
    selected = ",".join(columns)
    return [dict(row) for row in connection.execute(
        f"SELECT {selected} FROM {table} ORDER BY {order}"
    ).fetchall()]


def _digest(rows: list[dict]) -> str:
    payload = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def migrate(source: Path | None = None, *, apply: bool = False) -> dict:
    source_path = _source_path(source)
    if not source_path.is_file():
        raise FileNotFoundError(f"No existe el archivo fuente: {source_path}")

    source_connection = sqlite3.connect(source_path)
    source_connection.row_factory = sqlite3.Row
    try:
        source_rows = {
            table: _rows(source_connection, table, columns)
            for table, columns in TABLES.items()
            if _table_exists(source_connection, table)
        }
    finally:
        source_connection.close()

    plan = {
        table: {"rows": len(rows), "sha256": _digest(rows)}
        for table, rows in source_rows.items()
    }
    if not apply:
        return {"applied": False, "verified": False, "tables": plan}

    engine = create_engine_for_url(_destination_url())
    destination = PostgresCompatConnection(engine)
    try:
        destination.execute("BEGIN")
        initialize_state_schema(destination)
        for table, rows in source_rows.items():
            columns = TABLES[table]
            placeholders = ",".join("?" for _ in columns)
            column_list = ",".join(columns)
            statement = (
                f"INSERT INTO {table} ({column_list}) VALUES ({placeholders}) "
                "ON CONFLICT DO NOTHING"
            )
            for row in rows:
                destination.execute(statement, tuple(row[column] for column in columns))

        verification = {}
        for table, rows in source_rows.items():
            target_rows = _rows(destination, table, TABLES[table])
            source_hash = _digest(rows)
            target_hash = _digest(target_rows)
            verification[table] = {
                "source_rows": len(rows),
                "target_rows": len(target_rows),
                "source_sha256": source_hash,
                "target_sha256": target_hash,
                "match": len(rows) == len(target_rows) and source_hash == target_hash,
            }
        if not all(item["match"] for item in verification.values()):
            raise RuntimeError("La verificación falló; no se aplicó la migración")
        destination.execute("COMMIT")
        return {"applied": True, "verified": True, "tables": verification}
    except Exception:
        if destination.in_transaction:
            destination.execute("ROLLBACK")
        raise
    finally:
        destination.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Migra estado EjiXhole a PostgreSQL")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    result = migrate(args.source, apply=args.apply)
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.write_text(output + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
