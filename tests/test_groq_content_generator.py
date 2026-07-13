from apps.mindhigh.models.content_piece import ContentPiece
from apps.mindhigh.services.groq_content_generator import GroqContentGenerator

BRAIN_REPORT_EJEMPLO = {
    "executive_summary": {"topic": "inteligencia artificial en medicina", "final_recommendation": "PRODUCIR"},
    "reasoning": ["El MH Score es alto."],
    "recommended_actions": ["Producir cuanto antes."],
}


class _RespuestaHTTPFalsa:
    def __init__(self, texto, status_code=200):
        self._texto = texto
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return {"choices": [{"message": {"content": self._texto}}]}


class _SesionHTTPFalsa:
    def __init__(self, texto, status_code=200):
        self.texto = texto
        self.status_code = status_code
        self.llamadas = []

    def post(self, url, headers, json, timeout):
        self.llamadas.append({"url": url, "json": json})
        return _RespuestaHTTPFalsa(self.texto, self.status_code)


class _SesionHTTPQueFalla:
    def post(self, url, headers, json, timeout):
        raise RuntimeError("cuota agotada del nivel gratis (simulado)")


# --- Sin API key -------------------------------------------------------


def test_sin_api_key_intentar_devuelve_none():
    generador = GroqContentGenerator(api_key=None)
    assert generador.intentar(BRAIN_REPORT_EJEMPLO) is None


def test_sin_api_key_generar_usa_fallback_de_plantillas():
    generador = GroqContentGenerator(api_key=None)
    contenido = generador.generar(BRAIN_REPORT_EJEMPLO)

    assert isinstance(contenido, ContentPiece)
    assert "generado por plantilla" in contenido.script


# --- Éxito real (formato esperado) ---------------------------------------


def test_con_respuesta_bien_formateada_usa_titulo_y_guion_de_groq():
    sesion_falsa = _SesionHTTPFalsa("TITULO: La IA en medicina\nGUION:\nGancho inicial...\nCierre...")
    generador = GroqContentGenerator(api_key="clave-falsa", sesion_http=sesion_falsa)

    contenido = generador.generar(BRAIN_REPORT_EJEMPLO)

    assert contenido.title == "La IA en medicina"
    assert "Gancho inicial" in contenido.script
    assert sesion_falsa.llamadas[0]["json"]["model"] == "llama-3.3-70b-versatile"


def test_respeta_modelo_configurado():
    sesion_falsa = _SesionHTTPFalsa("TITULO: X\nGUION:\nY")
    generador = GroqContentGenerator(api_key="clave", model="llama-3.1-8b-instant", sesion_http=sesion_falsa)

    generador.generar(BRAIN_REPORT_EJEMPLO)

    assert sesion_falsa.llamadas[0]["json"]["model"] == "llama-3.1-8b-instant"


# --- Formato inesperado / vacío --------------------------------------------


def test_respuesta_sin_formato_esperado_no_falla():
    sesion_falsa = _SesionHTTPFalsa("Contenido libre sin el formato pedido.")
    generador = GroqContentGenerator(api_key="clave", sesion_http=sesion_falsa)

    contenido = generador.generar(BRAIN_REPORT_EJEMPLO)

    assert "sin el formato pedido" in contenido.script


def test_respuesta_vacia_usa_fallback():
    sesion_falsa = _SesionHTTPFalsa("")
    generador = GroqContentGenerator(api_key="clave", sesion_http=sesion_falsa)

    contenido = generador.generar(BRAIN_REPORT_EJEMPLO)

    assert "generado por plantilla" in contenido.script


# --- Error real (429 por cuota, o excepción de red) — no silencioso -------


def test_error_http_429_cae_a_fallback_sin_tronar():
    sesion_falsa = _SesionHTTPFalsa("no importa", status_code=429)
    generador = GroqContentGenerator(api_key="clave", sesion_http=sesion_falsa, reintentos=1)

    contenido = generador.generar(BRAIN_REPORT_EJEMPLO)

    assert isinstance(contenido, ContentPiece)
    assert "generado por plantilla" in contenido.script


def test_excepcion_de_red_cae_a_fallback_sin_tronar():
    generador = GroqContentGenerator(api_key="clave", sesion_http=_SesionHTTPQueFalla(), reintentos=1)

    contenido = generador.generar(BRAIN_REPORT_EJEMPLO)

    assert "generado por plantilla" in contenido.script


def test_reintenta_antes_de_caer_al_fallback():
    """Confirma que sí hay reintentos reales, con espera casi nula."""

    class _SesionQueFallaDosVecesYLuegoResponde:
        def __init__(self):
            self.llamadas = 0

        def post(self, url, headers, json, timeout):
            self.llamadas += 1
            if self.llamadas < 3:
                raise RuntimeError("429 simulado")
            return _RespuestaHTTPFalsa("TITULO: Al tercer intento\nGUION:\nFuncionó")

    sesion = _SesionQueFallaDosVecesYLuegoResponde()
    generador = GroqContentGenerator(api_key="clave", sesion_http=sesion, reintentos=3, espera_inicial=0.01)

    contenido = generador.generar(BRAIN_REPORT_EJEMPLO)

    assert contenido.title == "Al tercer intento"
    assert sesion.llamadas == 3
