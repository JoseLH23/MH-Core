from mh_core.integrations.ejixhole_state_store import ConfiguredEjixholeEventInbox
from mh_core.routes import ejixhole_event_routes


def test_webhook_usa_almacen_configurado():
    assert ejixhole_event_routes.SqliteEjixholeEventInbox is ConfiguredEjixholeEventInbox
