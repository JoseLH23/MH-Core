"""Esquema portable del estado analítico EjiXhole."""
from __future__ import annotations

TABLES: dict[str, tuple[str, ...]] = {
    "ejixhole_event_inbox": (
        "event_id", "event_key", "event_type", "schema_version",
        "aggregate_type", "aggregate_id", "occurred_at", "payload_json",
        "envelope_sha256", "received_at",
    ),
    "ejixhole_processed_events": (
        "event_id", "event_key", "processed_at",
    ),
    "ejixhole_operational_reservations": (
        "reservation_id", "status", "reservation_type", "people", "total",
        "paid_amount", "pending_balance", "arrival_date", "departure_date",
        "last_event_type", "updated_at",
    ),
    "ejixhole_prediction_snapshots": (
        "business_date", "horizon_start", "horizon_end", "expected_visitors",
        "expected_revenue", "activity_level", "cancellation_risk", "confidence",
        "generated_at",
    ),
    "ejixhole_recommendation_decisions": (
        "business_date", "code", "decision", "decided_at", "outcome",
        "outcome_note", "outcome_at",
    ),
    "ejixhole_weather_cache": (
        "cache_key", "payload_json", "fetched_at",
    ),
}

CREATE_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS ejixhole_event_inbox (
        event_id TEXT PRIMARY KEY,
        event_key TEXT NOT NULL UNIQUE,
        event_type TEXT NOT NULL,
        schema_version INTEGER NOT NULL,
        aggregate_type TEXT NOT NULL,
        aggregate_id TEXT NOT NULL,
        occurred_at TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        envelope_sha256 TEXT NOT NULL,
        received_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ejixhole_processed_events (
        event_id TEXT PRIMARY KEY,
        event_key TEXT NOT NULL UNIQUE,
        processed_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ejixhole_operational_reservations (
        reservation_id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        reservation_type TEXT,
        people INTEGER,
        total TEXT,
        paid_amount TEXT NOT NULL DEFAULT '0',
        pending_balance TEXT,
        arrival_date TEXT,
        departure_date TEXT,
        last_event_type TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ejixhole_prediction_snapshots (
        business_date TEXT PRIMARY KEY,
        horizon_start TEXT NOT NULL,
        horizon_end TEXT NOT NULL,
        expected_visitors INTEGER NOT NULL,
        expected_revenue TEXT NOT NULL,
        activity_level TEXT NOT NULL,
        cancellation_risk TEXT NOT NULL,
        confidence TEXT NOT NULL,
        generated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ejixhole_recommendation_decisions (
        business_date TEXT NOT NULL,
        code TEXT NOT NULL,
        decision TEXT NOT NULL,
        decided_at TEXT NOT NULL,
        outcome TEXT,
        outcome_note TEXT,
        outcome_at TEXT,
        PRIMARY KEY (business_date, code)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ejixhole_weather_cache (
        cache_key TEXT PRIMARY KEY,
        payload_json TEXT NOT NULL,
        fetched_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_ejixhole_event_type ON ejixhole_event_inbox(event_type, received_at)",
)


def initialize_state_schema(connection) -> None:
    for statement in CREATE_STATEMENTS:
        connection.execute(statement)
