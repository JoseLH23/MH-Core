# Persistencia durable de MH-Core

## Alcance

La base SQL conserva los trabajos asíncronos y las memorias de `MemoryEngine`.
La bandeja de eventos EjiXhole permanece temporalmente en SQLite porque los
reportes actuales dependen de esa conexión; su migración será un bloque aparte.

## Configuración

Sin `MH_DATABASE_URL`, el sistema usa un archivo SQLite local. Para varias
instancias o un worker separado se configura PostgreSQL mediante esa variable.

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

## Operación segura

Antes de activar PostgreSQL en producción se debe crear un respaldo y detener
workers anteriores. Todos los workers de una misma cola deben usar la misma
base. Retirar temporalmente `MH_DATABASE_URL` devuelve una instancia única al
modo local, pero no exporta automáticamente memorias nuevas desde SQL a JSON.
