"""Clima operativo opcional para EjiXhole con caché durable y fallback seguro."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
import os
from typing import Callable
from urllib.parse import urlencode
from urllib.request import urlopen


class EjixholeWeatherService:
    def __init__(self, inbox, fetch_json: Callable[[str, float], dict] | None = None) -> None:
        self.inbox = inbox
        self.fetch_json = fetch_json or self._fetch_json
        self.timeout = float(os.getenv("EJIXHOLE_WEATHER_TIMEOUT_SECONDS", "8"))
        self.cache_minutes = int(os.getenv("EJIXHOLE_WEATHER_CACHE_MINUTES", "30"))
        self._initialize()

    def _initialize(self) -> None:
        with self.inbox._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ejixhole_weather_cache (
                    cache_key TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    fetched_at TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _fetch_json(url: str, timeout: float) -> dict:
        with urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _coordinates() -> tuple[float, float] | None:
        latitude = os.getenv("EJIXHOLE_LATITUDE", "").strip()
        longitude = os.getenv("EJIXHOLE_LONGITUDE", "").strip()
        if not latitude or not longitude:
            return None
        try:
            lat, lon = float(latitude), float(longitude)
        except ValueError:
            return None
        if not -90 <= lat <= 90 or not -180 <= lon <= 180:
            return None
        return lat, lon

    def _cached(self, key: str) -> dict | None:
        with self.inbox._connect() as connection:
            row = connection.execute(
                "SELECT payload_json, fetched_at FROM ejixhole_weather_cache WHERE cache_key=?",
                (key,),
            ).fetchone()
        if not row:
            return None
        fetched_at = datetime.fromisoformat(row["fetched_at"])
        if datetime.now(timezone.utc) - fetched_at > timedelta(minutes=self.cache_minutes):
            return None
        payload = json.loads(row["payload_json"])
        payload["cache"] = "hit"
        return payload

    def _store(self, key: str, payload: dict) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.inbox._connect() as connection:
            connection.execute(
                """
                INSERT INTO ejixhole_weather_cache(cache_key,payload_json,fetched_at)
                VALUES(?,?,?)
                ON CONFLICT(cache_key) DO UPDATE SET payload_json=excluded.payload_json,fetched_at=excluded.fetched_at
                """,
                (key, json.dumps(payload, ensure_ascii=False), now),
            )

    def forecast(self, target: date) -> dict:
        coordinates = self._coordinates()
        if not coordinates:
            return {
                "status": "not_configured",
                "applied": False,
                "message": "Faltan las coordenadas exactas de EjiXhole.",
            }

        latitude, longitude = coordinates
        key = f"{latitude:.5f}:{longitude:.5f}:{target.isoformat()}"
        cached = self._cached(key)
        if cached:
            return cached

        query = urlencode({
            "latitude": latitude,
            "longitude": longitude,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,wind_speed_10m_max",
            "timezone": "America/Mexico_City",
            "forecast_days": 7,
        })
        try:
            raw = self.fetch_json(f"https://api.open-meteo.com/v1/forecast?{query}", self.timeout)
            daily = raw.get("daily") or {}
            dates = daily.get("time") or []
            days = []
            for index, day_text in enumerate(dates):
                days.append({
                    "date": day_text,
                    "weather_code": (daily.get("weather_code") or [None] * len(dates))[index],
                    "temperature_max_c": (daily.get("temperature_2m_max") or [None] * len(dates))[index],
                    "temperature_min_c": (daily.get("temperature_2m_min") or [None] * len(dates))[index],
                    "precipitation_probability_percent": (daily.get("precipitation_probability_max") or [None] * len(dates))[index],
                    "precipitation_mm": (daily.get("precipitation_sum") or [None] * len(dates))[index],
                    "wind_max_kmh": (daily.get("wind_speed_10m_max") or [None] * len(dates))[index],
                })
            rain_risk = max((item["precipitation_probability_percent"] or 0 for item in days), default=0)
            payload = {
                "status": "available",
                "provider": "open-meteo",
                "applied": False,
                "read_only": True,
                "cache": "miss",
                "coordinates": {"latitude": latitude, "longitude": longitude},
                "rain_risk_max_percent": rain_risk,
                "days": days,
                "message": "El clima se muestra como contexto y todavía no cambia automáticamente la predicción.",
            }
            self._store(key, payload)
            return payload
        except Exception:
            stale = self._latest_stale(latitude, longitude)
            if stale:
                stale.update({"status": "stale", "cache": "stale", "message": "Proveedor no disponible; se muestra el último pronóstico guardado."})
                return stale
            return {
                "status": "unavailable",
                "applied": False,
                "message": "El proveedor climático no está disponible; la predicción continúa sin clima.",
            }

    def _latest_stale(self, latitude: float, longitude: float) -> dict | None:
        prefix = f"{latitude:.5f}:{longitude:.5f}:"
        with self.inbox._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM ejixhole_weather_cache WHERE cache_key LIKE ? ORDER BY fetched_at DESC LIMIT 1",
                (f"{prefix}%",),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None
