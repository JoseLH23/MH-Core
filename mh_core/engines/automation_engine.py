"""
Automation Engine — Fase "Automation Engine" del roadmap.

Dispara el pipeline del Orchestrator solo (programado por intervalo),
sin depender de que alguien llame a un endpoint HTTP. Solo usa la
librería estándar (threading/time) — sin dependencias nuevas, y
funciona igual en Windows/PowerShell que en Linux/Mac (no usa nada
específico de un SO).

Reutiliza ResearchService._run_source() (mismo YouTubePlugin real) y
el Orchestrator ya construido — no duplica la obtención de videos ni
la secuencia de engines.
"""
import threading
import time
from datetime import datetime
from typing import Callable, Optional

from mh_core.core.orchestrator import Orchestrator
from mh_core.notifications.notification_center import NotificationCenter
from mh_core.services.research_service import ResearchService
from mh_core.utils.logger import logger


class AutomationEngine:
    def __init__(
        self,
        orchestrator: Optional[Orchestrator] = None,
        obtener_fuente: Optional[Callable[[], dict]] = None,
        notification_center: Optional[NotificationCenter] = None,
    ):
        # Todos inyectables a propósito — los tests nunca llaman a la
        # API real de YouTube ni tocan archivos reales.
        self.orchestrator = orchestrator or Orchestrator()
        self._obtener_fuente = obtener_fuente or ResearchService._run_source
        self.notification_center = notification_center or NotificationCenter()

        self._hilo: Optional[threading.Thread] = None
        self._detener = threading.Event()
        # AL-12 (auditoría de seguridad 13/jul/2026, mitigación PARCIAL
        # real): evita que una ejecución manual (run_once) y el
        # scheduler automático corran al mismo tiempo dentro de este
        # mismo proceso, pisándose entre sí. NO es un lock distribuido
        # — si algún día corren varios workers/procesos, esto no los
        # coordina entre sí (documentado como pendiente real, no
        # resuelto del todo).
        self._lock_ejecucion = threading.Lock()

        self.ultima_ejecucion: Optional[str] = None
        self.ultimo_resultado: Optional[dict] = None
        self.ultimo_error: Optional[str] = None
        self.total_ejecuciones = 0

    def run_once(self, remember: bool = True) -> dict:
        """Ejecuta el pipeline completo una vez, ahora mismo. Nunca
        lanza silenciosamente — si algo falla, se registra Y se
        levanta, para que quien llame decida qué hacer.

        AL-12: si ya hay una ejecución en curso (manual o del
        scheduler), se rechaza en vez de correr las dos a la vez."""
        if not self._lock_ejecucion.acquire(blocking=False):
            raise RuntimeError("Ya hay una ejecución en curso — se rechaza para no correr dos a la vez.")

        try:
            fuente = self._obtener_fuente()
            videos = fuente.get("top_videos", [])
            topic = fuente.get("topic")

            resultado = self.orchestrator.run(topic=topic, videos=videos, remember=remember, hasta="brain")

            self.ultima_ejecucion = datetime.now().isoformat(timespec="seconds")
            self.ultimo_resultado = resultado
            self.ultimo_error = None
            self.total_ejecuciones += 1

            # Evaluación de notificación — nunca debe tumbar la
            # ejecución del pipeline si algo sale mal aquí; el
            # resultado real del pipeline ya está a salvo arriba.
            brain_report = resultado.get("brain_report")
            if brain_report:
                try:
                    self.notification_center.evaluar_oportunidad(brain_report)
                except Exception as e:
                    logger.warning(f"AutomationEngine: no se pudo evaluar notificación ({e}).")

            logger.info(f"AutomationEngine: ejecución #{self.total_ejecuciones} completada (tema='{topic}').")
            return resultado

        except Exception as e:
            self.ultimo_error = str(e)
            logger.warning(f"AutomationEngine: la ejecución falló ({e}).")
            raise

        finally:
            self._lock_ejecucion.release()

    def esta_activo(self) -> bool:
        return self._hilo is not None and self._hilo.is_alive()

    def start(self, interval_seconds: int = 3600, remember: bool = True) -> None:
        """Corre run_once() en un hilo de fondo cada `interval_seconds`,
        hasta que se llame a stop(). No bloquea el proceso principal
        (FastAPI/uvicorn sigue respondiendo normal)."""
        if self.esta_activo():
            logger.info("AutomationEngine: start() llamado pero ya está activo — se ignora.")
            return

        self._detener.clear()

        def _loop():
            logger.info(f"AutomationEngine: iniciado (cada {interval_seconds}s).")
            while not self._detener.is_set():
                try:
                    self.run_once(remember=remember)
                except Exception as e:
                    # run_once() ya registra el detalle completo; aquí
                    # solo se confirma que el loop sigue vivo pese al
                    # error — nunca un except/pass silencioso.
                    logger.info(f"AutomationEngine: loop continúa pese al error de la última ejecución ({e}).")
                # Espera interrumpible — stop() no tiene que esperar
                # todo el intervalo completo para detenerse.
                self._detener.wait(timeout=interval_seconds)
            logger.info("AutomationEngine: detenido.")

        self._hilo = threading.Thread(target=_loop, daemon=True)
        self._hilo.start()

    def stop(self, esperar: bool = True, timeout: float = 5.0) -> None:
        if not self.esta_activo():
            return
        self._detener.set()
        if esperar and self._hilo:
            self._hilo.join(timeout=timeout)

    def status(self) -> dict:
        return {
            "activo": self.esta_activo(),
            "ultima_ejecucion": self.ultima_ejecucion,
            "total_ejecuciones": self.total_ejecuciones,
            "ultimo_error": self.ultimo_error,
        }
