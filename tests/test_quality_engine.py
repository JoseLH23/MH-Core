from apps.mindhigh.models.content_piece import ContentPiece
from apps.mindhigh.services.quality_engine import QualityEngine


def _pieza(**overrides) -> ContentPiece:
    base = dict(
        id="c1",
        topic="inteligencia artificial en medicina",
        title="La IA en medicina: lo que nadie te explicó",
        hook="¿Sabías que la IA ya diagnostica mejor que algunos médicos?",
        script="Gancho inicial.\nPunto uno.\nPunto dos.\nPunto tres.\nCierre con CTA.",
        description="Un video real sobre IA en medicina.",
        hashtags=["#IA", "#Medicina", "#Salud"],
        cta="Sígueme para más contenido como este.",
        duration_target="short",
    )
    base.update(overrides)
    return ContentPiece(**base)


def test_contenido_completo_y_bien_formado_aprueba():
    evaluacion = QualityEngine().evaluar(_pieza())

    assert evaluacion.aprobado is True
    assert evaluacion.score_total >= 60


def test_contenido_sin_gancho_baja_el_puntaje():
    con_gancho = QualityEngine().evaluar(_pieza())
    sin_gancho = QualityEngine().evaluar(_pieza(hook=""))

    assert sin_gancho.gancho < con_gancho.gancho
    assert any("gancho" in r for r in sin_gancho.razones)


def test_contenido_sin_cta_baja_utilidad_y_retencion():
    evaluacion = QualityEngine().evaluar(_pieza(cta=""))

    assert any("CTA" in r or "llamado a la acción" in r for r in evaluacion.razones)


def test_guion_muy_corto_para_duracion_larga_baja_claridad():
    corto = _pieza(duration_target="largo", script="Muy corto.")
    evaluacion = QualityEngine().evaluar(corto)

    assert evaluacion.claridad < 100
    assert any("claridad" in r for r in evaluacion.razones)


def test_pocos_hashtags_baja_utilidad():
    evaluacion = QualityEngine().evaluar(_pieza(hashtags=["#Solo1"]))

    assert evaluacion.utilidad < 100
    assert any("hashtags" in r for r in evaluacion.razones)


def test_sin_video_original_no_penaliza_originalidad():
    evaluacion = QualityEngine().evaluar(_pieza(), video_original_titulo=None)
    assert evaluacion.originalidad == 100.0


def test_titulo_casi_identico_al_video_original_baja_originalidad():
    pieza = _pieza(title="Como la inteligencia artificial cambia la medicina moderna hoy")
    evaluacion = QualityEngine().evaluar(
        pieza, video_original_titulo="Como la inteligencia artificial cambia la medicina moderna hoy"
    )

    assert evaluacion.originalidad < 50
    assert any("originalidad" in r for r in evaluacion.razones)


def test_titulo_totalmente_distinto_no_baja_originalidad():
    pieza = _pieza(title="5 secretos que los médicos no te cuentan")
    evaluacion = QualityEngine().evaluar(pieza, video_original_titulo="Receta de pastel de chocolate fácil")

    assert evaluacion.originalidad > 80


def test_score_total_es_promedio_de_los_5_criterios():
    evaluacion = QualityEngine().evaluar(_pieza())
    promedio_esperado = round(
        (evaluacion.claridad + evaluacion.gancho + evaluacion.retencion + evaluacion.utilidad + evaluacion.originalidad) / 5,
        1,
    )
    assert evaluacion.score_total == promedio_esperado
