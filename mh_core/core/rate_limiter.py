"""
Rate limiter real — solo librería estándar (sin agregar slowapi ni
ninguna dependencia nueva). Riesgo real que se documentó en la sesión
anterior: sin esto, alguien con acceso al panel/API podía llamar
POST /mindhigh/run o POST /video/render en bucle y agotar la cuota
gratis de Gemini/Groq en minutos.

Ventana deslizante simple, en memoria — suficiente para un solo
proceso (uvicorn sin varios workers). Si algún día se corre con
múltiples workers, esto necesitaría moverse a algo compartido (Redis,
etc.) — documentado como límite real, no oculto.
"""
import threading
import time
from collections import defaultdict


class RateLimiter:
    def __init__(self, max_llamadas: int, ventana_segundos: int):
        self.max_llamadas = max_llamadas
        self.ventana_segundos = ventana_segundos
        self._llamadas: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def permitido(self, clave: str) -> bool:
        ahora = time.time()
        with self._lock:
            recientes = [t for t in self._llamadas[clave] if ahora - t < self.ventana_segundos]
            if len(recientes) >= self.max_llamadas:
                self._llamadas[clave] = recientes
                return False
            recientes.append(ahora)
            self._llamadas[clave] = recientes
            return True

    def segundos_para_reintentar(self, clave: str) -> float:
        with self._lock:
            llamadas = self._llamadas.get(clave, [])
            if not llamadas:
                return 0.0
            mas_antigua = min(llamadas)
            return max(0.0, self.ventana_segundos - (time.time() - mas_antigua))
