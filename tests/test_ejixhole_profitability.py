from datetime import date

from mh_core.integrations.ejixhole_events import SqliteEjixholeEventInbox
from mh_core.integrations.ejixhole_profitability import EjixholeProfitabilityService


def test_sin_eventos_reporta_costos_faltantes_sin_inventar_margen(tmp_path):
    inbox = SqliteEjixholeEventInbox(tmp_path / "events.sqlite3")

    result = EjixholeProfitabilityService(inbox).build(date(2026, 7, 18), days=30)

    assert result["total_net_revenue"] == "0.00"
    assert result["services"] == []
    assert result["costs_available"] is False
    assert "márgenes no se calculan" in result["message"]


def test_valida_rango_de_periodo(tmp_path):
    inbox = SqliteEjixholeEventInbox(tmp_path / "events.sqlite3")
    service = EjixholeProfitabilityService(inbox)

    try:
        service.build(date(2026, 7, 18), days=0)
    except ValueError as exc:
        assert "entre 1 y 365" in str(exc)
    else:
        raise AssertionError("Debió rechazar un periodo inválido")
