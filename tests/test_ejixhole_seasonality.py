from datetime import date

from mh_core.integrations.ejixhole_events import SqliteEjixholeEventInbox
from mh_core.integrations.ejixhole_seasonality import EjixholeSeasonalityService


def test_sin_historial_no_modifica_prediccion(tmp_path):
    inbox = SqliteEjixholeEventInbox(tmp_path / "events.sqlite3")

    result = EjixholeSeasonalityService(inbox).analyze(date(2026, 7, 18))

    assert result["status"] == "insufficient_data"
    assert result["factor"] == 1.0
    assert result["applied"] is False
    assert result["minimum_comparable_days"] == 8
    assert result["day_type"] == "fin_de_semana"


def test_factor_estacional_siempre_esta_acotado(tmp_path):
    inbox = SqliteEjixholeEventInbox(tmp_path / "events.sqlite3")

    result = EjixholeSeasonalityService(inbox).analyze(date(2026, 7, 13))

    assert 0.80 <= result["factor"] <= 1.20
    assert result["lookback_days"] == 365
