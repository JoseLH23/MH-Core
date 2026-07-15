# CLAUDE.md — MH-Core / MindHigh

Contexto persistente para Claude Code en este repo. Es el más grande y con más piezas de los 4 — léelo completo.

## Misión actual — fuente de verdad

`mh_core/` es el cerebro privado del ecosistema MH. `apps/mindhigh/` es el departamento personal de marketing de EjiXhole.

La prioridad actual **NO** es producir videos de temas random, monetizar contenido genérico ni convertir MindHigh en un producto público. La misión es:

> Generar un flujo constante de clientes para EjiXhole durante todo el año, reducir el trabajo repetitivo de publicidad y ayudar a convertir interés en reservaciones.

MindHigh debe preparar campañas, textos, imágenes, carruseles, historias, estados de WhatsApp, ideas, calendario y análisis. El video es una herramienta opcional, no el centro del producto. Toda publicación automática requiere aprobación humana por ahora.

El plan rector completo vive en el repositorio privado `MH-Ecosystem`, documento `MH_ECOSYSTEM_MASTER_PLAN_V2.md`. Si una instrucción antigua contradice ese plan, gana el plan v2.

## Regla de capas — no la rompas

`mh_core/` NUNCA importa de `apps/`. `apps/mindhigh/` sí puede importar de `mh_core/`. `apps/ejixhole/` será la integración empresarial cuando corresponda; no inventes módulos vacíos ni acoplamientos prematuros.

## Criterio de prioridad

Antes de agregar una función, pregunta:

1. ¿Ayuda a conseguir más clientes para EjiXhole?
2. ¿Reduce trabajo repetitivo del propietario o del personal?
3. ¿Mejora la experiencia o conversión del visitante?
4. ¿Hace el ecosistema más estable, profesional o valioso?

Si no cumple al menos una, no es prioridad actual.

## Entorno

- Windows + PowerShell, no bash.
- `$env:PYTHONPATH = "."` antes de `pytest`.
- FFmpeg es una dependencia del sistema para el módulo de video, no de pip.
- `pyttsx3` usa `pywin32`/`comtypes` en Windows.
- En filtros FFmpeg, las rutas Windows requieren escape especial. Ya existe `_escapar_ruta_para_filtro` en `apps/mindhigh/video/video_renderer.py`; no reintroduzcas el bug.

## Comandos reales

```powershell
pip install -r requirements.txt
$env:PYTHONPATH = "."
pytest -q
uvicorn mh_core.app:app --reload
```

Panel: `http://localhost:8000/dashboard/panel`.

## Autenticación — deny-by-default

Los routers operativos requieren `X-API-Key` mediante `mh_core/core/auth.py` y fallan cerrado cuando `MH_CORE_API_KEY` no está configurada.

Rutas deliberadamente públicas hoy:

- `/` — liveness mínimo.
- `/dashboard/panel` — solo entrega el HTML; los datos requieren API key.
- `/docs`, `/redoc` y `/openapi.json` siguen públicos por defecto de FastAPI; es deuda de seguridad conocida para cerrar antes de exponer MH-Core fuera de una red privada.

El panel guarda la key en `sessionStorage`, no `localStorage`. La descarga de video con `window.open()` no puede enviar `X-API-Key`; es un bug funcional conocido pendiente de reemplazar por `fetchAutenticado + Blob`. No debilites la autenticación para resolverlo.

## Arquitectura real

```text
mh_core/engines/       Research, Memory, Automation, Scoring, Decision, Prediction
mh_core/agents/        BaseAgent, ResearchAgent, AgentManager
mh_core/core/          orchestrator.py, auth.py, rate_limiter.py, config.py
mh_core/database/      repositorios JSON
mh_core/notifications/ NotificationCenter y adaptadores
mh_core/memory/        VectorMemoryStore

apps/mindhigh/services/ generación de contenido, proveedores IA, calidad y prompts
apps/mindhigh/video/    TTS, FFmpeg y producción de video opcional
apps/mindhigh/agents/   agentes específicos de MindHigh
apps/mindhigh/database/ repositorios de contenido, renders, runs y métricas
```

## Dirección funcional de MindHigh

Priorizar gradualmente:

- biblioteca de conocimiento real de EjiXhole;
- biblioteca de fotografías y campañas anteriores;
- generador de textos por canal;
- generador y selección de imágenes;
- campañas completas con objetivo, CTA y variaciones;
- calendario continuo de publicaciones;
- clasificación por familia, pareja, camping, hospedaje, aventura y temporada;
- registro de alcance, mensajes, compartidos y reservaciones atribuidas;
- recomendaciones basadas en ocupación y resultados;
- respuestas sugeridas para preguntas frecuentes;
- aprobación humana antes de publicar.

No priorizar por ahora:

- videos random de nichos ajenos a EjiXhole;
- publicación autónoma sin aprobación;
- vender MindHigh o MH-Core a terceros;
- arquitectura multiempresa/multitenant;
- funciones llamativas sin impacto en clientes, operación o estabilidad.

## Convenciones técnicas

- Repositorio abstracto + implementación JSON, con respaldo ante corrupción y lock si hay escritura concurrente.
- Nunca inventes datos ni presentes fallback como IA real.
- Dependencias inyectables para pruebas sin red.
- Reintentos con backoff en APIs externas.
- Rate limiting en endpoints que gastan cuota.
- GET nunca dispara trabajo con efectos; usa POST.
- Quality Engine heurístico para no duplicar gasto de IA.
- Video Production solo renderiza contenido aprobado.
- Mantén dependencias ligeras mientras el volumen real no justifique otras.

## Reglas de trabajo

1. Antes de crear algo, busca si ya existe una pieza con ese propósito.
2. Un cambio por rama/PR; no trabajar directamente en `main`.
3. Corre `pytest -q` completo después de cada cambio.
4. Para threading/procesos, ejecuta la suite varias veces y prueba concurrencia.
5. Nunca borres archivos sin confirmar referencias.
6. Cambios que afecten API, headers o contratos deben revisarse contra los repos consumidores.
7. No marques algo como terminado solo porque compila: exige prueba funcional del flujo real.
8. Mantén actualizado este archivo y el Master Plan cuando cambie una decisión de producto.
