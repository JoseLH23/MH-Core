import time

from mh_core.core.orchestrator import Orchestrator
from mh_core.database.json_memory_repository import JsonMemoryRepository
from mh_core.engines.automation_engine import AutomationEngine
from mh_core.engines.learning_engine import LearningEngine
from mh_core.engines.memory_engine import MemoryEngine

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
    return AutomationEngine(orchestrator=orquestador, obtener_fuente=obtener_fuente)


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
