# AGENTS.md — MH-Core

## Propósito

MH-Core es una plataforma modular de inteligencia de decisión. Actualmente investiga oportunidades de YouTube, genera decisiones y reportes, mantiene memoria local y soporta el flujo de MindHigh: generación de contenido, evaluación, publicación simulada, métricas, notificaciones y video.

Los módulos documentados pero no implementados están **por confirmar**.

## Estructura principal

- `mh_core/`: núcleo reutilizable y aplicación FastAPI.
  - `app.py`: composición y registro de routers.
  - `core/`: autenticación, configuración, rate limiting y orquestación.
  - `engines/`: investigación, scoring, ranking, patrones, decisión, memoria, predicción y automatización.
  - `services/`, `routes/`, `agents/`: servicios, API y agentes compartidos.
  - `database/`: contratos y repositorios JSON.
  - `brain/`, `memory/`, `knowledge/`, `notifications/`, `plugins/`: capacidades del núcleo.
  - `dashboard/`: API de estado y panel web.
- `apps/mindhigh/`: lógica específica de MindHigh.
  - `services/`: generación, prompts y calidad.
  - `engines/`: métricas y rendimiento.
  - `agents/`, `publishing/`, `video/`, `routes/`, `database/`: agentes, publicación, video, API y persistencia.
  - `mindhigh_pipeline.py`: flujo simple.
  - `mindhigh_orchestrator.py`: flujo observable y reanudable.
- `tests/`: suite pytest.
- `docs/`: documentación del proyecto; puede incluir contenido aspiracional.
- `.github/workflows/tests.yml`: CI con Python 3.11.

Los directorios raíz `config/`, `core/`, `database/`, `scripts/` y `shared/` están vacíos. Su uso está **por confirmar**.

## Comandos

### Instalar dependencias

Comando verificado en CI:

```powershell
pip install -r requirements.txt
```

### Ejecutar la aplicación

Entrypoint ASGI verificado:

```text
mh_core.app:app
```

No existe un comando oficial de arranque versionado. El siguiente está **por confirmar** como comando canónico:

```powershell
python -m uvicorn mh_core.app:app
```

Las rutas protegidas requieren `MH_CORE_API_KEY`.

### Ejecutar pruebas

Comando verificado en CI:

```powershell
$env:PYTHONPATH = "."
pytest -q
```

Comprobación de importación usada por CI:

```powershell
python -c "import mh_core.app; print('mh_core.app importa correctamente')"
```

No ejecutes pruebas con credenciales reales de YouTube, Gemini o Groq disponibles. Prefiere dobles y rutas temporales.

## Reglas de arquitectura

1. `mh_core` contiene capacidades compartidas; `apps/mindhigh` contiene lógica específica de MindHigh.
2. El núcleo no debe depender de módulos de aplicación, excepto `mh_core/app.py` como raíz de composición.
3. Mantén las rutas delgadas; coloca lógica en servicios, engines u orquestadores.
4. Accede a persistencia mediante contratos de repositorio.
5. No agregues lectura o escritura directa de JSON fuera de la capa de persistencia correspondiente.
6. Las integraciones externas deben ser inyectables y sustituibles por dobles.
7. Usa modelos Pydantic o contratos tipados entre capas.
8. Conserva la separación explícita entre datos reales y simulados.
9. No presentes plantillas, métricas o publicaciones simuladas como reales.
10. No hagas llamadas de red, inicies TTS o arranques hilos durante la importación.
11. Reutiliza pasos compartidos; evita duplicar lógica entre pipelines y orquestadores.
12. Las operaciones con efectos secundarios o consumo externo deben usar `POST` o jobs.
13. No cambies fórmulas, scores o umbrales sin pruebas y una decisión explícita.
14. No asumas soporte multiworker: los repositorios, límites y schedulers actuales son locales al proceso.

## Reglas de seguridad

1. Toda ruta de datos nueva debe quedar protegida por `verificar_api_key`.
2. Mantén el fallo cerrado cuando `MH_CORE_API_KEY` no esté configurada.
3. Nunca devuelvas excepciones internas completas en respuestas HTTP.
4. Aplica rate limiting a operaciones costosas, proveedores externos y render.
5. Nunca llames proveedores reales desde pruebas.
6. `SimulatedPublisher` debe seguir siendo el publicador predeterminado.
7. Una publicación o mensaje externo real requiere autorización explícita.
8. Trata títulos, mensajes, respuestas LLM, errores y rutas como datos no confiables.
9. No insertes datos externos directamente mediante `innerHTML`.
10. Restringe descargas y archivos generados a directorios autorizados.
11. Nunca registres, muestres o versiones API keys, tokens o secretos.
12. No expongas el servidor públicamente ni habilites varios workers sin revisión explícita.

## Archivos que no se deben modificar ni versionar

No modifiques ni versiones:

- `.env` ni otros archivos con credenciales reales.
- `venv/` o `.venv/`.
- `__pycache__/`, `*.pyc` o `.pytest_cache/`.
- `logs/`, `temp/` o `*.log`.
- `.vscode/`, `.idea/`, `.DS_Store` o `Thumbs.db`.
- Archivos cuyo nombre contenga `credentials` o `secret`.
- `mh_core/database/learning/history.json`.
- Datos JSON generados durante pruebas o ejecuciones, salvo que la tarea los incluya explícitamente.

No alteres archivos JSON versionados como efecto secundario de pruebas. No borres ni reviertas cambios existentes del usuario.

El tratamiento futuro de `mh_core/database/mindhigh/`, `mh_core/database/notifications/` y `mh_core/database/knowledge/` está **por confirmar**.

## Definición de tarea terminada

Una tarea está terminada cuando:

1. El comportamiento solicitado está implementado sin cambios fuera de alcance.
2. Se respetan las fronteras entre núcleo, aplicación, servicios y persistencia.
3. No se introdujeron secretos, datos reales ni efectos externos accidentales.
4. Los errores HTTP no exponen detalles internos.
5. Se agregaron o actualizaron pruebas relevantes.
6. Las pruebas ejecutadas fueron aisladas y se reporta exactamente cuáles corrieron.
7. Si no fue seguro ejecutar la suite completa, se explica claramente.
8. No hubo errores de colección o pruebas omitidas sin explicación.
9. Las dependencias nuevas están justificadas y fijadas.
10. Los cambios de configuración se reflejan en `.env.example` sin secretos.
11. `git status --short` muestra únicamente cambios intencionales.
12. No se versionaron cachés, logs, entornos virtuales o datos runtime.
13. La documentación afectada coincide con el comportamiento real.
14. No se hizo commit o push salvo solicitud explícita.
