# Integración con MH-Knowledge

MH-Core consume conocimiento empresarial mediante un archivo `approved-bundle.json` generado por el CI privado de `MH-Knowledge`.

## Frontera de seguridad

- El bundle contiene únicamente documentos aprobados y vigentes.
- Cada documento conserva su `citation_id`, versión, fuente y checksum.
- MH-Core rechaza rutas de `drafts/`, citas duplicadas, gobierno permisivo y contenido alterado.
- Si no existe un bundle válido, el comportamiento es `POR CONFIRMAR`.
- Precios, disponibilidad, horarios y promociones continúan dependiendo del backend o de aprobación humana.

## Configuración

```env
MH_KNOWLEDGE_BUNDLE_PATH=/ruta/privada/approved-bundle.json
```

El archivo puede reemplazarse por una versión nueva. El servicio detecta su fecha de modificación y recarga el contenido validado sin reiniciar el proceso.

## Uso interno en Python

```python
from mh_core.knowledge.knowledge_engine import KnowledgeEngine

engine = KnowledgeEngine()
engine.load_governed_bundle("approved-bundle.json")

context = engine.get_governed_context("camping capacidad", limit=3)
for document in context["documents"]:
    print(document["citation_id"], document["content"])
```

## API protegida

Las rutas requieren el scope `knowledge.read`. Actualmente lo tienen `mindhigh-worker` y `operations`; `ejixhole-backend` no lo tiene.

```text
GET /knowledge/status
GET /knowledge/search?q=camping&category=sales&limit=3
```

La búsqueda devuelve la versión del conocimiento, el comportamiento para hechos desconocidos y los documentos coincidentes con sus citas. Cuando el bundle no está configurado o es inválido, la búsqueda responde `503` sin exponer detalles internos.

## Contrato de despliegue

1. `MH-Knowledge` valida aprobación, vigencia, fuentes y checksums.
2. Su workflow genera `governance-output/approved-bundle.json`.
3. El bundle se entrega al entorno de MH-Core como archivo de configuración privado.
4. MH-Core lo valida nuevamente antes de usarlo.
5. MindHigh consulta la API con su identidad de servicio y conserva los `citation_id`.

No se requiere que MH-Core tenga acceso de lectura al repositorio completo ni que almacene credenciales de GitHub en el código.
