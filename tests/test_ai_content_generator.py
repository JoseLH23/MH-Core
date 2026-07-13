from apps.mindhigh.models.content_piece import ContentPiece
from apps.mindhigh.services.ai_content_generator import AIContentGenerator

BRAIN_REPORT_EJEMPLO = {
    "executive_summary": {"topic": "ia en medicina", "final_recommendation": "PRODUCIR"},
    "reasoning": ["razón real"],
    "recommended_actions": ["acción real"],
}


class _GeminiFalso:
    def __init__(self, resultado):
        self.resultado = resultado
        self.llamado = False

    def intentar(self, brain_report):
        self.llamado = True
        return self.resultado


class _GroqFalso:
    def __init__(self, resultado):
        self.resultado = resultado
        self.llamado = False

    def intentar(self, brain_report):
        self.llamado = True
        return self.resultado


def _pieza(fuente: str) -> ContentPiece:
    return ContentPiece(id="x", topic="ia en medicina", title=f"Título de {fuente}", script=f"Guion de {fuente}")


# --- Prioridad: Gemini primero -----------------------------------------


def test_usa_gemini_si_esta_disponible_y_no_llama_a_groq():
    gemini = _GeminiFalso(_pieza("gemini"))
    groq = _GroqFalso(_pieza("groq"))
    generador = AIContentGenerator(gemini=gemini, groq=groq)

    contenido = generador.generar(BRAIN_REPORT_EJEMPLO)

    assert contenido.title == "Título de gemini"
    assert groq.llamado is False  # no debe gastar cuota de Groq si Gemini ya respondió


# --- Respaldo real: Groq cuando Gemini falla -------------------------------


def test_usa_groq_cuando_gemini_no_disponible():
    gemini = _GeminiFalso(None)
    groq = _GroqFalso(_pieza("groq"))
    generador = AIContentGenerator(gemini=gemini, groq=groq)

    contenido = generador.generar(BRAIN_REPORT_EJEMPLO)

    assert contenido.title == "Título de groq"
    assert gemini.llamado is True
    assert groq.llamado is True


# --- Red de seguridad: plantillas si ninguno responde ----------------------


def test_usa_plantillas_si_ni_gemini_ni_groq_responden():
    gemini = _GeminiFalso(None)
    groq = _GroqFalso(None)
    generador = AIContentGenerator(gemini=gemini, groq=groq)

    contenido = generador.generar(BRAIN_REPORT_EJEMPLO)

    assert isinstance(contenido, ContentPiece)
    assert "generado por plantilla" in contenido.script
