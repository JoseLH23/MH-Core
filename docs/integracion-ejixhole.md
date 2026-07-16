# Integración MH-Core con EjiXhole

La integración tiene dos canales separados y con credenciales distintas.

## Consulta agregada de solo lectura

MH-Core consulta el contrato agregado de EjiXhole bajo `/api/v1/integrations/mh-core/operational-summary` y envía la cabecera `X-MH-Service-Key`.

La ruta privada disponible en MH-Core es `GET /integrations/ejixhole/summary` y continúa protegida por `X-API-Key`.

Garantías:

- acceso de solo lectura;
- sin conexión directa a PostgreSQL;
- sin cookies administrativas;
- sin nombres, correos, teléfonos ni folios individuales;
- contrato validado antes de utilizarse;
- rechazo si EjiXhole no confirma API v1;
- timeout configurable;
- errores externos traducidos sin filtrar secretos.

Variables:

- `EJIXHOLE_API_BASE_URL`: URL del backend EjiXhole sin `/api/v1`.
- `EJIXHOLE_SERVICE_KEY`: misma clave configurada como `MH_CORE_SERVICE_KEY` en EjiXhole.
- `EJIXHOLE_TIMEOUT_SECONDS`: tiempo máximo de espera, predeterminado en 10 segundos.

## Recepción de eventos de dominio

EjiXhole publica eventos mediante `POST /integrations/ejixhole/events`. Esta ruta no usa la API key humana: exige firma HMAC SHA-256, identificador UUID y timestamp con ventana corta.

Cabeceras obligatorias:

- `X-MH-Event-Id`;
- `X-MH-Event-Timestamp`;
- `X-MH-Event-Signature`, con formato `sha256=<hex>`.

La firma cubre exactamente `timestamp + "." + cuerpo`. El cuerpo usa JSON canónico y el contrato `v1`.

Eventos aceptados:

- `reservation.created`;
- `reservation.confirmed`;
- `payment.recorded`;
- `reservation.cancelled`;
- `visit.completed`.

Cada payload es estricto y rechaza campos adicionales, evitando que nombres, correos, teléfonos, notas o referencias privadas entren accidentalmente a MH-Core.

La bandeja de entrada SQLite aplica transacciones `BEGIN IMMEDIATE`, claves únicas para `event_id` y `event_key`, WAL y sincronización completa. Un reintento idéntico responde como duplicado; el mismo identificador con otro contenido responde `409`.

Variables:

- `EJIXHOLE_EVENT_SIGNING_SECRET`: misma clave que `MH_CORE_EVENT_SIGNING_SECRET` en el backend EjiXhole.
- `EJIXHOLE_EVENT_MAX_AGE_SECONDS`: ventana anti-replay, predeterminada en 300 segundos.
- `EJIXHOLE_EVENT_INBOX_PATH`: archivo SQLite; en servidor debe vivir dentro de un volumen persistente.

Todas las claves de integración deben ser distintas de `MH_CORE_API_KEY` y nunca guardarse en Git.
