from datetime import date

from mh_core.integrations.ejixhole_events import SqliteEjixholeEventInbox
from mh_core.integrations.ejixhole_weather import EjixholeWeatherService


def _payload():
    return {
        "daily": {
            "time": ["2026-07-18", "2026-07-19"],
            "weather_code": [61, 3],
            "temperature_2m_max": [28.0, 30.0],
            "temperature_2m_min": [20.0, 21.0],
            "precipitation_probability_max": [80, 20],
            "precipitation_sum": [12.5, 0.0],
            "wind_speed_10m_max": [18.0, 14.0],
        }
    }


def test_clima_sin_coordenadas_no_falla(tmp_path, monkeypatch):
    monkeypatch.delenv("EJIXHOLE_LATITUDE", raising=False)
    monkeypatch.delenv("EJIXHOLE_LONGITUDE", raising=False)
    inbox = SqliteEjixholeEventInbox(tmp_path / "events.sqlite3")

    result = EjixholeWeatherService(inbox).forecast(date(2026, 7, 18))

    assert result["status"] == "not_configured"
    assert result["applied"] is False


def test_clima_consulta_y_reutiliza_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("EJIXHOLE_LATITUDE", "22.50")
    monkeypatch.setenv("EJIXHOLE_LONGITUDE", "-99.33")
    calls = []

    def fetch(url, timeout):
        calls.append((url, timeout))
        return _payload()

    inbox = SqliteEjixholeEventInbox(tmp_path / "events.sqlite3")
    service = EjixholeWeatherService(inbox, fetch_json=fetch)

    first = service.forecast(date(2026, 7, 18))
    second = service.forecast(date(2026, 7, 18))

    assert first["status"] == "available"
    assert first["rain_risk_max_percent"] == 80
    assert first["cache"] == "miss"
    assert second["cache"] == "hit"
    assert len(calls) == 1
