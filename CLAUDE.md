# CLAUDE.md — MH-Core / MindHigh

Contexto persistente para Claude Code en este repo. Es el más grande y con más piezas de los 4 — léelo completo.

## Qué es esto

`mh_core/` es el "cerebro" del ecosistema MH (compartido, sin conocer detalles de ninguna app específica). `apps/mindhigh/` es MindHigh, la app que genera contenido de video automatizado usando ese cerebro. `apps/ejixhole/` existe como carpeta pero está vacía — no hay nada ahí todavía.

**Regla de capas, no la rompas:** `mh_core/` NUNCA importa de `apps/` (rompería la separación cerebro/aplicación — ya pasó una vez por error y se corrigió). `apps/mindhigh/` sí puede importar de `mh_core/`.

## Entorno

- Windows + PowerShell, no bash.
- `$env:PYTHONPATH = "."` antes de `pytest` (no `export`).
- Requiere **FFmpeg instalado en el sistema** (no es dependencia de pip) para el motor de video — `winget install ffmpeg` o similar.
- `pyttsx3` (TTS local/gratis) usa `pywin32`/`comtypes` en Windows — ya está en `requirements.txt`.
- **Cuidado real con rutas en Windows dentro de filtros de FFmpeg**: `\` es carácter de escape en la sintaxis de filtros de FFmpeg (`-vf`) — una ruta real de Windows rompía el render en silencio (`C:\Users\...` se volvía ilegible). Ya arreglado en `apps/mindhigh/video/video_renderer.py` (`_escapar_ruta_para_filtro`) — si tocas ese archivo, no reintroduzcas el bug.

## Comandos reales

```powershell
pip install -r requirements.txt
$env:PYTHONPATH = "."
pytest -q                          # ~180 tests
uvicorn mh_core.app:app --reload
```

Panel visual: `http://localhost:8000/dashboard/panel` (HTML/JS puro, sin build — pide una API key la primera vez).

## Autenticación — deny-by-default real

Toda ruta requiere el header `X-API-Key` (`mh_core/core/auth.py`), **falla cerrado**: si `MH_CORE_API_KEY` no está configurada, la app rechaza todo por defecto, nunca deja pasar. La única ruta pública es `/` (liveness check mínimo). El panel HTML en sí (`/dashboard/panel`) también es público — pide la key vía JS y la manda en cada `fetch()` después.

## Arquitectura real (no la inventes de nuevo — ya existe)

```
mh_core/engines/       ResearchEngine, MemoryEngine, AutomationEngine, ScoringEngine, DecisionEngine, PredictionEngine...
mh_core/agents/          BaseAgent, ResearchAgent, AgentManager (patrón: name() + run())
mh_core/core/            orchestrator.py (Orchestrator central), auth.py, rate_limiter.py, config.py
mh_core/database/        repositorios JSON reales (patrón: abstracto + JsonXRepository)
mh_core/notifications/   NotificationCenter, reglas configurables, adaptadores (solo LogNotificationAdapter real hoy)
mh_core/memory/          VectorMemoryStore (TF-IDF + coseno, Python puro, sin numpy/sklearn)

apps/mindhigh/services/   ContentGenerator (plantillas), GeminiContentGenerator, GroqContentGenerator,
                            AIContentGenerator (cadena Gemini->Groq->plantillas), QualityEngine, PromptManager
apps/mindhigh/video/       TTSEngine (pyttsx3), VideoRenderer (FFmpeg real), VideoProductionEngine
apps/mindhigh/agents/       ContentAgent, VideoAgent (viven aquí, NO en mh_core/agents, por la regla de capas)
apps/mindhigh/database/     JsonContentVersionRepository, JsonVideoRenderRepository, JsonRunRepository, JsonMetricsRepository
```

## Convenciones reales — patrones ya establecidos, síguelos

- **Repositorio abstracto + implementación JSON**, siempre el mismo patrón: `XRepository(ABC)` con métodos abstractos, `JsonXRepository` que implementa con manejo real de archivo corrupto (respalda antes de tratar como vacío, nunca pierde datos en silencio) y lock de threading si hay escritura concurrente real.
- **Nunca inventes datos.** Si no hay `YOUTUBE_API_KEY`/`GEMINI_API_KEY`/`GROQ_API_KEY` configurada, el sistema cae a un fallback honesto (tema fijo, plantillas) y lo registra en el log — nunca simula una respuesta de IA real.
- **Todo lo inyectable, para tests sin red real.** Cada motor/servicio acepta sus dependencias por constructor con default real (`self.x = x or XReal()`) — los tests inyectan dobles/fakes, nunca llaman a Gemini/Groq/YouTube de verdad.
- **Reintentos con backoff real** (`mh_core/utils/retry.py`) en las 3 llamadas a APIs externas (YouTube, Gemini, Groq) — protege la cuota gratis de un 429 momentáneo.
- **Rate limiting real** (`mh_core/utils/rate_limit_dependency.py`) en los endpoints que gastan cuota — 10 llamadas/5min.
- **GET nunca dispara trabajo con efecto real** (ver `/research/*` — se cambiaron de GET a POST porque un bot/prefetcher podía gastar cuota sin que nadie lo pidiera). Si agregas una ruta nueva que llama a una API externa o escribe algo, que sea POST.
- **Quality Engine es heurístico, no otra llamada a IA** — evaluar con Gemini/Groq lo que Gemini/Groq ya generó duplicaría el gasto de cuota gratis. Es una decisión de presupuesto real, no un atajo técnico.
- **Video Production Engine solo renderiza contenido con `status == "aprobado"`** (por Quality Engine) — nunca lo saltes aunque parezca conveniente para un test rápido.
- Sin numpy/sklearn/moviepy — todo lo matemático (TF-IDF, similitud coseno) está en Python puro a propósito, dado el volumen real de datos de este proyecto.

## Reglas de trabajo — las más importantes de este repo

1. **Antes de crear un archivo nuevo, busca si ya existe uno con ese propósito.** Este repo tuvo varios incidentes reales de duplicar un motor/repositorio que ya existía porque no se auditó primero — reconciliar después cuesta mucho más que buscar antes.
2. Corre `pytest -q` completo (no solo el archivo tocado) después de cualquier cambio.
3. Si algo usa `threading`/procesos reales (Automation Engine, Video Production Engine), prueba el suite completo varias veces seguidas antes de dar por bueno un fix de concurrencia — ya hubo tests intermitentes reales por una condición de carrera en un repositorio JSON que no tenía lock.
4. Nunca borres un archivo sin confirmar primero que nada más lo importa (`grep -rn` real, no suposición).
