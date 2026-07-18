"""Copia memorias JSON a SQL de forma idempotente y conserva el archivo."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from mh_core.core.config import HISTORY_FILE
from mh_core.database.json_memory_repository import JsonMemoryRepository
from mh_core.database.sql_memory_repository import SqlMemoryRepository
from mh_core.persistence.database import create_engine_for_url


def migrate(source_path: Path, *, apply: bool) -> dict:
    memories = JsonMemoryRepository(source_path).listar()
    if not apply:
        return {"source": len(memories), "migrated": 0, "applied": False}
    configured = os.getenv("MH_DATABASE_URL", "").strip()
    if not configured:
        raise ValueError("Falta MH_DATABASE_URL")
    target = SqlMemoryRepository(create_engine_for_url(configured))
    before = target.count()
    for memory in memories:
        target.guardar(memory)
    return {
        "source": len(memories),
        "migrated": target.count() - before,
        "applied": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=HISTORY_FILE)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    result = migrate(args.source, apply=args.apply)
    print(f"source={result['source']} migrated={result['migrated']} applied={result['applied']}")


if __name__ == "__main__":
    main()
