"""Selección explícita del almacenamiento de memorias."""
from __future__ import annotations

import os
from pathlib import Path

from mh_core.database.json_memory_repository import JsonMemoryRepository
from mh_core.database.memory_repository import MemoryRepository
from mh_core.database.sql_memory_repository import SqlMemoryRepository


def create_memory_repository(json_path: Path) -> MemoryRepository:
    if os.getenv("MH_DATABASE_URL", "").strip():
        return SqlMemoryRepository()
    return JsonMemoryRepository(json_path)
