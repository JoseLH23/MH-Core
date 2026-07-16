"""Cliente HTTP de solo lectura para EjiXhole API v1."""
from __future__ import annotations

import os
from urllib.parse import urlparse

import requests
from pydantic import BaseModel, ConfigDict, ValidationError


class EjixholeConfigurationError(RuntimeError):
    pass


class EjixholeUpstreamError(RuntimeError):
    pass


class OperationalMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ingresos_hoy: float
    ingresos_mes: float
    reservaciones_activas: int
    proximas_7_dias: int
    saldo_pendiente_total: float
    tasa_cancelacion_mes: float
    ocupacion_promedio_mes: float
    diferencia_caja_hoy: float


class EjixholeOperationalSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: str
    business_date: str
    source: str
    api_version: str
    access: str
    scope: str
    metrics: OperationalMetrics


class EjixholeClient:
    """Consume exclusivamente el contrato agregado de EjiXhole.

    No conoce PostgreSQL, cookies administrativas ni endpoints de escritura.
    """

    def __init__(
        self,
        base_url: str | None = None,
        service_key: str | None = None,
        timeout_seconds: float | None = None,
        session: requests.Session | None = None,
    ):
        self.base_url = self._normalizar_base(
            base_url or os.getenv("EJIXHOLE_API_BASE_URL", "")
        )
        self.service_key = (
            service_key if service_key is not None else os.getenv("EJIXHOLE_SERVICE_KEY", "")
        ).strip()
        if len(self.service_key) < 32:
            raise EjixholeConfigurationError(
                "EJIXHOLE_SERVICE_KEY no está configurada o es demasiado corta."
            )

        timeout_value = timeout_seconds
        if timeout_value is None:
            raw_timeout = os.getenv("EJIXHOLE_TIMEOUT_SECONDS", "10")
            try:
                timeout_value = float(raw_timeout)
            except ValueError as exc:
                raise EjixholeConfigurationError(
                    "EJIXHOLE_TIMEOUT_SECONDS debe ser numérico."
                ) from exc
        if timeout_value <= 0 or timeout_value > 60:
            raise EjixholeConfigurationError(
                "EJIXHOLE_TIMEOUT_SECONDS debe estar entre 0 y 60 segundos."
            )
        self.timeout_seconds = timeout_value
        self.session = session or requests.Session()

    @staticmethod
    def _normalizar_base(base_url: str) -> str:
        base = base_url.strip().rstrip("/")
        if not base:
            raise EjixholeConfigurationError("EJIXHOLE_API_BASE_URL no está configurada.")

        parsed = urlparse(base)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise EjixholeConfigurationError("EJIXHOLE_API_BASE_URL no es una URL HTTP válida.")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise EjixholeConfigurationError(
                "EJIXHOLE_API_BASE_URL no debe incluir credenciales, query ni fragmento."
            )
        return base if base.endswith("/api/v1") else f"{base}/api/v1"

    def operational_summary(self) -> EjixholeOperationalSummary:
        url = f"{self.base_url}/integrations/mh-core/operational-summary"
        try:
            response = self.session.get(
                url,
                headers={
                    "Accept": "application/json",
                    "X-MH-Service-Key": self.service_key,
                },
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise EjixholeUpstreamError("EjiXhole no respondió a tiempo.") from exc

        if response.status_code == 401:
            raise EjixholeUpstreamError("EjiXhole rechazó la credencial de servicio.")
        if response.status_code >= 400:
            raise EjixholeUpstreamError(
                f"EjiXhole devolvió HTTP {response.status_code}."
            )
        if response.headers.get("X-API-Version") != "v1":
            raise EjixholeUpstreamError("EjiXhole no confirmó el contrato API v1.")

        try:
            payload = response.json()
            summary = EjixholeOperationalSummary.model_validate(payload)
        except (ValueError, ValidationError) as exc:
            raise EjixholeUpstreamError("EjiXhole devolvió un contrato inválido.") from exc

        if summary.access != "read_only" or summary.scope != "ejixhole:read:operations":
            raise EjixholeUpstreamError("EjiXhole devolvió un alcance inesperado.")
        return summary
