# Runbook — Recuperación del estado local de MH-Core

## Alcance actual

MH-Core todavía conserva parte de su estado en archivos locales. Este procedimiento reduce el riesgo mientras la persistencia crítica migra a PostgreSQL y una cola de trabajos.

No convierte el diseño actual en multiworker ni sustituye esa migración.

## Objetivos temporales

- **RPO:** 24 horas.
- **RTO:** 4 horas.
- Snapshots diarios fuera del servidor que ejecuta MH-Core.
- Simulacro mensual de verificación y restauración aislada.

## Crear snapshot

```powershell
python scripts/local_state_snapshot.py create `
  --output backups/mh-core-state.tar.gz
```

Por defecto incluye, cuando existen:

- `mh_core/database`;
- `apps/mindhigh/database`;
- `data`;
- `logs`.

Excluye archivos `.env`, bytecode, cachés y metadatos Git.

También se pueden indicar fuentes explícitas:

```powershell
python scripts/local_state_snapshot.py create `
  --source mh_core/database `
  --source apps/mindhigh/database `
  --output backups/mh-core-state.tar.gz
```

## Verificar snapshot

```powershell
python scripts/local_state_snapshot.py verify `
  --snapshot backups/mh-core-state.tar.gz
```

La validación comprueba:

- manifiesto interno;
- lista exacta de archivos;
- tamaños;
- checksums SHA-256;
- rutas seguras sin traversal.

## Restaurar de forma aislada

```powershell
python scripts/local_state_snapshot.py restore `
  --snapshot backups/mh-core-state.tar.gz `
  --target temp/mh-core-restore
```

El destino debe estar vacío. `--overwrite` solo debe utilizarse después de revisar manualmente su contenido.

## Simulacro mensual

1. seleccionar un snapshot reciente;
2. verificar su integridad;
3. restaurarlo en una carpeta temporal;
4. iniciar MH-Core apuntando a copias aisladas o ejecutar tests de repositorios;
5. confirmar que memoria, historial y ejecuciones pueden leerse;
6. registrar duración y errores;
7. eliminar el entorno temporal.

## Incidente real

1. detener automatizaciones y workers;
2. conservar una copia del estado dañado;
3. identificar el último snapshot válido;
4. verificarlo antes de extraer;
5. restaurar primero en una ubicación aislada;
6. comparar contenido y versión de aplicación;
7. reemplazar el estado únicamente con aprobación del propietario;
8. ejecutar pruebas y health checks;
9. documentar el intervalo de información posiblemente perdido.

## Retención temporal recomendada

- 7 snapshots diarios;
- 4 semanales;
- 3 mensuales;
- cifrado en reposo;
- una copia en ubicación independiente.

## Fin de vida

Cuando el estado crítico esté en PostgreSQL y la ejecución en una cola duradera, este procedimiento quedará limitado a archivos no críticos y exportaciones. La recuperación principal deberá usar el runbook de la plataforma de datos.
