# Contribuir a MH-Core

## Flujo

1. Crear una rama desde `main`.
2. Mantener un objetivo principal por cambio.
3. Separar capacidades reutilizables de la lógica de MindHigh.
4. Añadir o actualizar pruebas con dobles y carpetas temporales.
5. Ejecutar pruebas e importar la aplicación.
6. Abrir un pull request usando la plantilla.
7. Verificar límites, fallbacks y comportamiento externo.

## Ramas

- `feat/...` para funciones.
- `fix/...` para correcciones.
- `security/...` para endurecimiento.
- `docs/...` para documentación.
- `cto/...` para bloques coordinados del roadmap.

## Reglas

- Las pruebas deben ser aisladas y repetibles.
- Los resultados simulados deben identificarse claramente.
- Las acciones externas conservan aprobación humana.
- MH-Core se integra mediante APIs y eventos; no mediante acceso directo a bases privadas.
- Los procesos largos deben ser reanudables, observables e idempotentes.
- Toda integración debe tener límites de costo, tiempo y reintentos.

## Comandos mínimos

```powershell
$env:PYTHONPATH = "."
pytest -q
python -c "import mh_core.app; print('ok')"
```
