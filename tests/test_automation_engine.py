import time

from mh_core.core.orchestrator import Orchestrator
from mh_core.database.json_memory_repository import JsonMemoryRepository
from mh_core.database.json_notification_repository import JsonNotificationRepository
from mh_core.engines.automation_engine import AutomationEngine
from mh_core.engines.learning_engine import LearningEngine
from mh_core.engines.memory_engine import MemoryEngine
from mh_core.notifications.notification_center import NotificationCenter

VIDEOS_EJEMPLO = [
    {
        "query": "ia", "video_id": "abc", "title": "Video de prueba", "channel": "Canal",
        "views": 10000, "views_per_day": 500, "likes": 200, "comments": 10,
        "age_days": 3, "url": "https://youtube.com/watch?v=abc",
    }
]


def _fuente_falsa():
    return {"topic": "tema de prueba", "top_videos": VIDEOS_EJEMPLO}


def _fuente_que_falla():
    raise RuntimeError("fuente caída (simulado)")


def _motor_aislado(tmp_path, obtener_fuente=_fuente_falsa):
    repo = JsonMemoryRepository(tmp_path / "history.json")
    learning_engine = LearningEngine(memory_engine=MemoryEngine(repository=repo))
    orquestador = Orchestrator(learning_engine=learning_engine)
    # Aislado también de notificaciones — sin esto, cualquier test que
    # dispare una oportunidad "fuerte" escribiría al archivo real.
    centro_notificaciones = NotificationCenter(
        repository=JsonNotificationRepository(tmp_path / "notifications.json")
    )
    return AutomationEngine(
        orchestrator=orquestador, obtener_fuente=obtener_fuente, notification_center=centro_notificaciones
    )


# --- run_once ---------------------------------------------------------------


def test_run_once_devuelve_pipeline_completo(tmp_path):
    motor = _motor_aislado(tmp_path)
    resultado = motor.run_once()

    assert "brain_report" in resultado
    assert motor.total_ejecuciones == 1
    assert motor.ultimo_error is None
    assert motor.ultima_ejecucion is not None


def test_run_once_registra_error_y_lo_relanza_sin_silenciarlo(tmp_path):
    motor = _motor_aislado(tmp_path, obtener_fuente=_fuente_que_falla)

    try:
        motor.run_once()
        assert False, "debía lanzar la excepción, no tragársela"
    except RuntimeError:
        pass

    assert motor.ultimo_error is not None
    assert "fuente caída" in motor.ultimo_error
    assert motor.total_ejecuciones == 0


def test_run_once_remember_false_no_guarda_memoria(tmp_path):
    motor = _motor_aislado(tmp_path)
    motor.run_once(remember=False)

    assert motor.orchestrator.learning_engine.get_history() == []


# --- status -------------------------------------------------------------


def test_status_antes_de_correr(tmp_path):
    motor = _motor_aislado(tmp_path)
    estado = motor.status()

    assert estado["activo"] is False
    assert estado["total_ejecuciones"] == 0
    assert estado["ultima_ejecucion"] is None


# --- start/stop del loop en segundo plano --------------------------------


def test_start_ejecuta_en_segundo_plano_y_stop_lo_detiene(tmp_path):
    motor = _motor_aislado(tmp_path)

    motor.start(interval_seconds=0.05)
    assert motor.esta_activo() is True

    time.sleep(0.2)  # deja correr un par de ciclos reales, cortos de verdad
    motor.stop(esperar=True, timeout=2)

    assert motor.esta_activo() is False
    assert motor.total_ejecuciones >= 1


def test_start_dos_veces_no_duplica_el_hilo(tmp_path):
    motor = _motor_aislado(tmp_path)

    motor.start(interval_seconds=1)
    primer_hilo = motor._hilo
    motor.start(interval_seconds=1)  # debe ignorarse, ya está activo

    assert motor._hilo is primer_hilo
    motor.stop()


def test_stop_sin_haber_iniciado_no_falla(tmp_path):
    motor = _motor_aislado(tmp_path)
    motor.stop()  # no debe lanzar nada
    assert motor.esta_activo() is False


# --- Integración con NotificationCenter (Fase 1: Notificaciones) --------


def test_run_once_evalua_notificacion_tras_ejecutar(tmp_path):
    from mh_core.notifications.notification_rules import NotificationRules

    repo_mem = JsonMemoryRepository(tmp_path / "history.json")
    learning_engine = LearningEngine(memory_engine=MemoryEngine(repository=repo_mem))
    orquestador = Orchestrator(learning_engine=learning_engine)

    repo_notif = JsonNotificationRepository(tmp_path / "notifications.json")
    # Umbral muy bajo a propósito, para no depender de que el video de
    # prueba genere un score alto de verdad — lo que se prueba aquí es
    # que AutomationEngine SÍ llama a evaluar_oportunidad, no la lógica
    # de reglas en sí (eso ya lo cubre test_notifications.py).
    centro = NotificationCenter(repository=repo_notif, rules=NotificationRules(umbral_probabilidad=0))

    motor = AutomationEngine(orchestrator=orquestador, obtener_fuente=_fuente_falsa, notification_center=centro)
    motor.run_once()

    assert len(centro.listar()) == 1


def test_fallo_al_notificar_no_tumba_la_ejecucion(tmp_path):
    class _CentroQueFalla:
        def evaluar_oportunidad(self, brain_report):
            raise RuntimeError("falla simulada de notificaciones")

    repo_mem = JsonMemoryRepository(tmp_path / "history.json")
    learning_engine = LearningEngine(memory_engine=MemoryEngine(repository=repo_mem))
    orquestador = Orchestrator(learning_engine=learning_engine)

    motor = AutomationEngine(
        orchestrator=orquestador, obtener_fuente=_fuente_falsa, notification_center=_CentroQueFalla()
    )

    # No debe lanzar — un fallo al notificar no debe tumbar el pipeline real.
    resultado = motor.run_once()
    assert "brain_report" in resultado
    assert motor.ultimo_error is None


# --- AL-12 (mitigación parcial, en proceso): sin ejecuciones simultáneas ---


def test_run_once_rechaza_ejecucion_simultanea(tmp_path):
    """Mientras una ejecución real está en curso (bloqueada dentro de
    _obtener_fuente), una segunda llamada a run_once() debe
    rechazarse, no correr encima de la primera."""
    import threading

    evento_dentro = threading.Event()
    evento_liberar = threading.Event()

    def _fuente_lenta():
        evento_dentro.set()
        evento_liberar.wait(timeout=5)
        return _fuente_falsa()

    motor = _motor_aislado(tmp_path, obtener_fuente=_fuente_lenta)

    hilo = threading.Thread(target=motor.run_once)
    hilo.start()
    evento_dentro.wait(timeout=5)  # esperar a que la primera ya esté "dentro"

    try:
        motor.run_once()
        assert False, "debía rechazar la segunda ejecución simultánea"
    except RuntimeError as e:
        assert "ya hay una ejecución en curso" in str(e).lower()
    finally:
        evento_liberar.set()
        hilo.join(timeout=5)


def test_run_once_libera_el_lock_incluso_si_falla(tmp_path):
    """El lock no debe quedar atascado para siempre si la primera
    ejecución falla."""
    motor = _motor_aislado(tmp_path, obtener_fuente=_fuente_que_falla)

    try:
        motor.run_once()
    except RuntimeError:
        pass

    # Si el lock se liberó bien, esta segunda llamada NO debe rechazarse
    # por "ejecución en curso" (puede fallar por otra razón, pero no por eso).
    motor2 = _motor_aislado(tmp_path)
    resultado = motor2.run_once()
    assert "brain_report" in resultado
