import json

from apps.mindhigh.models.content_piece import ContentPiece
from apps.mindhigh.services.groq_content_generator import GroqContentGenerator

BRAIN_REPORT_EJEMPLO = {
    "executive_summary": {"topic": "inteligencia artificial en medicina", "final_recommendation": "PRODUCIR"},
    "reasoning": ["El MH Score es alto."],
    "recommended_actions": ["Producir cuanto antes."],
}

JSON_BIEN_FORMADO = json.dumps(
    {
        "titulo": "La IA en medicina",
        "gancho": "Esto va a cambiar cómo se diagnostica.",
        "guion": "Gancho inicial...\nDesarrollo...\nCierre...",
        "descripcion": "Video sobre IA en medicina.",
        "hashtags": ["#IA", "#Salud"],
        "cta": "Comenta qué opinas.",
    },
    ensure_ascii=False,
)


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


def test_sin_api_key_intentar_devuelve_none(monkeypatch):
    # monkeypatch.delenv asegura que el test no dependa de si GROQ_API_KEY
    # ya existe como variable de entorno real en la máquina donde corre
    # (ej. exportada a mano en PowerShell para probar con curl) — sin
    # esto, api_key=None seguía cayendo al valor real vía
    # os.environ.get("GROQ_API_KEY") y el test fallaba de forma
    # intermitente según el entorno, no por un cambio real de comportamiento.
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    generador = GroqContentGenerator(api_key=None)
    assert generador.intentar(BRAIN_REPORT_EJEMPLO) is None


def test_sin_api_key_generar_usa_fallback_de_plantillas(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    generador = GroqContentGenerator(api_key=None)
    contenido = generador.generar(BRAIN_REPORT_EJEMPLO)

    assert isinstance(contenido, ContentPiece)
    assert "generado por plantilla" in contenido.script


def test_con_respuesta_json_usa_todos_los_campos_estructurados():
    sesion_falsa = _SesionHTTPFalsa(JSON_BIEN_FORMADO)
    generador = GroqContentGenerator(api_key="clave-falsa", sesion_http=sesion_falsa)

    contenido = generador.generar(BRAIN_REPORT_EJEMPLO)

    assert contenido.title == "La IA en medicina"
    assert "Desarrollo" in contenido.script
    assert contenido.hashtags == ["#IA", "#Salud"]
    assert contenido.cta == "Comenta qué opinas."
    assert sesion_falsa.llamadas[0]["json"]["model"] == "llama-3.3-70b-versatile"


def test_pasa_duration_target_y_style_al_prompt():
    sesion_falsa = _SesionHTTPFalsa(JSON_BIEN_FORMADO)
    generador = GroqContentGenerator(api_key="clave", sesion_http=sesion_falsa)

    contenido = generador.generar(BRAIN_REPORT_EJEMPLO, duration_target="medio", style="cercano")

    assert contenido.duration_target == "medio"
    assert contenido.style == "cercano"
    mensaje_enviado = sesion_falsa.llamadas[0]["json"]["messages"][0]["content"]
    assert "3 a 5 minutos" in mensaje_enviado
    assert "cercano" in mensaje_enviado


def test_respeta_modelo_configurado():
    sesion_falsa = _SesionHTTPFalsa(JSON_BIEN_FORMADO)
    generador = GroqContentGenerator(api_key="clave", model="llama-3.1-8b-instant", sesion_http=sesion_falsa)

    generador.generar(BRAIN_REPORT_EJEMPLO)

    assert sesion_falsa.llamadas[0]["json"]["model"] == "llama-3.1-8b-instant"


# --- Formato inesperado / vacío --------------------------------------------


def test_respuesta_sin_json_no_falla_usa_texto_libre():
    sesion_falsa = _SesionHTTPFalsa("Contenido libre sin el formato JSON pedido.")
    generador = GroqContentGenerator(api_key="clave", sesion_http=sesion_falsa)

    contenido = generador.generar(BRAIN_REPORT_EJEMPLO)

    assert "sin el formato JSON pedido" in contenido.script or contenido.title


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
    # Precomputado FUERA del método post(): dentro de él, el parámetro
    # se llama `json` (mismo nombre que requests usa como keyword real,
    # ver groq_content_generator.py) y tapa al módulo `json` — llamar
    # json.dumps() ahí adentro fallaría con 'dict' object has no
    # attribute 'dumps'.
    respuesta_json = json.dumps({"titulo": "Al tercer intento", "guion": "Funcionó"})

    class _SesionQueFallaDosVecesYLuegoResponde:
        def __init__(self):
            self.llamadas = 0

        def post(self, url, headers, json, timeout):
            self.llamadas += 1
            if self.llamadas < 3:
                raise RuntimeError("429 simulado")
            return _RespuestaHTTPFalsa(respuesta_json)

    sesion = _SesionQueFallaDosVecesYLuegoResponde()
    generador = GroqContentGenerator(api_key="clave", sesion_http=sesion, reintentos=3, espera_inicial=0.01)

    contenido = generador.generar(BRAIN_REPORT_EJEMPLO)

    assert contenido.title == "Al tercer intento"
    assert sesion.llamadas == 3
