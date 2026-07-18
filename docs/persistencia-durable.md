# Persistencia durable de MH-Core

## Alcance

La base SQL conserva trabajos asíncronos, memorias de `MemoryEngine` y, mediante
una configuración separada, el estado analítico de EjiXhole.

## Configuración

Sin `MH_DATABASE_URL`, los jobs usan SQLite local y la memoria conserva JSON.
Para varias instancias o un worker separado se configura PostgreSQL mediante
esa variable.

El canal EjiXhole usa `EJIXHOLE_STATE_DATABASE_URL`. Mientras
`EJIXHOLE_EVENT_INBOX_PATH` tenga valor, continúa usando el SQLite histórico.
Esto permite preparar y verificar la migración antes de cambiar el destino.

## Trabajos

Estados: `pending`, `running`, `retry`, `succeeded`, `dead_letter` y `cancelled`.
PostgreSQL usa bloqueo de fila y `SKIP LOCKED`. Cada claim recibe un lease; un
trabajo abandonado vuelve a `retry` o pasa a `dead_letter`. La pareja de cola y
clave idempotente impide duplicar el mismo trabajo.

El worker se inicia con `python -m mh_core.jobs.worker`. El argumento `--once`
procesa como máximo un trabajo. Inicialmente solo está habilitado el handler
`automation.run_once`; el payload no permite seleccionar código arbitrario.

## Memoria

`MemoryEngine` mantiene su contrato de repositorio. Sin URL SQL usa JSON. Con
`MH_DATABASE_URL` usa `SqlMemoryRepository` y conserva búsqueda, recientes y
deduplicación.

La utilidad `python -m scripts.migrate_memory` hace una vista previa. El
argumento `--apply` copia los recuerdos sin borrar el JSON y puede repetirse sin
duplicarlos.

## Estado analítico EjiXhole

Se conservan en un único destino los eventos recibidos y procesados, el estado
de reservaciones, las predicciones, las decisiones y la caché meteorológica.
PostgreSQL serializa el procesamiento con un advisory lock para mantener el
orden de los eventos incluso con varias instancias.

`python -m scripts.migrate_ejixhole_state` muestra una vista previa. Con
`--apply` copia el SQLite dentro de una transacción y compara conteo y SHA-256
de cada tabla. El origen no se elimina. El cambio de destino se realiza solo
después de que todas las tablas indiquen coincidencia completa.

## Operación segura

Antes de cambiar cualquier destino se crea un respaldo y se detienen procesos
anteriores. Todos los workers e instancias de una misma función deben usar la
misma base. Una reversión de configuración no exporta automáticamente los datos
nuevos desde PostgreSQL hacia los archivos locales.
