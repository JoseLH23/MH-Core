"""Adaptador mínimo para reutilizar consultas EjiXhole en PostgreSQL."""
from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from typing import Any

from sqlalchemy.engine import Engine


class HybridRow(Mapping[str, Any]):
    def __init__(self, columns: Sequence[str], values: Sequence[Any]) -> None:
        self._columns = tuple(columns)
        self._values = tuple(values)
        self._mapping = dict(zip(self._columns, self._values))

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._mapping[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._columns)

    def __len__(self) -> int:
        return len(self._columns)

    def keys(self):
        return self._mapping.keys()


class CursorResult:
    def __init__(self, cursor=None, *, rows: list[HybridRow] | None = None, rowcount: int = -1) -> None:
        self.cursor = cursor
        self._rows = rows
        self._index = 0
        self.rowcount = cursor.rowcount if cursor is not None else rowcount
        self._columns = (
            [column.name if hasattr(column, "name") else column[0] for column in cursor.description]
            if cursor is not None and cursor.description
            else []
        )

    def _wrap(self, row):
        if row is None:
            return None
        if isinstance(row, HybridRow):
            return row
        return HybridRow(self._columns, row)

    def fetchone(self):
        if self._rows is not None:
            if self._index >= len(self._rows):
                return None
            row = self._rows[self._index]
            self._index += 1
            return row
        return self._wrap(self.cursor.fetchone())

    def fetchall(self):
        if self._rows is not None:
            remaining = self._rows[self._index :]
            self._index = len(self._rows)
            return remaining
        return [self._wrap(row) for row in self.cursor.fetchall()]


class PostgresCompatConnection:
    """Expone la parte de sqlite3.Connection usada por las integraciones actuales."""

    backend = "postgresql"

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.raw = engine.raw_connection()
        self._closed = False

    @staticmethod
    def _statement(sql: str) -> str:
        return sql.replace("?", "%s")

    @property
    def in_transaction(self) -> bool:
        info = getattr(self.raw, "info", None)
        return bool(info and int(info.transaction_status) != 0)

    def execute(self, sql: str, parameters: Sequence[Any] | None = None) -> CursorResult:
        normalized = sql.strip()
        upper = normalized.upper()
        if upper.startswith("PRAGMA JOURNAL_MODE"):
            return CursorResult(rows=[HybridRow(("journal_mode",), ("postgresql",))], rowcount=1)
        if upper.startswith("PRAGMA"):
            return CursorResult(rows=[], rowcount=0)
        if upper == "BEGIN IMMEDIATE" or upper == "BEGIN":
            cursor = self.raw.cursor()
            cursor.execute("BEGIN")
            return CursorResult(cursor)
        if upper == "COMMIT":
            self.raw.commit()
            return CursorResult(rows=[], rowcount=0)
        if upper == "ROLLBACK":
            self.raw.rollback()
            return CursorResult(rows=[], rowcount=0)

        cursor = self.raw.cursor()
        cursor.execute(self._statement(sql), tuple(parameters or ()))
        return CursorResult(cursor)

    def commit(self) -> None:
        self.raw.commit()

    def rollback(self) -> None:
        self.raw.rollback()

    def close(self) -> None:
        if not self._closed:
            try:
                if self.in_transaction:
                    self.raw.rollback()
            finally:
                self.raw.close()
                self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        try:
            if exc_type is None:
                self.raw.commit()
            else:
                self.raw.rollback()
        finally:
            self.raw.close()
            self._closed = True
        return False
