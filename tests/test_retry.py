import pytest

from mh_core.utils.retry import reintentar_con_backoff


def test_devuelve_el_resultado_si_funciona_al_primer_intento():
    llamadas = []

    def func():
        llamadas.append(1)
        return "ok"

    resultado = reintentar_con_backoff(func, intentos=3, espera_inicial=0.01)

    assert resultado == "ok"
    assert len(llamadas) == 1


def test_reintenta_hasta_que_funciona():
    llamadas = []

    def func():
        llamadas.append(1)
        if len(llamadas) < 3:
            raise RuntimeError("falla simulada")
        return "ok al tercer intento"

    resultado = reintentar_con_backoff(func, intentos=5, espera_inicial=0.01)

    assert resultado == "ok al tercer intento"
    assert len(llamadas) == 3


def test_relanza_el_error_real_si_agota_los_intentos():
    def func():
        raise ValueError("siempre falla")

    with pytest.raises(ValueError, match="siempre falla"):
        reintentar_con_backoff(func, intentos=3, espera_inicial=0.01)


def test_respeta_el_numero_exacto_de_intentos():
    llamadas = []

    def func():
        llamadas.append(1)
        raise RuntimeError("falla")

    with pytest.raises(RuntimeError):
        reintentar_con_backoff(func, intentos=4, espera_inicial=0.01)

    assert len(llamadas) == 4


def test_espera_crece_exponencialmente(monkeypatch):
    esperas_reales = []
    monkeypatch.setattr("mh_core.utils.retry.time.sleep", lambda s: esperas_reales.append(s))

    def func():
        raise RuntimeError("falla")

    with pytest.raises(RuntimeError):
        reintentar_con_backoff(func, intentos=4, espera_inicial=1.0, factor=2.0)

    # 4 intentos -> 3 esperas entre ellos: 1, 2, 4
    assert esperas_reales == [1.0, 2.0, 4.0]
