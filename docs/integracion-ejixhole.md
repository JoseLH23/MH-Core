# Integración MH-Core con EjiXhole

MH-Core consulta el contrato agregado de EjiXhole bajo `/api/v1/integrations/mh-core/operational-summary` y envía la cabecera `X-MH-Service-Key`.

La ruta privada disponible en MH-Core es `GET /integrations/ejixhole/summary` y continúa protegida por `X-API-Key`.

## Garantías

- acceso de solo lectura;
- sin conexión directa a PostgreSQL;
- sin cookies administrativas;
- sin nombres, correos, teléfonos ni folios individuales;
- contrato validado antes de utilizarse;
- rechazo si EjiXhole no confirma API v1;
- timeout configurable;
- errores externos traducidos sin filtrar secretos.

## Variables necesarias

- `EJIXHOLE_API_BASE_URL`: URL del backend EjiXhole sin `/api/v1`.
- `EJIXHOLE_SERVICE_KEY`: misma clave configurada como `MH_CORE_SERVICE_KEY` en EjiXhole.
- `EJIXHOLE_TIMEOUT_SECONDS`: tiempo máximo de espera, predeterminado en 10 segundos.

`EJIXHOLE_SERVICE_KEY` debe ser distinta de `MH_CORE_API_KEY`.
