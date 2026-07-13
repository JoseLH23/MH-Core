"""
TTSEngine — narración real con pyttsx3 (100% local y gratis, ya
disponible en el entorno — audité antes de agregar nada: no hace
falta ninguna API de pago ni internet).
"""
from pathlib import Path

import pyttsx3


class TTSEngine:
    def sintetizar(self, texto: str, ruta_salida: Path, velocidad: int = 165) -> Path:
        """Genera un WAV real a partir del texto. Lanza si pyttsx3
        falla — nunca se inventa un archivo de audio vacío como si
        fuera real."""
        motor = pyttsx3.init()
        motor.setProperty("rate", velocidad)
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)
        motor.save_to_file(texto, str(ruta_salida))
        motor.runAndWait()

        if not ruta_salida.exists() or ruta_salida.stat().st_size == 0:
            raise RuntimeError("pyttsx3 no generó un archivo de audio válido.")

        return ruta_salida
