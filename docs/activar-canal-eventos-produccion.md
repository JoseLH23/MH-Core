# Activación del canal EjiXhole → MH-Core en producción

Este procedimiento activa el canal sin compartir bases de datos ni claves humanas.

## 1. Preparar MH-Core

Configura en el servicio web:

```text
EJIXHOLE_EVENT_SIGNING_SECRET=<secreto aleatorio de 48+ caracteres>
EJIXHOLE_EVENT_MAX_AGE_SECONDS=300
EJIXHOLE_EVENT_INBOX_PATH=/var/data/ejixhole_events.sqlite3
```

Monta un volumen persistente en `/var/data`. La ruta debe sobrevivir reinicios y despliegues; no uses el sistema de archivos efímero del contenedor.

Después del despliegue, valida con la API key privada de MH-Core:

```text
GET /integrations/ejixhole/events/status
X-API-Key: <MH_CORE_API_KEY>
```

El resultado esperado antes de la primera entrega es:

- `configured: true`;
- `custom_storage_path_configured: true`;
- `journal_mode: wal`.

## 2. Preparar EjiXhole

En el backend y en el proceso worker configura el mismo acceso a PostgreSQL. En el worker agrega:

```text
MH_CORE_EVENTS_URL=https://<host-mh-core>/integrations/ejixhole/events
MH_CORE_EVENT_SIGNING_SECRET=<mismo secreto del paso 1>
OUTBOX_BATCH_SIZE=10
OUTBOX_MAX_ATTEMPTS=8
OUTBOX_LEASE_SECONDS=120
OUTBOX_INITIAL_BACKOFF_SECONDS=10
OUTBOX_MAX_BACKOFF_SECONDS=3600
OUTBOX_REQUEST_TIMEOUT_SECONDS=10
OUTBOX_POLL_INTERVAL_SECONDS=10
```

El comando del proceso persistente es:

```text
python -m app.workers.outbox_publisher
```

No lo ejecutes dentro del mismo proceso de Uvicorn. El servidor HTTP y el worker deben reiniciarse y escalar por separado.

## 3. Validación controlada

1. Aplica las migraciones del backend.
2. Crea desde el portal una reservación marcada `PILOTO CANAL MH — NO CONTACTAR`.
3. Consulta en EjiXhole el UUID del evento más reciente.
4. Espera hasta que el evento quede `published`.
5. Consulta en MH-Core:

```text
GET /integrations/ejixhole/events/<event_id>
X-API-Key: <MH_CORE_API_KEY>
```

La respuesta debe tener el mismo UUID y `unique_record: true`. No devuelve payload ni datos personales.

## 4. Criterio de aprobación

El canal queda aprobado únicamente cuando:

- el worker permanece ejecutándose;
- el outbox cambia de `pending` a `published`;
- MH-Core registra exactamente una fila;
- reenviar el mismo evento no crea otra fila;
- no hay eventos `dead_letter` nuevos;
- el archivo SQLite está dentro del volumen persistente.

Nunca pegues los secretos en issues, logs, comandos compartidos o capturas.
