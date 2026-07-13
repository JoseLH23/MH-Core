from fastapi import APIRouter, HTTPException

from mh_core.notifications.notification_center import NotificationCenter

router = APIRouter(prefix="/notifications", tags=["Notifications"])

_center = NotificationCenter()


@router.get("")
def listar(solo_no_leidas: bool = False):
    return {"notifications": [n.model_dump() for n in _center.listar(solo_no_leidas=solo_no_leidas)]}


@router.get("/{notification_id}")
def obtener(notification_id: str):
    notificacion = _center.obtener(notification_id)
    if notificacion is None:
        raise HTTPException(status_code=404, detail="Notificación no encontrada.")
    return notificacion.model_dump()


@router.post("/{notification_id}/read")
def marcar_leida(notification_id: str):
    notificacion = _center.marcar_leida(notification_id)
    if notificacion is None:
        raise HTTPException(status_code=404, detail="Notificación no encontrada.")
    return notificacion.model_dump()
