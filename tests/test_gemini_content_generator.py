from apps.mindhigh.services.gemini_content_generator import GeminiContentGenerator
from apps.mindhigh.models.content_piece import ContentPiece

BRAIN_REPORT_EJEMPLO = {
    "executive_summary": {"topic": "inteligencia artificial en medicina", "final_recommendation": "PRODUCIR"},
    "reasoning": ["El MH Score es alto."],
    "recommended_actions": ["Producir cuanto antes."],
}


class _RespuestaFalsa:
    def __init__(self, texto):
        self.text = texto


class _ModelsFalso:
    def __init__(self, texto):
        self.texto = texto
        self.llamadas = []

    def generate_content(self, model, contents):
        self.llamadas.append((model, contents))
        return _RespuestaFalsa(self.texto)


class _ClienteGeminiFalso:
    def __init__(self, texto):
        self.models = _ModelsFalso(texto)


class _ClienteGeminiQueFalla:
    class models:
        @staticmethod
        def generate_content(model, contents):
            raise RuntimeError("cuota agotada del nivel gratis (simulado)")


# --- Sin API key -------------------------------------------------------


def test_sin_api_key_usa_fallback_de_plantillas():
    generador = GeminiContentGenerator(api_key=None)
    contenido = generador.generar(BRAIN_REPORT_EJEMPLO)

    assert isinstance(contenido, ContentPiece)
    assert "generado por plantilla" in contenido.script  # marca real del fallback


# --- Éxito real (formato esperado) ---------------------------------------


def test_con_respuesta_bien_formateada_usa_titulo_y_guion_de_gemini():
    cliente_falso = _ClienteGeminiFalso(
        "TITULO: Lo que la IA está cambiando en medicina\nGUION:\nGancho inicial...\nCierre..."
    )
    generador = GeminiContentGenerator(api_key="clave-falsa-de-prueba", cliente=cliente_falso)

    contenido = generador.generar(BRAIN_REPORT_EJEMPLO)

    assert contenido.title == "Lo que la IA está cambiando en medicina"
    assert "Gancho inicial" in contenido.script
    assert contenido.topic == "inteligencia artificial en medicina"
    assert cliente_falso.models.llamadas[0][0] == "gemini-3.5-flash"


def test_modelo_por_defecto_es_gemini_3_5_flash():
    """Confirma el valor por defecto real usado cuando no se pasa `model`
    explícito — evita que un cambio futuro lo modifique sin darse cuenta."""
    cliente_falso = _ClienteGeminiFalso("TITULO: X\nGUION:\nY")
    generador = GeminiContentGenerator(api_key="clave", cliente=cliente_falso)

    assert generador.model == "gemini-3.5-flash"

    generador.generar(BRAIN_REPORT_EJEMPLO)
    assert cliente_falso.models.llamadas[0][0] == "gemini-3.5-flash"


def test_respeta_modelo_configurado_por_variable():
    cliente_falso = _ClienteGeminiFalso("TITULO: X\nGUION:\nY")
    generador = GeminiContentGenerator(api_key="clave", model="gemini-2.0-flash", cliente=cliente_falso)

    generador.generar(BRAIN_REPORT_EJEMPLO)

    assert cliente_falso.models.llamadas[0][0] == "gemini-2.0-flash"


# --- Formato inesperado, no falla -----------------------------------------


def test_respuesta_sin_formato_esperado_no_falla():
    cliente_falso = _ClienteGeminiFalso("Aquí está tu contenido sin seguir el formato pedido.")
    generador = GeminiContentGenerator(api_key="clave", cliente=cliente_falso)

    contenido = generador.generar(BRAIN_REPORT_EJEMPLO)

    assert "sin seguir el formato" in contenido.script
    assert "generado por IA" in contenido.title


def test_respuesta_vacia_usa_fallback():
    cliente_falso = _ClienteGeminiFalso("")
    generador = GeminiContentGenerator(api_key="clave", cliente=cliente_falso)

    contenido = generador.generar(BRAIN_REPORT_EJEMPLO)

    assert "generado por plantilla" in contenido.script


# --- Error real de la API (no silencioso) ---------------------------------


def test_error_de_api_cae_a_fallback_sin_tronar():
    generador = GeminiContentGenerator(api_key="clave", cliente=_ClienteGeminiQueFalla(), reintentos=1)

    contenido = generador.generar(BRAIN_REPORT_EJEMPLO)

    assert isinstance(contenido, ContentPiece)
    assert "generado por plantilla" in contenido.script


def test_reintenta_antes_de_caer_al_fallback():
    """Confirma que sí hay reintentos reales (no solo un intento) —
    con espera casi nula para no volver el test lento."""

    class _ClienteQueFallaDosVecesYLuegoResponde:
        def __init__(self):
            self.llamadas = 0

        class models:
            llamadas = 0

            @staticmethod
            def generate_content(model, contents):
                _ClienteQueFallaDosVecesYLuegoResponde.models.llamadas += 1
                if _ClienteQueFallaDosVecesYLuegoResponde.models.llamadas < 3:
                    raise RuntimeError("429 simulado")
                return _RespuestaFalsa("TITULO: Al tercer intento\nGUION:\nFuncionó")

    cliente = _ClienteQueFallaDosVecesYLuegoResponde()
    generador = GeminiContentGenerator(api_key="clave", cliente=cliente, reintentos=3, espera_inicial=0.01)

    contenido = generador.generar(BRAIN_REPORT_EJEMPLO)

    assert contenido.title == "Al tercer intento"
    assert cliente.models.llamadas == 3
