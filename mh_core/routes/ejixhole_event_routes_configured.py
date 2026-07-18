"""Compatibilidad del webhook existente con el almacén EjiXhole configurable."""
from mh_core.integrations import ejixhole_event_status
from mh_core.integrations.ejixhole_state_store import ConfiguredEjixholeEventInbox
from mh_core.routes import ejixhole_event_routes as existing_routes

# Los endpoints conservan exactamente su autenticación y contrato. Solo se
# sustituye la implementación de almacenamiento usada en tiempo de ejecución.
ejixhole_event_status.SqliteEjixholeEventInbox = ConfiguredEjixholeEventInbox
existing_routes.SqliteEjixholeEventInbox = ConfiguredEjixholeEventInbox

router = existing_routes.router
