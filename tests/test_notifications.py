from mh_core.database.json_notification_repository import JsonNotificationRepository
from mh_core.notifications.notification_center import NotificationCenter
from mh_core.notifications.notification_rules import NotificationRules

BRAIN_REPORT_FUERTE = {
    "executive_summary": {
        "topic": "ia en medicina",
        "success_probability": 85,
        "confidence": "HIGH",
        "final_recommendation": "PRODUCIR_INMEDIATAMENTE",
    },
    "evidence": {"decision": {"best_opportunity": {"priority": "HIGH"}}},
}

BRAIN_REPORT_DEBIL = {
    "executive_summary": {
        "topic": "tema sin interés",
        "success_probability": 20,
        "confidence": "LOW",
        "final_recommendation": "NO_PRIORIZAR",
    },
    "evidence": {"decision": {"best_opportunity": {"priority": "LOW"}}},
}


def _centro(tmp_path):
    repo = JsonNotificationRepository(tmp_path / "notifications.json")
    return NotificationCenter(repository=repo, adapters=[])  # sin adaptadores reales en tests


# --- NotificationRules ---------------------------------------------------


def test_rules_modo_cualquiera_basta_una_condicion():
    reglas = NotificationRules(umbral_probabilidad=70, confidence_requerida=("HIGH",), prioridad_requerida=("HIGH",))
    assert reglas.cumple(success_probability=85, confidence="LOW", priority="LOW") is True  # solo probabilidad


def test_rules_modo_todas_requiere_las_3():
    reglas = NotificationRules(modo="todas", umbral_probabilidad=70, confidence_requerida=("HIGH",), prioridad_requerida=("HIGH",))
    assert reglas.cumple(success_probability=85, confidence="LOW", priority="HIGH") is False
    assert reglas.cumple(success_probability=85, confidence="HIGH", priority="HIGH") is True


def test_rules_no_cumple_si_todo_esta_bajo():
    reglas = NotificationRules()
    assert reglas.cumple(success_probability=10, confidence="LOW", priority="LOW") is False


# --- NotificationCenter.evaluar_oportunidad ------------------------------


def test_oportunidad_fuerte_genera_notificacion(tmp_path):
    centro = _centro(tmp_path)
    notificacion = centro.evaluar_oportunidad(BRAIN_REPORT_FUERTE)

    assert notificacion is not None
    assert notificacion.topic == "ia en medicina"
    assert notificacion.read is False


def test_oportunidad_debil_no_genera_notificacion(tmp_path):
    centro = _centro(tmp_path)
    notificacion = centro.evaluar_oportunidad(BRAIN_REPORT_DEBIL)

    assert notificacion is None
    assert centro.listar() == []


def test_no_genera_notificaciones_duplicadas(tmp_path):
    centro = _centro(tmp_path)
    primera = centro.evaluar_oportunidad(BRAIN_REPORT_FUERTE)
    segunda = centro.evaluar_oportunidad(BRAIN_REPORT_FUERTE)  # mismo tema+recomendación, justo después

    assert primera is not None
    assert segunda is None
    assert len(centro.listar()) == 1


def test_temas_distintos_si_generan_notificaciones_separadas(tmp_path):
    centro = _centro(tmp_path)
    reporte_2 = {**BRAIN_REPORT_FUERTE, "executive_summary": {**BRAIN_REPORT_FUERTE["executive_summary"], "topic": "otro tema"}}

    centro.evaluar_oportunidad(BRAIN_REPORT_FUERTE)
    centro.evaluar_oportunidad(reporte_2)

    assert len(centro.listar()) == 2


# --- Persistencia + leído/no leído ----------------------------------------


def test_persiste_entre_instancias(tmp_path):
    ruta = tmp_path / "notifications.json"
    NotificationCenter(repository=JsonNotificationRepository(ruta), adapters=[]).evaluar_oportunidad(BRAIN_REPORT_FUERTE)

    centro2 = NotificationCenter(repository=JsonNotificationRepository(ruta), adapters=[])
    assert len(centro2.listar()) == 1


def test_marcar_leida_cambia_el_estado(tmp_path):
    centro = _centro(tmp_path)
    notificacion = centro.evaluar_oportunidad(BRAIN_REPORT_FUERTE)

    actualizada = centro.marcar_leida(notificacion.id)

    assert actualizada.read is True
    assert centro.listar(solo_no_leidas=True) == []


def test_marcar_leida_id_inexistente_devuelve_none(tmp_path):
    centro = _centro(tmp_path)
    assert centro.marcar_leida("no-existe") is None


def test_listar_solo_no_leidas_filtra_correctamente(tmp_path):
    centro = _centro(tmp_path)
    reporte_2 = {**BRAIN_REPORT_FUERTE, "executive_summary": {**BRAIN_REPORT_FUERTE["executive_summary"], "topic": "otro tema"}}

    n1 = centro.evaluar_oportunidad(BRAIN_REPORT_FUERTE)
    centro.evaluar_oportunidad(reporte_2)
    centro.marcar_leida(n1.id)

    no_leidas = centro.listar(solo_no_leidas=True)
    assert len(no_leidas) == 1
    assert no_leidas[0].topic == "otro tema"


# --- Archivo corrupto, sin fallar -----------------------------------------


def test_archivo_corrupto_no_falla_y_se_respalda(tmp_path):
    ruta = tmp_path / "corrupto.json"
    ruta.write_text("{roto", encoding="utf-8")

    centro = NotificationCenter(repository=JsonNotificationRepository(ruta), adapters=[])
    assert centro.listar() == []

    respaldos = list(tmp_path.glob("corrupto.corrupto-*.json.bak"))
    assert len(respaldos) == 1
