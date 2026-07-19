"""Autenticación servidor-a-servidor con identidad y permisos mínimos."""
from dataclasses import dataclass
import hmac
import os

from fastapi import Depends, Header, HTTPException, Request


@dataclass(frozen=True)
class ServiceIdentity:
    name: str
    scopes: frozenset[str]
    legacy: bool = False


def _service_table() -> dict[str, tuple[str, frozenset[str]]]:
    definitions = {
        "ejixhole-backend": (
            os.environ.get("MH_CORE_EJIXHOLE_KEY", ""),
            frozenset({"core.read", "ejixhole.read", "ejixhole.execute"}),
        ),
        "mindhigh-worker": (
            os.environ.get("MH_CORE_MINDHIGH_KEY", ""),
            frozenset({"core.read", "mindhigh.execute"}),
        ),
        "operations": (
            os.environ.get("MH_CORE_OPERATIONS_KEY", ""),
            frozenset({"core.read", "core.admin", "mindhigh.execute", "ejixhole.execute"}),
        ),
    }
    return {name: value for name, value in definitions.items() if value[0]}


def _revoked() -> set[str]:
    raw = os.environ.get("MH_CORE_REVOKED_SERVICES", "")
    return {item.strip() for item in raw.split(",") if item.strip()}


def _unauthorized(message: str = "Credencial de servicio inválida o faltante.") -> HTTPException:
    return HTTPException(status_code=401, detail=message)


def verificar_api_key(
    request: Request = None,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_service_id: str | None = Header(default=None, alias="X-Service-ID"),
) -> ServiceIdentity:
    services = _service_table()
    if x_service_id:
        if x_service_id in _revoked():
            raise _unauthorized("La identidad de servicio está revocada.")
        configured = services.get(x_service_id)
        if configured is None:
            raise _unauthorized("Identidad de servicio desconocida o no configurada.")
        expected, scopes = configured
        if not x_api_key or not hmac.compare_digest(x_api_key, expected):
            raise _unauthorized()
        identity = ServiceIdentity(name=x_service_id, scopes=scopes)
        if request is not None:
            request.state.service_identity = identity
        return identity

    legacy = os.environ.get("MH_CORE_API_KEY", "")
    allow_legacy = not services or os.environ.get("MH_CORE_ALLOW_LEGACY_API_KEY", "").lower() in {
        "1",
        "true",
        "yes",
    }
    if allow_legacy and legacy:
        if x_api_key and hmac.compare_digest(x_api_key, legacy):
            identity = ServiceIdentity(name="legacy", scopes=frozenset({"*"}), legacy=True)
            if request is not None:
                request.state.service_identity = identity
            return identity
        raise _unauthorized()

    if not services and not legacy:
        raise HTTPException(status_code=503, detail="No hay identidades configuradas; acceso cerrado por defecto.")
    raise _unauthorized("X-Service-ID es obligatorio.")


def requerir_scopes(*required_scopes: str):
    required = frozenset(required_scopes)

    def dependency(identity: ServiceIdentity = Depends(verificar_api_key)) -> ServiceIdentity:
        if "*" not in identity.scopes and not required.issubset(identity.scopes):
            raise HTTPException(status_code=403, detail="La identidad no tiene los permisos requeridos.")
        return identity

    return dependency
