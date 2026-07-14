# MH-Core

Núcleo modular de inteligencia y automatización del ecosistema MH.

MH-Core investiga oportunidades, procesa señales, genera decisiones y
reportes, mantiene memoria local y coordina el flujo supervisado de
MindHigh para crear, evaluar y preparar contenido.

## Estado

Proyecto en **desarrollo activo**.

El núcleo ya cuenta con API protegida, motores de investigación y decisión,
orquestación, agentes, automatización, memoria local y un flujo funcional de
MindHigh. La publicación real permanece desactivada por seguridad; el
publicador predeterminado es simulado.

## Tecnologías

- Python 3.11
- FastAPI
- Uvicorn
- Pydantic 2
- Pytest
- Requests y HTTPX
- Google GenAI
- pyttsx3

## Capacidades actuales

### MH-Core

- Investigación de oportunidades de YouTube
- Scoring y ranking
- Detección de patrones
- Motor de decisiones
- Predicción y aprendizaje
- Memoria local
- Knowledge Engine
- Orquestador central
- Automation Engine
- Agentes especializados
- Notificaciones
- Dashboard de estado
- API protegida mediante clave

### MindHigh

- Generación de contenido
- Proveedores Gemini y Groq
- Respaldo mediante plantillas
- Evaluación de calidad
- Flujo observable y reanudable
- Producción de video
- Métricas de rendimiento
- Publicación simulada
- Agentes especializados

## Arquitectura

```text
MH-Core/
├── mh_core/
│   ├── agents/         agentes compartidos
│   ├── brain/          generación de reportes ejecutivos
│   ├── core/           autenticación, configuración y orquestación
│   ├── dashboard/      panel y estado del sistema
│   ├── database/       contratos y repositorios locales
│   ├── engines/        investigación, decisión, predicción y automatización
│   ├── knowledge/      conocimiento reutilizable
│   ├── memory/         memoria y aprendizaje
│   ├── notifications/  notificaciones
│   ├── plugins/        integraciones reemplazables
│   ├── routes/         endpoints FastAPI
│   ├── services/       casos de uso compartidos
│   └── app.py          composición de la aplicación
├── apps/
│   └── mindhigh/
│       ├── agents/
│       ├── database/
│       ├── engines/
│       ├── publishing/
│       ├── routes/
│       ├── services/
│       ├── video/
│       ├── mindhigh_pipeline.py
│       └── mindhigh_orchestrator.py
├── tests/
├── docs/
├── AGENTS.md
└── requirements.txt
```

`mh_core` contiene capacidades reutilizables. `apps/mindhigh` contiene la
lógica específica de la aplicación MindHigh.

## Instalación local

```powershell
git clone https://github.com/JoseLH23/MH-Core.git
cd MH-Core

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
Copy-Item .env.example .env
```

## Configuración

Genera una clave segura:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Después colócala en `.env`:

```env
MH_CORE_API_KEY=tu-clave-segura

YOUTUBE_API_KEY=
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.5-flash
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
```

Las claves de YouTube, Gemini y Groq son opcionales. Cuando un proveedor no
está disponible, el sistema utiliza fallbacks explícitos sin inventar datos
ni ocultar que el resultado es simulado.

## Ejecutar la API

```powershell
python -m uvicorn mh_core.app:app --reload
```

Direcciones locales:

- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`
- Liveness público: `http://127.0.0.1:8000/`
- Estado protegido: `http://127.0.0.1:8000/status`

## Autenticación

Las rutas de datos requieren el encabezado:

```text
X-API-Key: tu-clave-segura
```

Ejemplo en PowerShell:

```powershell
$headers = @{ "X-API-Key" = "tu-clave-segura" }
Invoke-RestMethod -Uri "http://127.0.0.1:8000/status" -Headers $headers
```

El servidor falla cerrado: sin `MH_CORE_API_KEY` configurada, las rutas
protegidas no quedan abiertas accidentalmente.

## Pruebas

```powershell
$env:PYTHONPATH = "."
pytest -q
```

Comprobación rápida de importación:

```powershell
python -c "import mh_core.app; print('mh_core.app importa correctamente')"
```

No ejecutes pruebas con credenciales reales de YouTube, Gemini o Groq
disponibles. Las pruebas deben utilizar dobles y directorios temporales.

## Seguridad

- Protección deny-by-default para las rutas de datos
- Rate limiting en operaciones sensibles o costosas
- Fallo cerrado cuando falta la clave principal
- Publicación simulada como comportamiento predeterminado
- Sin efectos externos durante importaciones
- Sin exposición de excepciones internas completas
- Secretos excluidos del repositorio
- Separación explícita entre datos reales y simulados

## Persistencia actual

La persistencia crítica todavía utiliza repositorios locales y archivos JSON.

Antes de operar con varios procesos, múltiples servidores o cargas de
producción, debe migrarse el estado crítico a PostgreSQL y añadirse una cola
de trabajos. El sistema actual no debe asumirse como multiworker.

## Flujo objetivo de MindHigh

```text
investigación
→ oportunidad
→ decisión
→ generación de contenido
→ evaluación de calidad
→ producción de video
→ aprobación humana
→ publicación
→ métricas
→ aprendizaje
```

La aprobación humana debe mantenerse antes de cualquier publicación externa
real.

## Integración futura con EjiXhole

MH-Core se conectará a EjiXhole mediante APIs autenticadas, versionadas y
eventos. No debe acceder directamente a la base de datos operacional de
EjiXhole.

## Próximos objetivos

1. Migrar persistencia crítica de JSON a PostgreSQL.
2. Añadir una cola de trabajos para procesos largos.
3. Consolidar el AI Provider Manager.
4. Registrar costo, latencia, proveedor y calidad por ejecución.
5. Añadir contratos de API versionados.
6. Completar observabilidad y trazabilidad.
7. Mantener publicación real bajo autorización explícita.
8. Conectar EjiXhole solo después de estabilizar ambos sistemas.

## Documentación

- `AGENTS.md`: reglas técnicas y de seguridad para agentes de desarrollo.
- `docs/`: documentación interna y decisiones del proyecto.
- `MH-Ecosystem`: visión, arquitectura y roadmap general del ecosistema.
