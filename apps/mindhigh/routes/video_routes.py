from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from apps.mindhigh.database.json_content_version_repository import JsonContentVersionRepository
from apps.mindhigh.video.video_production_engine import VideoProductionEngine
from mh_core.core.config import DATABASE_DIR
from mh_core.utils.rate_limit_dependency import limitar_generacion_ia

router = APIRouter(prefix="/mindhigh/video", tags=["Video Production"])

_engine = VideoProductionEngine()
_content_repo = JsonContentVersionRepository(DATABASE_DIR / "mindhigh" / "content_versions.json")


@router.post("/render/{content_id}", dependencies=[Depends(limitar_generacion_ia)])
def iniciar_render(content_id: str):
    contenido = _content_repo.obtener_por_id(content_id)
    if contenido is None:
        raise HTTPException(status_code=404, detail=f"Contenido '{content_id}' no encontrado.")
    if contenido.status != "aprobado":
        raise HTTPException(
            status_code=400,
            detail=f"Solo se puede renderizar contenido aprobado por Quality Engine (status actual: '{contenido.status}').",
        )
    # No bloquea la respuesta — el render real corre en un hilo de
    # fondo (VideoProductionEngine.iniciar_render); el estado se
    # consulta con GET /renders/{id}.
    render = _engine.iniciar_render(content_id, contenido.title, contenido.script)
    return render.model_dump()


@router.get("/renders")
def listar(limit: int = 20):
    return {"renders": [r.model_dump() for r in _engine.repository.listar(limit=limit)]}


@router.get("/renders/{render_id}")
def obtener(render_id: str):
    render = _engine.repository.obtener_por_id(render_id)
    if render is None:
        raise HTTPException(status_code=404, detail="Render no encontrado.")
    return render.model_dump()


@router.get("/renders/{render_id}/file")
def descargar(render_id: str):
    render = _engine.repository.obtener_por_id(render_id)
    if render is None or render.status != "completed" or not render.file_path:
        raise HTTPException(status_code=404, detail="Este render no tiene un archivo listo todavía.")
    ruta = Path(render.file_path)
    if not ruta.exists():
        raise HTTPException(status_code=404, detail="El archivo del render ya no existe en disco.")
    return FileResponse(ruta, media_type="video/mp4", filename=ruta.name)


@router.post("/renders/{render_id}/cancel")
def cancelar(render_id: str):
    try:
        render = _engine.cancelar(render_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return render.model_dump()


@router.post("/renders/{render_id}/retry")
def reintentar(render_id: str):
    try:
        render = _engine.reintentar(render_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return render.model_dump()
